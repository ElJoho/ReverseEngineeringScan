#!/usr/bin/env bash
# Corre analyze.sh desacoplado de la terminal, bloqueando la suspensión del PC.
# Uso: scripts/overnight.sh [win|mac|android|all]   -> log en analysis/<plataforma>/run.log
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-android}"
LOG="$ROOT/analysis/$TARGET/run.log"
[ "$TARGET" = all ] && LOG="$ROOT/analysis/run.log"

export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
export GHIDRA_INSTALL_DIR="${GHIDRA_INSTALL_DIR:-$HOME/tools/ghidra_12.1.4_PUBLIC}"
export REA_ANALYSIS_PROVIDER=ghidra
# 6 h por librería: liborbbec_scan.so (65 MB) supera 1 h
export REA_GHIDRA_STARTUP_TIMEOUT_MS="${REA_GHIDRA_STARTUP_TIMEOUT_MS:-21600000}"
# Ghidra lanza un proceso "decompile" por CPU (~1.6 GB c/u con liborbbec_scan.dylib):
# con 12 CPUs se agotó la RAM y el OOM killer cerró la sesión de GNOME (2026-10-26).
# Se limitan las CPUs visibles y se encierra todo en un scope con tope de memoria,
# así si se excede solo muere el análisis.
CPUS="${REA_CPUS:-0-3}"
MEMMAX="${REA_MEMMAX:-9G}"
# Aun con 4 CPUs, 5 decompiladores (~1.7 GB c/u) superaron los 9 GB. Estos analizadores son los
# que decompilan todo durante el análisis inicial (Call Convention ID también, visto 11:11); las funciones se decompilan luego bajo demanda.
export REA_GHIDRA_DISABLED_ANALYZERS="${REA_GHIDRA_DISABLED_ANALYZERS:-Decompiler Switch Analysis,Decompiler Parameter ID,Call Convention ID,Objective-C Message Analyzer}"

setsid nohup systemd-run --user --scope --quiet -p MemoryMax="$MEMMAX" -p MemorySwapMax=1G \
    taskset -c "$CPUS" systemd-inhibit --what=sleep:idle:handle-lid-switch --who=REA --why="Análisis de Ghidra" \
    bash -c "time '$ROOT/scripts/analyze.sh' '$TARGET'; echo \"exit=\$?\"; notify-send REA 'Análisis $TARGET terminado' 2>/dev/null" \
    > "$LOG" 2>&1 < /dev/null &
echo "Iniciado (PID $!). Log: ${LOG#"$ROOT"/}"
