# Visión general

## Objetivo
<!-- ¿Qué se quiere entender? p. ej. protocolo del escáner, formato de proyecto, calibración -->

## Componentes identificados

| Componente | Plataforma | Archivo | Rol |
|---|---|---|---|
| Unity IL2CPP | Android | `libil2cpp.so` | Lógica de la app (C#) |
| Orbbec SDK | Android | `libOrbbecSDK.so` | Driver de la cámara de profundidad |
| Escaneo | Android | `liborbbec_scan.so` | Reconstrucción |
| Depth engine | Android | `libmx6600_depth_engine.so`, `libsoc_depth_engine.so` | Cálculo de profundidad |
| Línea láser | Android | `libline_laser_param_preprocessing.so` | Parámetros láser |

## Preguntas abiertas
- 
