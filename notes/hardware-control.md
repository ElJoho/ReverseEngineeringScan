# Control de hardware (macOS `liborbbec_scan.3.5.4.dylib`, x86_64)

Decompilado con `scripts/decompile.sh` (proyecto de Ghidra en `ghidra_projects/`, salida en
`analysis/mac/decompiled/`, ambos fuera de git). Direcciones = direcciones de Ghidra del slice x86_64.

## Capas

```
C#  OBScanNative.obscan_scan_config_laser_current(handle, int)        (P/Invoke)
C   _obscan_scan_config_laser_current            0x0000f130   -> vtable del escáner +0x48
C++ OBScanBase::config_laser_current             0x008b4600
C++ OBDeviceManagement::set_laser_current        0x0074a3e0
C++ device::OrbbecInternalDevice::set_laser_current  0x00231c00  -> propiedades del SDK
C++ device::<Modelo>DeviceHandle::*              (una clase por familia de escáner)
SDK libOrbbecSDK (fork Creality de OrbbecSDK v2) -> ob::Device::set*Property -> USB
```

Otros exports con el mismo patrón: `ir_exposure_time` (+0x28), `light_type` (+0x70, con arg extra `1`),
`combined_exposure_and_laser_current` (llama a `OBScanBase` directo). Retorno de error común: `0x32620107`
(handle nulo).

## Modelos y USB PID

De `device::registerDeviceHandle_<Clase>_<PID>` y la tabla `identities` (0x03e084d0) usada por
`device::device_type_from_pid` (0x00814d10):

| Modelo | PID | Clase |
|---|---|---|
| CR-Scan Ferret | 0x069c | FerretDeviceHandle |
| CR-Scan Ferret Pro | 0x06a1 (alias de 0x069c) | FerretDeviceHandle |
| CR-Scan Raptor | 0x06a8 | RaptorSerialDeviceHandle |
| CR-Scan Otter | 0x06da | OtterSerialDeviceHandle |
| CR-Scan Raptor X | 0x0c00 | RaptorSerialDeviceHandle |
| CR-Scan Raptor Pro | 0x0c03 | RaptorSerialDeviceHandle |
| CR-Scan Otter Lite | 0x0c04 | OtterSerialDeviceHandle |
| Sermoon X1 | 0x0c05 | SermoonX1DeviceHandle |
| Sermoon S1 | 0x0c06 | SermoonS1DeviceHandle |
| Sermoon P1 | 0x0c08 | SermoonP1DeviceHandle |
| CR-Scan Otter Lite Basic | 0x0c09 | OtterSerialDeviceHandle |
| Creality Pika | 0x0c0b | PikaDeviceHandle |
| Sermoon P1 Lite | 0x0c0d | SermoonP1DeviceHandle |
| M1 Ultra | 0x0c10 | PikaDeviceHandle |
| CR-Scan Raptor Pro Max | 0x0c11 | RaptorSerialDeviceHandle |
| (modo bootloader) | 0x0501 | AbstractDeviceHandle |

El VID no aparece en estas funciones; probablemente es el de Orbbec (0x2bc5). **Confirmar con `lsusb`**
cuando se conecte el escáner. Estos PID no están en la lista pública de OrbbecSDK_v2, por eso hay que
agregarlos para el port.

## Propiedades del SDK

Públicas (confirmadas en `Property.h` de OrbbecSDK_v2):

| ID | Nombre | Uso visto |
|---|---|---|
| 5 | OB_PROP_LASER_CURRENT_FLOAT | leída en set_laser_current / set_ir_exposure_time |
| 2000 / 2001 / 2002 | OB_PROP_COLOR_AUTO_EXPOSURE_BOOL / _EXPOSURE_INT / _GAIN_INT | set_color_exposure_time |
| 2025 / 2026 / 2027 | OB_PROP_IR_AUTO_EXPOSURE_BOOL / _EXPOSURE_INT / _GAIN_INT | set_ir_exposure_time, set_ir_gain (exposición limitada a ≤ 1000) |

Propias de Creality (no están en el SDK público):

| ID | Tipo | Evidencia | Nombre probable (inferido, sin confirmar) |
|---|---|---|---|
| 154 (0x9a), 155 (0x9b), 220 (0xdc), 240 (0xf0) | float | Se leen siempre junto con 5; `set_calib_laser_cur` escribe 154/155/220 según el tipo de dispositivo | LASER_2..5_CURRENT_FLOAT |
| 160 (0xa0) | int | set_ir_exposure_time escribe 60000 | ? |
| 161 (0xa1) | int | `RaptorSerialDeviceHandle::setBlueLightCurrent` escribe el valor normalizado a 1..1000; set_laser_current escribe 20 o 40 | corriente de la luz azul (LIGHT_IR_BLUE_ELECTRIC_INT?) |
| 162 (0xa2) | bool | set_ir_hdr_enable | OB_PROP_IR_HDR_BOOL? |

