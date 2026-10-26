# ReverseEngineeringScan

Análisis de CrealityScan (Windows 4.3.3, macOS 4.3.3, Android 3.1.2) con [REA](https://github.com/morluto/rea)
para interoperabilidad con fines académicos y personales. **No se redistribuyen binarios ni código descompilado.**

## Estructura

| Carpeta | Contenido | ¿En git? |
|---|---|---|
| `exes/` | Instaladores originales | No |
| `extracted/{win,mac,android}/` | Contenido desempaquetado | No |
| `analysis/{win,mac,android}/` | Snapshots y evidencia JSON de REA | No |
| `notes/` | Hallazgos documentados | Sí |
| `scripts/` | Extracción y análisis reproducibles | Sí |

## Requisitos

```bash
sudo apt install innoextract p7zip-full cpio unzip openjdk-21-jdk
nvm install 22                 # Node >= 22.23.4
npm install -g rea-agents
npx rea-agents setup           # registra REA como MCP en Claude Code
# Ghidra: https://ghidra-sre.org
rea doctor --provider ghidra --json
```

## Uso

```bash
scripts/extract.sh   [win|mac|android|all]
scripts/analyze.sh   [win|mac|android|all]
```

| Archivo | Tipo | Punto de entrada |
|---|---|---|
| Windows `.exe` | Instalador Inno Setup 6.3.0 | ejecutable principal + DLLs |
| macOS `.pkg` | xar → Payload (cpio) | `CrealityScan.app` |
| Android `.apk` | Unity IL2CPP arm64 | `global-metadata.dat` + `libil2cpp.so`, `liborbbec_scan.so` |
