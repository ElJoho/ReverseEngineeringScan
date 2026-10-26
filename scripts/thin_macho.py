#!/usr/bin/env python3
"""Extrae una arquitectura de un binario Mach-O universal (equivalente a `lipo -thin`).

Uso: thin_macho.py ENTRADA SALIDA [x86_64|arm64]   (por defecto: x86_64)
Si ENTRADA no es universal, se copia tal cual.
"""
import shutil
import struct
import sys

FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
CPU_TYPES = {"x86_64": 0x01000007, "arm64": 0x0100000C}


def thin(src, dst, arch):
    with open(src, "rb") as f:
        magic, count = struct.unpack(">II", f.read(8))
        if magic not in (FAT_MAGIC, FAT_MAGIC_64):
            shutil.copyfile(src, dst)
            return "no universal, copiado"
        entry = ">iiQQI4x" if magic == FAT_MAGIC_64 else ">iiIII"
        size = struct.calcsize(entry)
        for _ in range(count):
            cputype, _sub, offset, length, _align = struct.unpack(entry, f.read(size))
            if cputype == CPU_TYPES[arch]:
                f.seek(offset)
                with open(dst, "wb") as out:
                    while length:
                        chunk = f.read(min(length, 1 << 20))
                        out.write(chunk)
                        length -= len(chunk)
                return arch
    raise SystemExit(f"{src}: no contiene {arch}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    print(thin(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else "x86_64"))
