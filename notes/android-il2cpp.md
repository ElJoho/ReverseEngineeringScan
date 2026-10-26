# Android: clases IL2CPP

Fuente: `analysis/android/il2cpp-metadata.json` (`rea inspect-il2cpp-metadata`, metadata v31,
10 883 tipos, 75 840 métodos, 66 assemblies).

## Assemblies propios de la app

| Assembly | Tipos | Notas |
|---|---|---|
| `Assembly-CSharp.dll` | 1487 | UI y lógica de la app (mayormente namespace global) |
| `Framework.dll` | 321 | `Orbbec.Framework` (MVVM, Rpc, Network) |
| `OBScan.SDK.dll` | 135 | Wrapper C# del SDK de escaneo nativo |
| `OBScan.Base.dll` | 13 | Tipos base del SDK |
| `websocket-sharp.dll` | 82 | Servidor/cliente WebSocket |
| `zxing.unity.dll` | 194 | Lectura de QR (calibración) |

## Hallazgos

| Qué | Archivo | Dirección / símbolo | Evidencia (analysis/...) |
|---|---|---|---|
| API C nativa del escáner: 168 funciones P/Invoke `obscan_*` | `OBScan.SDK.dll` → `liborbbec_scan.so` (probable) | `OBScan.SDK.OBScanNative` | `android/il2cpp-metadata.json` |
| Contexto / sesiones / escaneos | `OBScan.SDK.dll` | `OBScanContext`, `OBScanSession`, `OBScanTarget` | idem |
| Gestión de dispositivo: firmware, recovery, backup de parámetros | `OBScan.SDK.dll` | `OBScanDeviceManagement.DeviceUpgrade`, `BootInRecoveryMode`, `BackupDeviceParam` | idem |
| Calibración con QR y tablero | `OBScan.SDK.dll` | `OBScanCalib`, `OBScanCalibTarget` | idem |
| Frames: nube de puntos, pose, marcadores | `OBScan.SDK.dll` | `OBScanFrame.GetPointCloud`, `GetPose`, `GetMarkers` | idem |
| Registro y edición de malla | `OBScan.SDK.dll` | `OBScanRegistration`, `OBScanEditMesh` | idem |

## Detalle

`OBScanTarget` expone la configuración del hardware: `ConfigIRCombinedExposureAndLaserCurrent`,
`ConfigColorExposureTime`, `ConfigDepthRange`, `ConfigColorFillLight`, `ConfigLightType`.

## Librerías nativas (Ghidra, 2026-10-26)

| Librería | Funciones | Exportadas | API pública |
|---|---|---|---|
| `liborbbec_scan.so` | 58 154 | 4 479 | **194 `obscan_*`** (confirma el P/Invoke de `OBScanNative`) |
| `libOrbbecSDK.so` | 24 419 | 8 683 | 267 `ob_*` (Orbbec SDK de la cámara) |
| `libmx6600_depth_engine.so` | 865 | | |
| `libsoc_depth_engine.so` | 578 | | |
| `libline_laser_param_preprocessing.so` | 600 | | |
| `libsoc_linelaser_param_processing.so` | 619 | | |

`obscan_*` por grupo: scan 49, session 41, device 32, context 23, debug 19, edit 16, calib 16,
frame 13, get 9, registration 6, project 6, image 5.

Las 26 funciones `obscan_*` que no declara `OBScanNative` (194 vs 168) son candidatas a API oculta
(p. ej. `obscan_debug_*`).

Siguiente paso: decompilar las `obscan_*` según el objetivo (protocolo, formato, calibración).
