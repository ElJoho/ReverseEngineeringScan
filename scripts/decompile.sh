#!/usr/bin/env bash
# Decompila funciones de un binario con Ghidra headless, guardando el proyecto analizado
# en ghidra_projects/ para que las siguientes consultas no repitan el análisis (~25 min).
# Uso: scripts/decompile.sh <binario> <regex> <salida>
#   ej: scripts/decompile.sh extracted/mac/x86_64/liborbbec_scan.3.5.4.dylib '^obscan_' analysis/mac/decompiled/obscan
# Corre con tope de memoria y 4 CPUs (ver overnight.sh). Variables: REA_CPUS, REA_MEMMAX.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$(realpath "$1")"; REGEX="$2"; OUT="$(realpath -m "$3")"
GHIDRA="${GHIDRA_INSTALL_DIR:-$HOME/tools/ghidra_12.1.4_PUBLIC}"
PROJ_DIR="$ROOT/ghidra_projects"
PROJ="$(basename "$BIN" | tr -c 'A-Za-z0-9_\n' _)"
NAME="$(basename "$BIN")"
export GHIDRA_HEADLESS_MAXMEM="${GHIDRA_HEADLESS_MAXMEM:-4G}"
mkdir -p "$PROJ_DIR" "$OUT"

if [ -d "$PROJ_DIR/$PROJ.rep" ]; then
    MODE=(-process "$NAME" -noanalysis -readOnly)
else
    MODE=(-import "$BIN" -preScript DisableDecompilerAnalyzers.java)
fi

exec systemd-run --user --scope --quiet -p MemoryMax="${REA_MEMMAX:-9G}" -p MemorySwapMax=1G \
    taskset -c "${REA_CPUS:-0-3}" \
    "$GHIDRA/support/analyzeHeadless" "$PROJ_DIR" "$PROJ" "${MODE[@]}" \
    -scriptPath "$ROOT/scripts/ghidra" -postScript DecompileMatching.java "$REGEX" "$OUT" \
    -analysisTimeoutPerFile 21600
