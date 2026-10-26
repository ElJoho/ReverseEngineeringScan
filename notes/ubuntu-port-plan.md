# Plan: CrealityScan en Ubuntu 26.04 LTS

Objetivo: escanear con un escáner Creality (CR-Scan) en Ubuntu 26.04 sin depender del software
de Creality, usando lo aprendido por ingeniería inversa solo para interoperabilidad.

Estado: Android analizado (ver `android-il2cpp.md`). Windows pendiente de extraer
(requiere innoextract compilado desde git, ver README).

## Arquitectura de CrealityScan (según Android 3.1.2)

```
UI Unity (C#, Assembly-CSharp)          -> NO se replica: se reemplaza por una app propia
  └─ OBScan.SDK (C#, P/Invoke)          -> mapa de la API: 168 funciones declaradas
      └─ liborbbec_scan.so  (obscan_*)  -> motor de escaneo propietario (58k funciones)
          ├─ libOrbbecSDK.so (ob_*)     -> driver de cámara: OrbbecSDK 2.0.90, fork Creality
          │   └─ libOrbbecGPL.so        -> libuvc/libusb (código GPL/LGPL)
          ├─ depth engines (mx6600, soc) + line-laser param libs -> cálculo de profundidad
          └─ OpenCV, OpenMP, OpenCL (Windows: CUDA)
```

Algoritmos identificados en `liborbbec_scan.so` (por cadenas): TSDF fusion, Incremental
Poisson Reconstruction, MLS smoothing (CUDA), normales en OpenCL, registro automático y por
pares de puntos, relleno de agujeros, texturizado. Formatos: `.ply`, `.obj`, `.stl`, `.3mf`, `.asc`.

Escáneres soportados: CR-Scan Otter, Otter Lite (Basic), Raptor, Raptor X, Raptor Pro,
Raptor Pro Max, Ferret, Ferret Pro (también "Creality Pika"). Conexión USB (UVC/libusb) y
WiFi bridge.

## Componentes a reemplazar en Linux

| Capa | Equivalente abierto en Ubuntu | Qué hay que averiguar por RE |
|---|---|---|
| Driver de cámara | OrbbecSDK_v2 (MIT, Linux x64) — **no** lista dispositivos Creality | PID/VID de cada CR-Scan, entradas de `OrbbecSDKConfig_v1.0.xml`, comandos vendor/UVC-XU, perfiles de stream |
| Control del láser / IR | (propio) | `ConfigIRCombinedExposureAndLaserCurrent` → qué comando `ob_*` / propiedad envía |
| Calibración (intrínsecos, extrínsecos, LUT de distorsión) | OpenCV | Dónde se leen del dispositivo (`obscan_calib_*`, `libcreate_distortion_lut.so`) y su formato |
| Profundidad desde línea láser (Raptor) | (propio, posible) | `libline_laser_param_preprocessing.so`, `libsoc_linelaser_param_processing.so` |
| Tracking / registro | Open3D (ICP, odometría RGB-D), marcadores con OpenCV | Parámetros de marcadores (`OBScanFrame.GetMarkers`) |
| Fusión | Open3D `ScalableTSDFVolume` (CUDA) | Tamaño de vóxel y truncamiento por modo de escaneo |
| Malla | PoissonRecon (mkazhdan) / Open3D | Parámetros de profundidad Poisson |
| UI | Python + Open3D GUI, o Qt | — |

## Fases

0. **Prueba rápida con Wine**: instalar el .exe de Windows en Wine. Probablemente falla el
   acceso USB/UVC, pero confirma si la UI arranca. Bajo costo.
1. **Extraer Windows** (innoextract desde git) y analizar: la versión de escritorio suele traer
   más símbolos y las DLL equivalentes (`OrbbecSDK.dll`, `obscan*.dll`) en x64 → comparables con
   la API de Android y más cercanas a Linux x64.
2. **Captura de USB** del escáner con el software oficial (Windows + Wireshark/USBPcap) mientras
   se escanea: es la forma más directa de obtener el protocolo. REA lee pcap vía TShark.
3. **Driver**: hacer que OrbbecSDK_v2 en Ubuntu reconozca el escáner (añadir PID/config) y
   obtener streams de profundidad/IR/color. **Hito clave**: si esto funciona, el resto es software
   abierto.
4. **Calibración**: leer intrínsecos/extrínsecos del dispositivo.
5. **Pipeline**: Open3D (odometría + TSDF) → malla → exportar STL/PLY/OBJ.
6. **UI** mínima y modos (objeto, cara, marcadores, línea láser).

## Hardware de este PC

Intel UHD 630 + **NVIDIA GTX 1660 Ti** (CUDA disponible para Open3D), 12 hilos.

## Pendiente de decidir

- Qué escáner se tiene (cambia todo: Otter = luz estructurada IR; Raptor = IR + línea láser azul).
- Si basta con un pipeline propio "suficientemente bueno" (Open3D) o se busca igualar la calidad
  del motor propietario.
