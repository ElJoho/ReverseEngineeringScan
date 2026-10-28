#!/usr/bin/env python3
"""Cliente mínimo para el puente Wi-Fi de Creality ("Scan Pocket", Orbbec "Wifi Handle") con el CR-Scan Otter.

Protocolos (obtenidos por ingeniería inversa de libOrbbecSDK 1.7.1 de macOS y pruebas en vivo):
  - UDP 3956  GVCP (GigE Vision): descubrimiento.
  - TCP 8090  HostProtocol de Orbbec: comandos (propiedades, datos crudos, heartbeat).
  - RTSP      video: rtsp://IP:PUERTO/<stream>/<ancho>_<alto>_<fps>_<formato>
              (ir_l :8556, ir_r :8557, color :8888 mjpg). Cada cuadro = cabecera de 26 bytes + datos.

Uso:
  otter_bridge.py discover
  otter_bridge.py heartbeat
  otter_bridge.py ports                          # lista de streams (getRawData 0xFCB)
  otter_bridge.py getprop ID [ID ...]
  otter_bridge.py setprop ID VALOR               # escribe y vuelve a leer
  otter_bridge.py rawdata ID SALIDA.bin          # lee un bloque de datos crudos
  otter_bridge.py capture STREAM SEGUNDOS DIR    # STREAM: ir_l | ir_r | color
  otter_bridge.py keepalive [INTERVALO_S]        # heartbeat periódico (Ctrl+C para salir)

Se asume que la interfaz Wi-Fi ya está conectada a la red del puente (nmcli connection up scan-pocket).
"""
import os
import socket
import struct
import sys
import time

HOST = "192.168.193.1"
GVCP_PORT = 3956
CMD_PORT = 8090

HP_REQ_MAGIC = 0x4D47   # "GM"
HP_RESP_MAGIC = 0x4252  # "RB"
OP_GET_PROPERTY = 0x01
OP_SET_PROPERTY = 0x02
OP_HEARTBEAT = 0x05
OP_RAW_INIT, OP_RAW_READ, OP_RAW_FINISH = 0x11, 0x12, 0x13

STREAM_PORTS_ID = 0xFCB
FRAME_HEADER = 26
STREAMS = {
    "ir_l": (8556, "ir_l/1280_800_15_y8"),
    "ir_r": (8557, "ir_r/1280_800_15_y8"),
    "color": (8888, "color/1280_800_15_mjpg"),
}
OB_STREAM_TYPES = {1: "IR", 2: "COLOR", 3: "DEPTH", 4: "ACCEL", 5: "GYRO", 6: "IR_LEFT", 7: "IR_RIGHT"}


