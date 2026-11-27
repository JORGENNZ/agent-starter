# Proyectos de ejemplo

Un proyecto por máquina. Cada carpeta tiene `modelo.py` (paramétrico: cambia las medidas
de arriba y vuelve a correrlo), los archivos para fabricar y una `vista.png`.

Para regenerar:
```
pip install manifold3d trimesh ezdxf shapely matplotlib networkx lxml
(cd taller/render && npm install)      # render 3D con three.js (usa Chromium/Playwright)
python3 taller/proyectos/<proyecto>/modelo.py
```

| Máquina | Proyectos |
|---|---|
| P2S | Brida de sujeción · **Frasco con tapa de rosca** |
| A2L | Porta-fresas · **Colección de floreros** |
| CNC 1325 | Soporte para iPad (MDF 18) · **Banco armable (MDF 25)** · Silla de cuñas · **Sillón de costillas (1 hoja)** · **Cama para perro + comedero** · **Librero Skyline** |

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

---

## 4. Frasco con tapa de rosca — Bambu Lab P2S
Carpeta `frasco-rosca/` · archivos `frasco.3mf` y `tapa.3mf`

Frasco de unos 380 ml con rosca trapezoidal de 4 mm de paso y tapa estriada.
El modelo revisa que frasco y tapa no se encimen (0 mm³ de interferencia) y que la rosca sí agarre.

- **Material:** PETG (aguanta mejor los golpes y no se pone quebradizo).
- **Bambu Studio:** 3 paredes, relleno de 15 %, capa de 0.2 mm, **sin soportes**. La tapa ya viene boca abajo.
- Si la tapa entra muy dura, sube `HOLGURA` a 0.5. Si baila, bájala a 0.3.
- ⚠️ No es apto para alimentos tal cual: las capas impresas guardan bacterias.
  Úsalo para tornillería, especias en bolsa, dulces envueltos, etc.

## 5. Colección de floreros — Bambu Lab A2L
Carpeta `florero-torcido/` · archivos `florero-alto.3mf`, `florero-bajo.3mf` y `florero-botella.3mf`

Tres variantes de la misma familia, buenas para vender como colección. Cambia
`VARIANTES` en `modelo.py` (lóbulos, giro, escala) para sacar más modelos.

- **Material:** PLA (el seda o el mate se ven muy bien).
- **Bambu Studio:** activa **Spiral vase** (en *Others → Special mode*), con 3 capas de fondo
  y una boquilla de 0.4 mm. Sale una sola pared continua: rápido y con poco material.
- Si lo quieres para agua, imprime con 2 paredes normales en vez de modo espiral, o
  métele un tubo de ensayo o un vaso de vidrio adentro.
- La "botella" mide 200 mm de alto. Confirma que quepa en la A2L.

## 6. Banco armable — CNC 1325 + VCarve Pro
Carpeta `banco-mdf/` · archivo `banco.dxf` · acomodo en `hoja.png`

Banco de 447 mm de alto con 2 patas en X y un asiento redondo de 360 mm, sin herrajes.
Ocupa 1120 × 430 mm, así que de una hoja de 1220 × 2440 salen **5 bancos**.

**En VCarve Pro** (material de 25 mm, Z cero en la superficie):
1. Importa `banco.dxf`. Viene con 3 capas, una por operación.
2. **BOLSILLO** → *Pocket Toolpath*, fresa plana de 1/4", 8 mm de profundidad.
   Va en la cara de **abajo** del asiento: córtalo con la hoja tal cual; esa cara queda abajo al armar.
3. **CORTE_INT** (agarraderas) → *Profile*, **Inside**, a 25.2 mm, con 2 tabs.
4. **CORTE_EXT** → *Profile*, **Outside**, a 25.2 mm, con 3 o 4 tabs por pieza.
5. Orden: bolsillo → interiores → exteriores. Así la pieza sigue sujeta mientras se corta.
6. Pasadas de 6 mm (5 pasadas para 25 mm). Postprocesador: **RichAuto (mm)**.
7. Opcional: pásale una fresa de redondeo (roundover) al canto del asiento.

