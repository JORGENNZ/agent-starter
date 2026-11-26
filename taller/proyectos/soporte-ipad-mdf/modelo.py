"""Soporte para iPad en MDF de 18 mm — CNC Asia Robotics 1325 + VCarve Pro.

3 piezas que se arman sin tornillos ni pegamento: 2 laterales + 1 travesaño unidos
por encastre a media madera. Las esquinas internas llevan dog-bones para que la
fresa de 1/4" deje el encastre a escuadra.

Salidas:
  soporte-ipad.dxf  -> importar en VCarve Pro (mm). Capa CORTE_EXT = perfil exterior.
  vista.png         -> soporte armado
  hoja.png          -> acomodo de las piezas
    python3 taller/proyectos/soporte-ipad-mdf/modelo.py
"""
import math, os, sys
import ezdxf
import manifold3d as mf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, box
from shapely import affinity
from shapely.geometry.polygon import orient
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import render, a_trimesh

# ---------------- Parámetros (mm) ----------------
T = 18.0              # grosor REAL del MDF (mídelo con calibrador)
HOLGURA = 0.25        # holgura del encastre
R_FRESA = 3.175       # fresa plana de 1/4"
ANCHO = 200           # ancho total del soporte (largo del travesaño)
ALTO_TRAV = 60        # alto del travesaño
RANURA_IPAD = 16      # ancho de la canal donde se apoya el iPad (con funda)
ANGULO = 65           # inclinación del iPad respecto a la mesa (grados)
ALTO = 155            # alto del respaldo
SEPARACION = 20       # entre piezas en la hoja (mayor que el diámetro de la fresa)
# -------------------------------------------------

S = T + HOLGURA                    # ancho de ranura
X_TRAV = 75                        # posición del travesaño en el lateral
y_canal = 18                       # fondo de la canal
x_canal = 28                       # inicio de la canal
x_resp = x_canal + RANURA_IPAD     # donde empieza el respaldo
x_top = x_resp + (ALTO - y_canal) / math.tan(math.radians(ANGULO))
BASE = x_top + 45

def dogbone(esquina, hacia):
    """Círculo en una esquina interna para que la fresa redonda la limpie."""
    d = R_FRESA / math.sqrt(2)
    return Point(esquina[0] + hacia[0] * d, esquina[1] + hacia[1] * d).buffer(R_FRESA + 0.05, 32)

def lateral():
    p = Polygon([(0, 0), (BASE, 0), (x_top + 16, ALTO), (x_top, ALTO),
                 (x_resp, y_canal), (x_canal, y_canal), (x_canal, 40), (10, 40), (0, 30)])
    a, b, h = X_TRAV, X_TRAV + S, ALTO_TRAV / 2
    p = p.difference(box(a, -1, b, h))                      # ranura desde abajo
    p = p.difference(dogbone((a, h), (1, -1))).difference(dogbone((b, h), (-1, -1)))
    # dog-bones de la canal del iPad
    p = p.difference(dogbone((x_canal, y_canal), (1, 1)))
    p = p.difference(dogbone((x_resp, y_canal), (-1, 1)))
    return p

def centros_laterales():
    return [T / 2 + 12, ANCHO - T / 2 - 12]

def travesano():
    p = box(0, 0, ANCHO, ALTO_TRAV)
    h = ALTO_TRAV / 2
    for c in centros_laterales():
        a, b = c - S / 2, c + S / 2
        p = p.difference(box(a, h, b, ALTO_TRAV + 1))      # ranura desde arriba
        p = p.difference(dogbone((a, h), (1, 1))).difference(dogbone((b, h), (-1, 1)))
    return p

aqui = os.path.dirname(os.path.abspath(__file__))
L, TR = lateral(), travesano()

# ---------- DXF acomodado ----------
piezas = [("LATERAL 1", L), ("LATERAL 2", affinity.translate(L, BASE + SEPARACION, 0)),
          ("TRAVESAÑO", affinity.translate(TR, 0, ALTO + SEPARACION))]
doc = ezdxf.new("R2010", setup=True)
doc.units = ezdxf.units.MM
doc.layers.add("CORTE_EXT", color=1)
doc.layers.add("NOTAS", color=8)
msp = doc.modelspace()
for nombre, p in piezas:
    msp.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
    c = p.representative_point()
    msp.add_text(nombre, height=6, dxfattribs={"layer": "NOTAS"}).set_placement((c.x - 20, c.y))
doc.saveas(os.path.join(aqui, "soporte-ipad.dxf"))

# ---------- dibujo de la hoja ----------
fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
for nombre, p in piezas:
    x, y = p.exterior.xy
    ax.fill(x, y, color="#c8a97e", ec="#6b4f2a", lw=1)
    c = p.representative_point(); ax.text(c.x, c.y, nombre, ha="center", fontsize=8)
minx, miny, maxx, maxy = (min(p.bounds[i] for _, p in piezas) if i < 2 else max(p.bounds[i] for _, p in piezas) for i in range(4))
ax.set_title(f"Acomodo en MDF de {T:g} mm — {maxx - minx:.0f} × {maxy - miny:.0f} mm")
ax.set_aspect("equal"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hoja.png"), facecolor="white"); plt.close(fig)

# ---------- vista 3D armado ----------
def extruir(p):
    return mf.Manifold.extrude(mf.CrossSection([list(orient(p, 1.0).exterior.coords)[:-1]]), T)

mallas = []
for c in centros_laterales():
    lat = extruir(L).rotate((90, 0, 0)).translate((0, c + T / 2, 0))
    mallas.append(a_trimesh(lat))
trav = extruir(TR).rotate((90, 0, 0)).rotate((0, 0, 90)).translate((X_TRAV + HOLGURA / 2, 0, 0))
mallas.append(a_trimesh(trav))
render(mallas, os.path.join(aqui, "vista.png"), f"Soporte para iPad — CNC, MDF {T:g} mm",
       colores=["#c8a97e", "#c8a97e", "#b08d5e"], azim=-130, elev=22)
print(f"Lateral: {BASE:.0f} × {ALTO} mm | Travesaño: {ANCHO} × {ALTO_TRAV} mm | ranura {S} mm")
