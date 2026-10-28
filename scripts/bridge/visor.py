#!/usr/bin/env python3
"""Visor en vivo del CR-Scan Otter por el puente Wi-Fi: IR izquierda, IR derecha y color en una ventana.

Uso: visor.py [--streams ir_l,ir_r,color] [--gain N] [--exposure N] [--stretch]
  --streams            qué streams mostrar (por defecto ir_l,ir_r). Con color, el Wi-Fi se satura y baja la tasa IR.
  --gain / --exposure  cambian la ganancia (2027) y la exposición IR (2026) mientras corre el visor
                       y restauran los valores anteriores al salir.
  --stretch            estira el contraste de las imágenes IR (útil con la configuración por defecto, muy oscura).
Teclas: q o Esc para salir.
Requiere numpy y opencv-python. Mantiene el puente despierto con heartbeat cada 2 s.
"""
import argparse
import os
import sys
import threading
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otter_bridge as ob  # noqa: E402

PROP_IR_EXPOSURE = 2026
PROP_IR_GAIN = 2027


class StreamThread(threading.Thread):
    """Recibe un stream RTSP y guarda el último cuadro decodificado."""

    def __init__(self, name):
        super().__init__(daemon=True)
        self.name, self.image, self.fps = name, None, 0.0
        self.running = True
        port, path = ob.STREAMS[name]
        self.rtsp = ob.RtspStream(port, path)

    def run(self):
        self.rtsp.start()
        t0, n = time.time(), 0
        for raw in self.rtsp.frames():
            if not self.running:
                break
            f = ob.parse_frame(raw)
            if self.name == "color":
                img = cv2.imdecode(np.frombuffer(f["data"], np.uint8), cv2.IMREAD_COLOR)
            elif len(f["data"]) == f["width"] * f["height"]:
                img = np.frombuffer(f["data"], np.uint8).reshape(f["height"], f["width"])
            else:
                continue
            self.image = img
            n += 1
            if time.time() - t0 >= 1.0:
                self.fps, t0, n = n / (time.time() - t0), time.time(), 0
        self.rtsp.stop()


def keepalive(stop):
    hp = ob.HostProtocol()
    while not stop.is_set():
        hp.heartbeat()
        stop.wait(2.0)
    hp.close()


def tile(img, label, fps, stretch, size=(640, 400)):
    if img is None:
        out = np.zeros((size[1], size[0], 3), np.uint8)
    else:
        if img.ndim == 2:
            if stretch:
                img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        out = cv2.resize(img, size)
    cv2.putText(out, f"{label}  {fps:.1f} fps", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gain", type=int)
    ap.add_argument("--exposure", type=int)
    ap.add_argument("--stretch", action="store_true")
    ap.add_argument("--streams", default="ir_l,ir_r")
    args = ap.parse_args()

    hp = ob.HostProtocol()
    saved = {}
    for pid, val in ((PROP_IR_GAIN, args.gain), (PROP_IR_EXPOSURE, args.exposure)):
        if val is not None:
            saved[pid] = hp.get_property(pid)["cur"]
            hp.set_property(pid, val)
    hp.close()

    stop = threading.Event()
    threading.Thread(target=keepalive, args=(stop,), daemon=True).start()
    streams = [StreamThread(n) for n in args.streams.split(",")]
    for s in streams:
        s.start()
    try:
        while True:
            row = np.hstack([tile(s.image, s.name, s.fps, args.stretch) for s in streams])
            cv2.imshow("CR-Scan Otter (puente Wi-Fi)", row)
            if cv2.waitKey(30) & 0xFF in (ord("q"), 27):
                break
    finally:
        for s in streams:
            s.running = False
        stop.set()
        time.sleep(0.5)
        cv2.destroyAllWindows()
        if saved:
            hp = ob.HostProtocol()
            for pid, val in saved.items():
                hp.set_property(pid, val)
            hp.close()
            print("valores restaurados:", saved)


if __name__ == "__main__":
    main()
