#!/usr/bin/env bash
# Desempaqueta los instaladores de exes/ en extracted/<plataforma>/.
# Uso: scripts/extract.sh [win|mac|android|all]   (por defecto: all)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXES="$ROOT/exes"
OUT="$ROOT/extracted"

WIN_EXE="$EXES/CrealityScan_win_4.3.3.exe"
MAC_PKG="$EXES/CrealityScan_mac_4.3.3.pkg"
APK="$EXES/CrealityScan_Android_3.1.2.apk"

need() {
    command -v "$1" >/dev/null 2>&1 || { echo "Falta '$1'. Instálalo con: sudo apt install $2" >&2; exit 1; }
}

# Devuelve 0 si el directorio ya tiene contenido además de .gitkeep
already_done() {
    [ -n "$(find "$1" -mindepth 1 -not -name .gitkeep -print -quit 2>/dev/null)" ]
}

extract_win() {
    need innoextract innoextract
    local dest="$OUT/win"
    if already_done "$dest"; then echo "[win] ya extraído en $dest (bórralo para repetir)"; return; fi
    echo "[win] Inno Setup -> $dest"
    innoextract --silent --output-dir "$dest" "$WIN_EXE"
}

extract_mac() {
    need 7z p7zip-full
    need cpio cpio
    local dest="$OUT/mac"
    if already_done "$dest"; then echo "[mac] ya extraído en $dest (bórralo para repetir)"; return; fi
    echo "[mac] pkg (xar) -> $dest/pkg"
    7z x -y -bso0 -o"$dest/pkg" "$MAC_PKG"

    local payload
    payload="$(find "$dest/pkg" -name Payload -type f | head -n1)"
    [ -n "$payload" ] || { echo "[mac] no se encontró Payload" >&2; exit 1; }

    echo "[mac] Payload -> $dest/root"
    mkdir -p "$dest/root"
    # El Payload suele ser cpio comprimido con gzip; si no, se deja que 7z lo intente
    if file -b "$payload" | grep -qi gzip; then
        (cd "$dest/root" && gunzip -dc "$payload" | cpio -idm --quiet)
    else
        7z x -y -bso0 -o"$dest/root" "$payload"
    fi
}

extract_android() {
    need unzip unzip
    local dest="$OUT/android"
    if already_done "$dest"; then echo "[android] ya extraído en $dest (bórralo para repetir)"; return; fi
    echo "[android] APK -> $dest"
    unzip -q -o "$APK" -d "$dest"
}

target="${1:-all}"
case "$target" in
    win)     extract_win ;;
    mac)     extract_mac ;;
    android) extract_android ;;
    all)     extract_android; extract_win; extract_mac ;;
    *)       echo "Uso: $0 [win|mac|android|all]" >&2; exit 1 ;;
esac

echo "Listo."