**Antes de cortar el banco completo:** mide el MDF. Si no mide 25.0, cambia `T`.
Corta las dos patas primero y prueba el encastre.

---

## 7. Silla de cuñas — CNC 1325 + VCarve Pro
Carpeta `silla-cunas/` · archivo `silla.dxf` · acomodo en `hoja.png`

Silla 100 % CNC, sin tornillos ni pegamento: 2 laterales esculpidos, asiento, respaldo,
2 travesaños y 14 cuñas (12 + 2 de repuesto). Todas las uniones son **espigas pasantes con cuña**:
la espiga atraviesa el lateral, la cuña entra por el agujero y jala todo hacia adentro.
Se arma y desarma a mano, y las cuñas a la vista son parte del diseño.

- Asiento a 419 mm · ancho total 564 mm · alto 822 mm · respaldo inclinado unos 20°
- **Toda la silla sale de una hoja de 1220 × 2440.**
- El modelo revisa que ninguna pieza se encime con otra y que cada espiga pase completa por su caja.

**Material, importante:** el diseño está en 25 mm. El MDF sirve para una silla decorativa
o de uso ocasional, pero **para uso diario usa triplay (contrachapado) de 18 mm o más**.
El MDF se debilita con la humedad y las patas trabajan de canto. Cambia `T` en `modelo.py`
y se recalculan cajas, espigas y cuñas.

**En VCarve Pro** (material de 25 mm, Z cero en la superficie):
1. Importa `silla.dxf`.
2. **CORTE_INT** (cajas, agujeros de cuña y agarradera) → *Profile*, **Inside**, fresa plana de 1/4",
   a 25.2 mm, con 2 tabs pequeños. **Primero estos.**
3. **CORTE_EXT** → *Profile*, **Outside**, a 25.2 mm. Usa 3 o 4 tabs en piezas grandes y 1 en cada cuña.
4. Postprocesador: **RichAuto (mm)**.

**Prueba antes de cortar la silla completa:** corta solo un travesaño y un pedazo de lateral
con su caja. La espiga debe entrar a mano, firme y sin martillo. Si entra muy floja, baja `HOLG`;
si no entra, súbela.

**Armado:**
1. Mete asiento, respaldo y travesaños en un lateral.
2. Pon el otro lateral encima.
3. Mete las cuñas con la parte delgada primero y dales un golpe suave con un mazo de hule.
4. Lija los cantos (o pásales una fresa de redondeo). Si quieres que las cuñas contrasten,
   píntalas o tíñelas de otro color.
5. Vuelve a apretar las cuñas después de unos días de uso.

---

## 8. Sillón de costillas — CNC 1325, MDF 18 mm, **una sola hoja**
Carpeta `sillon-costillas/` · archivo `hoja-1.dxf` · acomodo en `hojas.png` · vistas `vista*.png`

Sillón lounge de 15 costillas paramétricas, cada una distinta:
- **asiento en cuna:** baja 24 mm al centro, así abraza la cadera.
- **frente en ola:** el centro sale 18 mm más.
- **respaldo envolvente:** las costillas de afuera se adelantan 46 mm arriba, y el centro es 60 mm más alto.

**Estructura sin tornillos:**
- **2 caballetes** (las patas, abiertos hacia afuera). Cada costilla se asienta en ellos por una ranura desde abajo. El trasero va inclinado hacia atrás (pie a 712 mm) para que el sillón no se vaya de espaldas. El delantero va inclinado hacia adelante (pie a 60 mm), casi debajo de la orilla del asiento, para que no se vaya de frente si alguien se sienta en la punta.
- **1 cresta:** barra curva atrás del respaldo que amarra las puntas.

Medidas: 593 mm de ancho, 706 de fondo y 975 de alto. Asiento a unos 400 mm al frente.

