#!/usr/bin/env bash
# Muestra el estado del análisis de REA/Ghidra. Uso con refresco:
#   watch -n 5 scripts/progress.sh [win|mac|android]   (por defecto: android)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANA="$ROOT/analysis/${1:-android}"

echo "== Resultados en ${ANA#"$ROOT"/} =="
for log in "$ANA"/*.log; do
    [ -e "$log" ] || continue
    name="$(basename "${log%.log}")"
    [ "$name" = run ] && continue
    if [ -s "$ANA/$name.json" ]; then
        printf '  %-40s LISTO  (%s)\n' "$name" "$(du -h "$ANA/$name.json" | cut -f1)"
    elif grep -q failure_kind "$log" 2>/dev/null; then
        printf '  %-40s FALLÓ  (%s)\n' "$name" "$(grep -m1 -oP 'failure_message: \K.*' "$log")"
    else
        printf '  %-40s en curso o pendiente\n' "$name"
    fi
done

echo
echo "== Ghidra en ejecución =="
ps -eo etime,pcpu,rss,args | grep '[G]hidraClassLoader' \
    | awk '{printf "  tiempo %s  cpu %s%%  memoria %d MB\n", $1, $2, $3/1024}' \
    | grep . || echo "  (ninguno)"

echo
echo "== Última fase registrada por Ghidra =="
glog="$(ls -t /tmp/rea-ghidra-*/ghidra.log 2>/dev/null | head -n1)"
if [ -n "$glog" ]; then
    grep -vE 'LSDACallSiteTable|Failed to disassemble' "$glog" | tail -n 3 | cut -c1-150 | sed 's/^/  /'
    echo "  (último cambio del log: $(date -r "$glog" +%H:%M:%S))"
fi