def discover(timeout=2.0):
    """Envía DISCOVERY_CMD de GVCP y devuelve las respuestas decodificadas."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    s.sendto(bytes.fromhex("4211000200000001"), (HOST, GVCP_PORT))
    found = []
    try:
        while True:
            d, addr = s.recvfrom(4096)
            p = d[8:]
            text = lambda a, b: p[a:b].split(b"\0")[0].decode(errors="replace")
            found.append({
                "ip": socket.inet_ntoa(p[36:40]),
                "mac": ":".join(f"{x:02x}" for x in p[10:16]),
                "manufacturer": text(72, 104),
                "model": text(104, 136),
                "pid": struct.unpack(">H", p[134:136])[0],
                "version": text(136, 168),
                "serial": text(216, 232),
            })
    except socket.timeout:
        pass
    return found


class HostProtocol:
    """Canal de comandos TCP 8090. Cabecera: <magic, tamaño en palabras de 16 bits, opcode, id>."""

    def __init__(self, host=HOST, port=CMD_PORT, timeout=3.0):
        self.sock = socket.create_connection((host, port), timeout)
        self.sock.settimeout(timeout)
        self.timeout = timeout
        self.nid = 0

    def close(self):
        self.sock.close()

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            d = self.sock.recv(n - len(buf))
            if not d:
                raise ConnectionError("el puente cerró la conexión")
            buf += d
        return buf

    def call(self, opcode, payload=b"", expect=None):
        """Devuelve (status, datos). status 0 = OK. expect = bytes de datos esperados (lecturas por bloques)."""
        self.sock.sendall(struct.pack("<HHHH", HP_REQ_MAGIC, len(payload) // 2, opcode, self.nid) + payload)
        self.nid = (self.nid + 1) & 0xFFFF
        magic, size, _, _ = struct.unpack("<HHHH", self._recv_exact(8))
        if magic != HP_RESP_MAGIC:
            raise ValueError(f"magic de respuesta inesperado 0x{magic:04x}")
        # En las lecturas por bloques (0x12) el campo tamaño no es fiable (a veces omite el status):
        # la respuesta trae siempre status (2 bytes) + los bytes pedidos.
        n = max(size * 2, expect + 2) if expect is not None else size * 2
        body = self._recv_exact(n)
        self._drain_padding()
        st = struct.unpack("<H", body[:2])[0]
        return st, body[2:2 + expect] if expect is not None else body[2:]

    def _drain_padding(self):
        """El puente rellena algunas respuestas con ceros (hasta 64 o 1024 bytes); se descartan."""
        self.sock.settimeout(0.05)
        try:
            while self.sock.recv(65536):
                pass
        except (socket.timeout, BlockingIOError):
            pass
        finally:
            self.sock.settimeout(self.timeout)

    def heartbeat(self):
        return self.call(OP_HEARTBEAT)

    def get_property(self, pid):
        """Devuelve dict con cur, max, min, default, step (enteros), o None si no está soportada."""
        st, d = self.call(OP_GET_PROPERTY, struct.pack("<I", pid))
        if st != 0 or len(d) < 20:
            return None
        return dict(zip(("cur", "max", "min", "default", "step"), struct.unpack("<5i", d[:20])))

    def set_property(self, pid, value):
        st, _ = self.call(OP_SET_PROPERTY, struct.pack("<Ii", pid, value))
        return st

    def get_raw_data(self, pid, chunk=512):
        st, d = self.call(OP_RAW_INIT, struct.pack("<I", pid))
        if st != 0:
            raise RuntimeError(f"getRawData 0x{pid:x}: status {st}")
        total = struct.unpack("<I", d[:4])[0]
        data = b""
        try:
            while len(data) < total:
                n = min(chunk, total - len(data))
                st, part = self.call(OP_RAW_READ, struct.pack("<III", pid, len(data), n), expect=n)
                if st != 0 or not part:
                    raise RuntimeError(f"lectura 0x{pid:x} offset {len(data)}: status {st}")
                data += part
        finally:
            self.call(OP_RAW_FINISH, struct.pack("<I", pid))
        return data


def parse_stream_ports(data):
    """Formato 0xFCB: u16 tamaño de entrada, u16 cantidad, entradas {u32 tipo de puerto, u32 OBStreamType, u16 puerto}."""
    size, count = struct.unpack("<HH", data[:4])
    out = []
    for i in range(count):
        e = data[4 + i * size: 4 + (i + 1) * size]
        ptype, stype, port = struct.unpack("<IIH", e[:10])
        out.append({"kind": {0x11: "data", 0x12: "rtsp"}.get(ptype, hex(ptype)),
                    "stream": OB_STREAM_TYPES.get(stype, stype), "port": port})
    return out


class RtspStream:
    """Cliente RTSP mínimo con RTP intercalado sobre TCP. Entrega cuadros completos (cabecera + datos)."""

    def __init__(self, port, path, host=HOST):
        self.host, self.port = host, port
        self.url = f"rtsp://{host}:{port}/{path}"
        self.sock = None
        self.session = None

    def _connect(self):
        if self.sock:
            self.sock.close()
        self.sock = socket.create_connection((self.host, self.port), 5)
        self.sock.settimeout(5)
        self.cseq, self.buf, self.session = 1, b"", None

    def _fill(self, cond, chunk=65536):
        """Lee del socket hasta que cond() sea cierta; error si el servidor cierra la conexión."""
        while not cond():
            d = self.sock.recv(chunk)
            if not d:
                raise ConnectionError("el servidor RTSP cerró la conexión")
            self.buf += d

    def _request(self, method, url, extra=""):
        msg = f"{method} {url} RTSP/1.0\r\nCSeq: {self.cseq}\r\nUser-Agent: OrbbecSDK\r\n"
        if self.session:
            msg += f"Session: {self.session}\r\n"
        self.sock.sendall((msg + extra + "\r\n").encode())
        self.cseq += 1
        # Puede haber paquetes RTP intercalados ('$') antes de la respuesta.
        while True:
            self._fill(lambda: len(self.buf) >= 4)
            if self.buf[0] == 0x24:
                ln = struct.unpack(">H", self.buf[2:4])[0]
                self._fill(lambda: len(self.buf) >= 4 + ln)
                self.buf = self.buf[4 + ln:]
                continue
            self._fill(lambda: b"\r\n\r\n" in self.buf)
            head, self.buf = self.buf.split(b"\r\n\r\n", 1)
            head = head.decode(errors="replace")
            length = [int(l.split(":")[1]) for l in head.split("\r\n") if l.lower().startswith("content-length")]
            if length:
                self._fill(lambda: len(self.buf) >= length[0])
                self.buf = self.buf[length[0]:]
            if not head.split("\r\n")[0].endswith("200 OK"):
                raise RuntimeError(f"{method} {url}: {head.splitlines()[0]}")
            return head

    def start(self, retries=6):
        # Si la sesión anterior en el mismo puerto aún se está cerrando, el servidor responde 401
        # (y cierra la conexión): reconectar y reintentar.
        for attempt in range(retries):
            try:
                self._connect()
                self._request("DESCRIBE", self.url, "Accept: application/sdp\r\n")
                head = self._request("SETUP", self.url + "/track1",
                                     "Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n")
                break
            except (RuntimeError, ConnectionError) as e:
                if ("401" not in str(e) and not isinstance(e, ConnectionError)) or attempt == retries - 1:
                    raise
                time.sleep(1.0)
        self.session = [l.split(":", 1)[1].strip().split(";")[0]
                        for l in head.split("\r\n") if l.lower().startswith("session")][0]
        self._request("PLAY", self.url + "/", "Range: npt=0.000-\r\n")

    def frames(self):
        """Generador de cuadros: bytes = cabecera de 26 bytes + datos (Y8 crudo o JPEG)."""
        cur = b""
        while True:
            try:
                self._fill(lambda: len(self.buf) >= 4, 262144)
                if self.buf[0] != 0x24:  # respuesta RTSP suelta: se descarta
                    self.buf = self.buf[1:]
                    continue
                ch, ln = self.buf[1], struct.unpack(">H", self.buf[2:4])[0]
                self._fill(lambda: len(self.buf) >= 4 + ln, 262144)
            except ConnectionError:
                return
            pkt, self.buf = self.buf[4:4 + ln], self.buf[4 + ln:]
            if ch != 0:
                continue
            cur += pkt[12 + 4 * (pkt[0] & 0x0F):]
            if pkt[1] & 0x80:  # bit marker = fin de cuadro
                yield cur
                cur = b""

    def stop(self):
        if not self.sock:
            return
        try:
            self.sock.sendall(f"TEARDOWN {self.url}/ RTSP/1.0\r\nCSeq: {self.cseq}\r\nSession: {self.session}\r\n\r\n".encode())
            time.sleep(0.3)
        except OSError:
            pass
        finally:
            self.sock.close()
            self.sock = None


def parse_frame(frame):
    """Cabecera: u32 contador @0, u32 timestamp en ms @10, u16 ancho @18, u16 alto @22."""
    counter = struct.unpack("<I", frame[0:4])[0]
    ts = struct.unpack("<I", frame[10:14])[0]
    w, h = struct.unpack("<H", frame[18:20])[0], struct.unpack("<H", frame[22:24])[0]
    return {"counter": counter, "timestamp_ms": ts, "width": w, "height": h, "data": frame[FRAME_HEADER:]}


def capture(stream, seconds, out_dir):
    """Guarda cuadros IR como .pgm y de color como .jpg en out_dir."""
    port, path = STREAMS[stream]
    os.makedirs(out_dir, exist_ok=True)
    rtsp = RtspStream(port, path)
    rtsp.start()
    n, t0 = 0, time.time()
    try:
        for raw in rtsp.frames():
            f = parse_frame(raw)
            base = os.path.join(out_dir, f"{stream}_{f['timestamp_ms']:010d}")
            if stream == "color":
                with open(base + ".jpg", "wb") as fh:
                    fh.write(f["data"])
            elif len(f["data"]) == f["width"] * f["height"]:
                with open(base + ".pgm", "wb") as fh:
                    fh.write(f"P5 {f['width']} {f['height']} 255\n".encode() + f["data"])
            n += 1
            if time.time() - t0 >= seconds:
                break
    finally:
        rtsp.stop()
    return n


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "discover":
        for d in discover():
            print(d)
        return 0
    if cmd == "capture":
        n = capture(args[0], float(args[1]), args[2])
        print(f"{n} cuadros guardados en {args[2]}")
        return 0
    hp = HostProtocol()
    try:
        if cmd == "heartbeat":
            st, d = hp.heartbeat()
            print(f"status {st}, estado {d.hex(' ')}")
        elif cmd == "ports":
            for p in parse_stream_ports(hp.get_raw_data(STREAM_PORTS_ID)):
                print(p)
        elif cmd == "getprop":
            for a in args:
                print(int(a, 0), hp.get_property(int(a, 0)))
        elif cmd == "setprop":
            pid, val = int(args[0], 0), int(args[1], 0)
            print(f"set {pid}={val}: status {hp.set_property(pid, val)}; ahora {hp.get_property(pid)}")
        elif cmd == "rawdata":
            data = hp.get_raw_data(int(args[0], 0))
            with open(args[1], "wb") as fh:
                fh.write(data)
            print(f"{len(data)} bytes -> {args[1]}")
        elif cmd == "keepalive":
            interval = float(args[0]) if args else 2.0
            while True:
                st, _ = hp.heartbeat()
                print(time.strftime("%H:%M:%S"), "heartbeat status", st, flush=True)
                time.sleep(interval)
        else:
            print(__doc__)
            return 1
    except KeyboardInterrupt:
        pass
    finally:
        hp.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