**Diseñado para el corte:**
- Las costillas son bandas en "J" que se acomodan una dentro de otra, como cucharas.
- El sillón completo (18 piezas) sale de **una hoja de 1220 × 2440**.
- El acomodo se calcula solo (`taller/lib/nesting.py`): apila las costillas y busca el giro del bloque que deja lugar a las patas y la cresta.

**El modelo revisa:**
- que ninguna pieza se encime con otra;
- que cada caballete y la cresta entren en las 15 costillas;
- que ninguna pieza quede debajo del piso.

**En VCarve Pro** (MDF de 18 mm, Z cero en la superficie):
1. Importa `hoja-1.dxf`.
2. **GRABADO** → *Quick Engrave* o *Profile On*, con V-bit a 1 mm. Son los números de pieza (C01–C15, P1, P2, CR).
3. **CORTE_EXT** → *Profile*, **Outside**, fresa plana de 1/4", a 18.3 mm. Usa 3 tabs en cada costilla y 4 en patas y cresta.
4. Pasadas de 6 mm. Postprocesador: **RichAuto (mm)**.

**Prueba primero:** corta solo la costilla C08 y el caballete P1. La ranura debe entrar justa en el caballete.

**Armado:**
1. Para los 2 caballetes.
2. Baja las costillas en orden (C01 → C15) sobre sus ranuras.
3. Mete la cresta por atrás, a presión.
4. Lija o redondea los cantos de arriba de las costillas: es donde te sientas.

**Notas:**
- La cresta entra a presión. Si la quieres permanente, ponle una gota de pegamento blanco en cada ranura.
- Las patas apoyan en canto porque van inclinadas. Ponles regatones de fieltro.
- Para triplay (con veta) cambia `GIRO = 90`, para que las piezas no se giren en ángulos raros contra la veta.

---

## 9. Cama sofá para perro + comedero a juego — CNC 1325, MDF 18 mm
Carpeta `cama-perro/` · `python3 taller/proyectos/cama-perro/modelo.py S|M|L`

Archivos por talla: `cama-<T>-hoja-1.dxf`, `hoja-<T>.png`, `vista-<T>.png` y `vista-cojin-<T>.png`.
En la L, el comedero va aparte en `comedero-L.dxf`.

**Cama:**
- Laterales tipo brazo de sofá: altos atrás, bajos al frente, con patas.
- Respaldo con un hueso calado, que sirve de agarradera.
- Frente bajo con curva al centro para que el perro entre fácil.
- Piso elevado 8 cm, con un camino de huellas caladas que ventilan el cojín.

**Comedero elevado:** dos platos, patas con la misma curva y una huella. La cubierta queda 22 mm abajo
del borde de las patas, así los platos no se resbalan.

Todo se arma con espigas pasantes y cuñas, como la silla. Sin tornillos ni pegamento.

| Talla | Cojín | Perro | Cama (ancho × fondo × alto) | Platos | Hojas |
|---|---|---|---|---|---|
| S | 65 × 50 cm | hasta ~10 kg | 774 × 636 × 300 mm | 150 mm, alto 150 | 1 (cama + comedero) |
| M | 80 × 60 cm | ~10–25 kg | 924 × 736 × 380 mm | 180 mm, alto 240 | 1 (cama + comedero) |
| L | 100 × 70 cm | ~25–40 kg | 1124 × 836 × 450 mm | 220 mm, alto 330 | 1 (cama) + un sobrante de 1220 × 700 (comedero) |

**Revisiones del modelo (en las 3 tallas):**
- Ninguna pieza se encima con otra.
- Cada espiga pasa completa por su caja.
- Todas las piezas salen enteras.
- Ningún puente de material entre agujeros mide menos de 6 mm.

**Antes de cortar:**
- **Platos:** mide el diámetro exterior del borde de tus platos y pon ese valor en `COMEDERO[talla]["plato"]`.
  El hueco se hace 12 mm más chico para que el plato se apoye en su borde.
