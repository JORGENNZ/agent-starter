# Proyectos de ejemplo

Un proyecto por máquina. Cada carpeta tiene `modelo.py` (paramétrico: cambia las medidas
de arriba y vuelve a correrlo), los archivos para fabricar y una `vista.png`.

Para regenerar: `pip install manifold3d trimesh ezdxf shapely matplotlib networkx lxml`
y luego `python3 taller/proyectos/<proyecto>/modelo.py`.

---

## 1. Brida de sujeción — Bambu Lab P2S
Carpeta `brida-sujecion/` · archivos `brida-mdf18.3mf` y `brida-mdf25.3mf`

Sujeta la hoja de MDF a la mesa de la CNC con un tornillo M8 en la ranura T.
La pata trasera mide lo mismo que el grosor del MDF, así aprieta parejo.

- **Material:** PETG (o ASA). No uses PLA: con la presión del tornillo se deforma con el tiempo.
- **Bambu Studio:** 4 paredes, relleno de 40 % (gyroid), capa de 0.2 mm. **Sin soportes**: ya viene boca abajo.
- **Cantidad:** imprime de 4 a 6 por grosor.
- **Por confirmar:** que tu mesa sea de ranuras T con tornillo M8. Si es de vacío o de otro tornillo, cambia `RANURA`.
- ⚠️ Pon las bridas fuera de la ruta de la fresa. En VCarve, dibújalas como zona prohibida.

## 2. Porta-fresas — Bambu Lab A2L
Carpeta `porta-fresas/` · archivo `porta-fresas.3mf`

Bloque de 112 × 52 × 32 mm con 6 fresas de 1/4" atrás (escalón alto) y 8 de 1/8" adelante.

- **Material:** PLA.
- **Bambu Studio:** 3 paredes, relleno de 15 %, capa de 0.2 mm, sin soportes.
- **En serie:** clic derecho → *Fill bed with copies* para llenar la cama, y manda la otra
  copia a la segunda A2L.
- Si las fresas quedan muy flojas o muy duras, cambia `HOLGURA` (ahora 0.35 mm).

## 3. Soporte para iPad — CNC 1325 + VCarve Pro
Carpeta `soporte-ipad-mdf/` · archivo `soporte-ipad.dxf` · acomodo en `hoja.png`

3 piezas de MDF de 18 mm que se arman por encastre, sin tornillos.
Ocupa 326 × 235 mm de hoja: salen unos 25 soportes por hoja de 1220 × 2440.

**Antes de cortar:** mide el MDF con calibrador. Si no mide 18.0, cambia `T` en `modelo.py`
y vuelve a generar el DXF (o pídemelo).

**En VCarve Pro:**
1. *Job Setup*: material de 18 mm, origen abajo a la izquierda, Z cero en la superficie del material.
2. *File → Import → Import Vectors* → `soporte-ipad.dxf` (en mm).
3. Selecciona los 3 vectores de la capa `CORTE_EXT` → *Profile Toolpath*:
   - Fresa plana de 1/4", **Outside/Right**, profundidad de 18.2 mm (para cortar completo)
   - Profundidad por pasada de 6 mm, 18 000 RPM y avance de 3000 mm/min
   - **Tabs:** 2 por pieza, de 6 mm de largo y 2 mm de alto
4. Postprocesador: **RichAuto (mm)** → guarda el archivo → cópialo a la USB del control RichAuto.
5. Corta primero **una sola pieza de prueba** y revisa que el encastre entre a presión con la mano.
   Si queda flojo, baja `HOLGURA`; si no entra, súbela.

Los círculos en las esquinas de las ranuras son **dog-bones**: con ellos la fresa redonda
deja la esquina a escuadra y la pieza entra completa.
