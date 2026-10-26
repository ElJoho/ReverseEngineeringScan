#!/usr/bin/env bash
# Corre REA sobre el contenido de extracted/ y guarda la evidencia en analysis/.
# Requiere: rea (npm install -g rea-agents) y Ghidra configurado.
# Uso: scripts/analyze.sh [win|mac|android|all]   (por defecto: all)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT="$ROOT/extracted"
ANA="$ROOT/analysis"
PROVIDER="${REA_ANALYSIS_PROVIDER:-ghidra}"

command -v rea >/dev/null 2>&1 || { echo "Falta 'rea'. Instálalo con: npm install -g rea-agents" >&2; exit 1; }

# Librerías nativas de Android con la lógica de escaneo
ANDROID_LIBS=(
    liborbbec_scan.so
    libOrbbecSDK.so
    libmx6600_depth_engine.so
    libsoc_depth_engine.so
    libline_laser_param_preprocessing.so
    libsoc_linelaser_param_processing.so
)

require_dir() {
    [ -d "$1" ] && [ -n "$(find "$1" -mindepth 1 -not -name .gitkeep -print -quit)" ] \
        || { echo "No hay contenido en $1. Corre primero: scripts/extract.sh" >&2; exit 1; }
}

# rea analyze con snapshot (se reutiliza si ya existe)
analyze_native() {
    local bin="$1" snap="$2"
    echo "  analyze $(basename "$bin")"
    rea analyze "$bin" --provider "$PROVIDER" --snapshot "$snap" >/dev/null
}

analyze_android() {
    local src="$EXT/android" dst="$ANA/android"
    require_dir "$src"
    echo "[android]"

    local meta="$src/assets/bin/Data/Managed/Metadata/global-metadata.dat"
    local il2cpp="$src/lib/arm64-v8a/libil2cpp.so"
    echo "  inspect-il2cpp-metadata"
    rea inspect-il2cpp-metadata "$meta" --binary "$il2cpp" --json > "$dst/il2cpp-metadata.json"

    for lib in "${ANDROID_LIBS[@]}"; do
        [ -f "$src/lib/arm64-v8a/$lib" ] && analyze_native "$src/lib/arm64-v8a/$lib" "$dst/${lib%.so}.json"
    done
}

analyze_win() {
    local src="$EXT/win" dst="$ANA/win"
    require_dir "$src"
    echo "[win]"

    # El ejecutable principal es el .exe más grande (excluye desinstaladores)
    local main
    main="$(find "$src" -iname '*.exe' -not -iname 'unins*' -printf '%s\t%p\n' | sort -rn | head -n1 | cut -f2)"
    [ -n "$main" ] || { echo "  no se encontró ningún .exe en $src" >&2; exit 1; }
    echo "  ejecutable principal: ${main#"$ROOT"/}"

    rea inspect-pe-imports      "$main" --json > "$dst/pe-imports.json"
    rea inspect-pe-certificates "$main" --json > "$dst/pe-certificates.json"
    analyze_native "$main" "$dst/$(basename "${main%.*}").json"

    # DLLs propias relacionadas con el escaneo (por nombre)
    find "$src" -iname '*.dll' | grep -iE 'orbbec|scan|depth|laser|creality' | while read -r dll; do
        analyze_native "$dll" "$dst/$(basename "${dll%.*}").json"
    done
}

analyze_mac() {
    local src="$EXT/mac/root" dst="$ANA/mac"
    require_dir "$src"
    echo "[mac]"

    local app
    app="$(find "$src" -maxdepth 3 -name '*.app' -type d | head -n1)"
    [ -n "$app" ] || { echo "  no se encontró ningún .app en $src" >&2; exit 1; }
    echo "  bundle: ${app#"$ROOT"/}"
    analyze_native "$app" "$dst/$(basename "${app%.app}").json"
}

target="${1:-all}"
case "$target" in
    win)     analyze_win ;;
    mac)     analyze_mac ;;
    android) analyze_android ;;
    all)     analyze_android; analyze_win; analyze_mac ;;
    *)       echo "Uso: $0 [win|mac|android|all]" >&2; exit 1 ;;
esac

echo "Evidencia guardada en ${ANA#"$ROOT"/}/"
