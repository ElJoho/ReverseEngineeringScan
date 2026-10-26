# macOS: CrealityScan 4.3.3

Fuente: `exes/CrealityScan_mac_4.3.3.pkg` → `extracted/mac/root/Applications/`.
Binarios universales (x86_64 + arm64); `extract.sh mac` deja la parte x86_64 en
`extracted/mac/x86_64/` (con `scripts/thin_macho.py`) para Ghidra.

## Contenido

| Archivo | Tamaño (universal → x86_64) | Rol |
|---|---|---|
| `CrealityScan.app` | 1.6 GB total | App Unity IL2CPP (`GameAssembly.dylib`, `global-metadata.dat`) |
| `CrealityScan Diagnostics.app` | — | Herramienta de diagnóstico aparte (1.0.0, macOS 11+) |
| `PlugIns/liborbbec_scan.3.5.4.dylib` | 209 → 113 MB | Motor de escaneo (`obscan_*`) |
| `PlugIns/libOrbbecSDK.1.7.1.dylib` | 22 → 12 MB | OrbbecSDK 2.0.90 (build 20260924), fork Creality |
| `PlugIns/camera_user_calib` | 37 → 20 MB | **Ejecutable de calibración de usuario** |
| `PlugIns/libmx6600_depth_engine`, `libsoc_depth_engine`, `libline_laser_*`, `libsoc_linelaser_*`, `libcreate_distortion_lut` | < 1 MB c/u | Profundidad y línea láser (mismas que Android) |
| `PlugIns/libMoltenVK.dylib` | 10 MB | Vulkan sobre Metal (GPU) |

## Comparación con Android 3.1.2

| | Android | macOS |
|---|---|---|
| Tipos IL2CPP | 10 883 | 13 996 |
| Funciones en `OBScanNative` | 168 | **219** (todas las de Android + 51) |
| Nombres C++ en `liborbbec_scan` | 9 630 | **225 565** (ambas arquitecturas) |
| Dispositivos en OrbbecSDK | — | + **CR-Scan H** |

macOS conserva muchos más símbolos: es el mejor objetivo para decompilar `liborbbec_scan`.

### `obscan_*` solo en macOS (selección)

- Hardware: `obscan_scan_config_laser_current`, `obscan_scan_config_ir_exposure_time`,
  `obscan_device_management_select_active_device`, `..._get_active_device_register_state`
- Frames: `obscan_frame_get_timestamp`, `obscan_frame_get_frame_rate`
- IA: `obscan_session_AI_3D_generator`, `..._AI_body_completion`, `..._AI_head_restoration`
- 3D Gaussian Splatting: `obscan_session_3D_GS_mesh_export` (+ assembly `GaussianSplatting.dll`)
- Varilla de referencia con QR: `obscan_session_reference_rod_*`
- Otros: `obscan_session_merge`, `..._measure_mesh_surface_area`, `obscan_version`

Assemblies solo en macOS: `GaussianSplatting.dll`, `CrealityScan.Rendering.dll`,
`Orbbec.Creality.Account.*` (cuenta Creality), `Orbbec.PopGuide.dll`, `Backtrace.Unity.dll`.

## `camera_user_calib`

Contiene configuraciones de tableros de calibración embebidas
(`calib_board_user_tb2302_X_v1_6_0.ini`, `..._XZ_...`, `calib_board_config_produce_510/855.ini`) y
modelos de distorsión seleccionables: `0--k3 1--k6 2--KB 3--POLY` (Brown-Conrady k3/k6,
Kannala-Brandt, polinómico). Usa OpenCV y JSON (`CalibrateParamsMulti`).
Relevante para la fase de calibración del port a Ubuntu.

## `CrealityScan Diagnostics.app`

App Swift independiente (README en chino dentro de `Resources/`). Solo recopila diagnósticos:
Unity `Player.log`, logs de `Application Support/.../Logs` (incluye subcarpeta `Native`),
reportes de crash `.ips`, dumps de Backtrace/crashpad, info de sistema y SHA256 de las librerías.
No sube nada. No aporta al protocolo, pero confirma que el SDK nativo escribe logs propios
(`Logs/Native`): útiles si se ejecuta la app oficial mientras se captura el USB.

## Análisis de Ghidra

`scripts/overnight.sh mac` → `analysis/mac/`. Completado 2026-10-26 13:37 (39 min, pico 3.9 GB):
los 8 binarios x86_64 tienen snapshot. Los tres intentos previos murieron por falta de RAM;
se resolvió desactivando los analizadores de Ghidra que usan el decompilador (ver `overnight.sh`).