Los nombres de las propiedades Creality existen como cadenas en `libOrbbecSDK.1.7.1.dylib`
(`OB_PROP_LASER_2..5_*`, `OB_PROP_LIGHT_IR_BLUE_*`, `OB_PROP_IR_*_LINE_LASER_LIGHT_TYPE_INT`, …) pero no
hay una tabla nombre→ID en datos; falta decompilar la función del SDK que los asocia.

## Pendiente

- Mapear con certeza los IDs 154–240 (decompilar `libOrbbecSDK.1.7.1.dylib`).
- Recorrer los métodos por modelo (`configPropertyEx`, `setLaserCurrentDefaultValue`, `setIRWorkMode`,
  `setBlueLightLineType`) para el modelo del usuario.
- Confirmar VID/PID con `lsusb` y comparar con una captura USB.

## CR-Scan Otter (modelo del usuario, PID 0x06da)

Clase `device::OtterSerialDeviceHandle` (0x00463a40–0x004683d0). Comparte código con Otter Lite (0x0c04)
y Otter Lite Basic (0x0c09), que difieren en el segundo proyector.

### Propiedades que usa

| ID | Tipo | Función | Uso |
|---|---|---|---|
| 3 | bool | OB_PROP_LASER_BOOL (público) | proyector principal |
| 0xb2 (178) | bool | segundo proyector del Otter | se enciende en lugar del 3 según el modo de escaneo |
| 0x98 (152) | bool | OB_PROP_LASER_2_BOOL (por el mensaje de error) | segundo proyector en Otter Lite/Basic |
| 0x7e9 (2025) | bool | OB_PROP_IR_AUTO_EXPOSURE_BOOL | auto-exposición IR |
| 0x9d (157) | bool | encendido de la luz de relleno IR | `setIRFillLightEnable` |
| 0xa0 (160) | int 1..1000 | corriente de la luz de relleno IR | `setIRFillLightCurrent` |
| 0x9f (159) | int 1..1000 | corriente de la luz de relleno blanca (RGB) | `setColorFillLightCurrent` |
| 0xb3 (179) | int | modo de trabajo IR | `setIRWorkMode`, verifica leyendo de vuelta |
| 0xa4 (164), 0xb7 (183) | int | se ponen en 0 en `configProperty` | ? |
| 0x83 (131), 0xb1 (177) | bool | bandera de restaurar a fábrica | `restoreFactorySetting` |

Nota: los IDs 157/159/160 encajan con el orden de las cadenas `OB_PROP_LIGHT_IR_WHITE_BOOL`,
`OB_PROP_LIGHT_RGB_WHITE_ELECTRIC_INT`, `OB_PROP_LIGHT_IR_WHITE_ELECTRIC_INT`, pero es una inferencia.

### Lógica de proyectores (`setInfraredScanType(int tipo)`, 0x004642d0)

- `tipo == 2`: apaga ambos proyectores (3 = 0, 0xb2 = 0) y la auto-exposición IR (0x7e9 = 0).
- Otro tipo: enciende **uno** de los dos proyectores:
  - 0xb2 si `scanModeConfig+0xc < 3` y `scanModeConfig+0x10 == 1`;
  - si no, 3 (OB_PROP_LASER_BOOL).
  - Si el tipo de auto-exposición (`+0x2c`) es 2, activa la auto-exposición IR (0x7e9 = 1).
- Al final guarda el tipo en `+0x2c` y llama `AlgorithmProcessor::changeAEType`.

### Arranque (`configPropertyEx`, 0x00466300)

Leído del desensamblado (el decompilador pierde los argumentos porque desactivamos "Call Convention ID"):
`setPropertyValue<bool>` está en 0x0022f740 con `esi = id`, `edx = valor`.
- Según el modo, enciende 3 o 0xb2 (igual que arriba) y, si `+0x14 == 2`, la luz de relleno IR (vtable +0xd0).
- Si `scanModeConfig+0x78 != 0xff` (modo con luz de relleno): apaga 3 y 0xb2, enciende la luz de relleno IR
  (vtable +0xd0) y luego la blanca (vtable +0xb0).
- Otros mensajes de error en la función: `OB_PROP_IR_MIRROR_BOOL`, `OB_PROP_IR_LED_MASK_BOOL`, "white light".

### Pendiente para el Otter

- Identificar los campos de `scanModeConfig` (+0xc, +0x10, +0x14, +0x2c, +0x78) con los modos de la UI
  (tamaño de objeto, precisión, textura); probablemente vienen de `obscan_mode_config_init` y del XML.
- `configDeviceParam` (4889 bytes) y `setLaserCurrentDefaultValue`: valores por defecto de corriente.
- Sección `<CR-ScanOtter>` de `extracted/mac/root/Library/Creality/OrbbecSDKConfig_v1.0.xml` (línea 1932).
