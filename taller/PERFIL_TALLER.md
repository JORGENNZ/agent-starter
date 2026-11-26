# Perfil del taller

Referencia para diseñar piezas pensando en las máquinas y materiales reales del taller.
Actualiza este archivo cuando cambie algo (máquina nueva, fresas, materiales).

## Impresoras 3D (Bambu Lab)

| Máquina | Cantidad | Uso principal | Volumen de impresión |
|---|---|---|---|
| P2S (cerrada) | 1 | Piezas técnicas: PETG, ABS/ASA, nylon, materiales con fibra de carbono | 256 × 256 × 256 mm |
| A2L | 2 | Producción en volumen y piezas grandes con PLA/PETG | **PENDIENTE: confirmar** |

**Reglas de diseño (por defecto):**
- Holgura para piezas que encajan: 0.2 mm por lado (0.15 si es ajuste apretado, 0.3 si se mueve libre)
- Pared mínima: 1.2 mm (3 líneas con boquilla de 0.4 mm)
- Voladizos de máximo 45° sin soporte; usar chaflanes en vez de filetes en la cara de abajo
- Barrenos para tornillos: M3 de paso = 3.4 mm; para inserto de calor M3 = 4.0–4.2 mm (según el inserto)
- Entregar en **3MF** (o STL) ya orientado para imprimir

## CNC router: Asia Robotics Shop Pro 1325

- Área de trabajo: unos 1300 × 2500 mm (hoja estándar de 1220 × 2440 mm)
- Controlador: **RichAuto DSP** (por confirmar el modelo, p. ej. A11)
- CAM: **VCarve Pro**, con el postprocesador de RichAuto en milímetros
- Husillo (spindle): potencia y RPM máximas **PENDIENTE: confirmar**

### Materiales
| Material | Grosor | Notas |
|---|---|---|
| MDF | 18 mm | Medir el grosor real con calibrador; suele variar ±0.3 mm |
| MDF | 25 mm | Ídem |
| Acrílico | **PENDIENTE: confirmar grosores** (comunes: 3, 5, 6 mm) | Fresa de 1 filo (O-flute) para que no se derrita |

### Fresas
**Estado: todavía no se sabe cuáles tiene.** Kit inicial recomendado:
1. **Plana de 1/4" (6.35 mm), 2 filos, compresión o upcut**: cortes y bolsillos en MDF
2. **Plana de 1/8" (3.175 mm), 2 filos**: detalles finos y letras pequeñas
3. **O-flute de 1 filo, 1/8" o 1/4"**: acrílico
4. **V-bit de 90° y de 60°**: grabado y letreros (V-carving)
5. **Bola de 1/8" (3.175 mm)**: acabado de relieves 3D

### Reglas de diseño (por defecto)
- Radio interno mínimo = radio de la fresa (1/4" → 3.2 mm). En ensambles, agregar **dog-bones** en esquinas internas
- Encastres (slots) en MDF: ancho = grosor real medido + 0.2 a 0.3 mm
- Tabs (puentes) para que la pieza no se suelte: 2 o 3 por pieza, de unos 6 × 2 mm
- Entregar **DXF en mm**, con vectores cerrados y una capa por operación: `CORTE_EXT`, `CORTE_INT`, `BOLSILLO`, `GRABADO_V`, `BARRENOS`
- Para relieves 3D: STL para importarlo como componente en VCarve Pro

### Parámetros de inicio (hay que probarlos y ajustarlos en la máquina)
| Material | Fresa | RPM | Avance | Profundidad por pasada |
|---|---|---|---|---|
| MDF | 1/4" de 2 filos | 18 000 | 3000–4000 mm/min | 6 mm |
| MDF | 1/8" de 2 filos | 18 000 | 1500–2000 mm/min | 2–3 mm |
| Acrílico | 1/4" O-flute | 16 000–18 000 | 2000–2500 mm/min | 2–3 mm |
| Acrílico | 1/8" O-flute | 18 000 | 1200–1500 mm/min | 1–1.5 mm |

## Pendientes por confirmar
- [ ] Volumen de impresión de la A2L
- [ ] Modelo exacto del RichAuto (A11, A18, B57...)
- [ ] Potencia y RPM máximas del husillo
- [ ] Fresas que tiene actualmente (o cuáles compró del kit)
- [ ] Grosores de acrílico que usa