- **MDF:** mide el grosor real y pon el valor en `T`.

**En VCarve Pro:**
1. Importa el DXF.
2. **CORTE_INT** (cajas, huellas, hueso, agujeros de cuña) → *Profile Inside*, fresa plana de 1/4", a 18.3 mm, con 1 o 2 tabs. **Primero estos.**
3. **CORTE_EXT** → *Profile Outside*, a 18.3 mm, con 3 o 4 tabs por pieza y 1 por cuña.
4. Opcional: graba el nombre del perro en el respaldo con *V-Carve* (texto de VCarve, V-bit de 60° o 90°).

**Acabado (importante con perros):**
- El MDF se hincha con agua y orines. Sella **todas las caras y sobre todo los cantos** con 2 o 3 manos de
  poliuretano o pintura **base agua, no tóxica**.
- Si la cama va a estar en exterior o en zona húmeda, mejor usa MDF RH (verde, resistente a la humedad) o triplay.
- Redondea cantos y cuñas con lija o con una fresa de redondeo. Si el perro es mordelón, revisa las cuñas
  de vez en cuando.

---

## 10. Librero Skyline — CNC 1325, MDF 18 mm, 2 hojas (+ sujetalibros con el sobrante)
Carpeta `librero-skyline/` · archivos `hoja-1.dxf`, `hoja-2.dxf` · acomodo en `hojas.png`
· vistas `vista.png`, `vista-libros.png`, `vista-lado.png`

**Medidas:** 1178 de ancho × 338 de fondo × 1810 de alto. Son 4 paredes y 6 repisas.

**El diseño:**
- **Composición asimétrica:** las paredes van a 340, 360 y 340 mm, y no todas las repisas van de lado a lado.
  Por eso los nichos son distintos, y hay uno alto (660 mm) para vinilos, plantas o tocadiscos.
- **Más profundo abajo (320) que arriba (220),** con una ola suave en el frente de las paredes.
  El peso queda abajo y los libros grandes también.
- **Skyline:** las paredes sobresalen arriba a distintas alturas, con puntas redondas.
- **Repisas abombadas** entre pared y pared, con puntas redondas que sobresalen 60 mm.

**Armado sin herramientas:**
- Las uniones son encastre a media madera: la ranura de la pared abre al frente y la de la repisa abre atrás.
- Para las 4 paredes y mete cada repisa por el frente, deslizándola hacia atrás.

**Aprovechamiento:**
- **Hoja 1:** las 4 paredes, acomodadas una contra otra con la ola de su frente.
- **Hoja 2:** las repisas.
- Lo que sobra se llena con **sujetalibros a juego** (respaldo con ola + base, con espigas a presión).
  Caben 23 juegos y las hojas quedan al **78 % y 70 %**.
- Si prefieres guardar un retazo grande, baja `maximo` en la llamada a `rellenar()`.

**El modelo revisa:**
- que ninguna pieza se encime con otra;
- que los 22 cruces repisa/pared queden trabados;
- que todas las piezas salgan enteras;
- que no quede ningún puente de material menor a 6 mm.

**⚠️ Seguridad:** un librero de 1.8 m **siempre se ancla a la pared**. La repisa de arriba trae 2 barrenos
de 9 mm junto a la orilla trasera para taquete y pija, o para una correa antivuelco.

**En VCarve Pro:**
1. Importa cada hoja.
2. **CORTE_INT** (barrenos de anclaje y cajas de los sujetalibros) → *Profile Inside*. **Primero estos.**
3. **CORTE_EXT** → *Profile Outside*, fresa plana de 1/4", a 18.3 mm.
   Usa 4 o 5 tabs en las paredes y repisas, y 1 en cada pieza de sujetalibros.
4. **Prueba antes:** corta una repisa y una pared y revisa que la ranura entre justa. Mide el MDF y ajusta `T`.
