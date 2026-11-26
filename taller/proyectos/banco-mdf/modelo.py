"""Banco armable (flat-pack) en MDF de 25 mm — CNC Asia Robotics 1325 + VCarve Pro.

2 patas que se cruzan en X por encastre a media madera + asiento redondo con un
bolsillo en cruz de 8 mm que las acomoda. Sin tornillos ni herrajes.

Capas del DXF (una operación de VCarve por capa):
  CORTE_EXT  perfil exterior, corte completo con tabs (patas y asiento)
  CORTE_INT  agarraderas de las patas, corte completo (se cortan ANTES que el exterior)
  BOLSILLO   cruz en la cara de abajo del asiento, 8 mm de profundidad
    python3 taller/proyectos/banco-mdf/modelo.py
"""
import math, os, sys
import ezdxf
import manifold3d as mf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import render, a_trimesh

# ---------------- Parámetros (mm) ----------------
T = 25.0              # grosor REAL del MDF (mídelo)
HOLGURA = 0.3         # encastre de las patas
HOLGURA_BOLSILLO = 0.5
R_FRESA = 3.175       # fresa plana de 1/4"
ALTO = 430            # alto de las patas (alto del asiento = ALTO - BOLSILLO + T)
ANCHO_ARRIBA = 300
ANCHO_ABAJO = 360
D_ASIENTO = 360
BOLSILLO = 8          # profundidad del bolsillo del asiento
R_AGARRE = 28         # agarraderas redondas en las patas
SEPARACION = 20
# -------------------------------------------------
S = T + HOLGURA

def dogbone(p, d):
    k = R_FRESA / math.sqrt(2)
    return Point(p[0] + d[0] * k, p[1] + d[1] * k).buffer(R_FRESA + 0.05, 32)

def pata(ranura_arriba):
    a, b = ANCHO_ARRIBA / 2, ANCHO_ABAJO / 2
    p = Polygon([(-b, 0), (b, 0), (a, ALTO), (-a, ALTO)])
    # esquinas exteriores redondeadas (se ve mejor y no astilla)
    p = p.buffer(-12, join_style=1).buffer(12, join_style=1)
    h = ALTO / 2
    if ranura_arriba:
        p = p.difference(box(-S / 2, h, S / 2, ALTO + 1))
        esq = [((-S / 2, h), (1, 1)), ((S / 2, h), (-1, 1))]
    else:
        p = p.difference(box(-S / 2, -1, S / 2, h))
        esq = [((-S / 2, h), (1, -1)), ((S / 2, h), (-1, -1))]
    for e, d in esq:
        p = p.difference(dogbone(e, d))
    agarres = [Point(x, ALTO * 0.72).buffer(R_AGARRE, 64) for x in (-88, 88)]
    return p, agarres

def bolsillo():
    L, w = ANCHO_ARRIBA + 2 * HOLGURA_BOLSILLO, T + HOLGURA_BOLSILLO
    c = unary_union([box(-L / 2, -w / 2, L / 2, w / 2), box(-w / 2, -L / 2, w / 2, L / 2)])
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = c.union(dogbone((sx * L / 2, sy * w / 2), (-sx, -sy)))
            c = c.union(dogbone((sx * w / 2, sy * L / 2), (-sx, -sy)))
    return c

asiento = Point(0, 0).buffer(D_ASIENTO / 2, 128)
pA, agA = pata(True)
pB, agB = pata(False)
bol = bolsillo()

aqui = os.path.dirname(os.path.abspath(__file__))

# ---------- DXF acomodado ----------
dx1 = ANCHO_ABAJO / 2
dx2 = dx1 + ANCHO_ABAJO + SEPARACION
dx3 = dx2 + ANCHO_ABAJO / 2 + SEPARACION + D_ASIENTO / 2
mov = lambda g, x, y=0: affinity.translate(g, x, y)
capas = {"CORTE_EXT": [mov(pA, dx1), mov(pB, dx2), mov(asiento, dx3, D_ASIENTO / 2)],
         "CORTE_INT": [mov(g, dx1) for g in agA] + [mov(g, dx2) for g in agB],
         "BOLSILLO": [mov(bol, dx3, D_ASIENTO / 2)]}
doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
for nombre, color in (("CORTE_EXT", 1), ("CORTE_INT", 5), ("BOLSILLO", 3), ("NOTAS", 8)):
    doc.layers.add(nombre, color=color)
msp = doc.modelspace()
for capa, gs in capas.items():
    for g in gs:
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": capa})
for txt, x, y in (("PATA A", dx1, 60), ("PATA B", dx2, 60), ("ASIENTO (bolsillo abajo)", dx3 - 70, 40)):
    msp.add_text(txt, height=10, dxfattribs={"layer": "NOTAS"}).set_placement((x - 30, y))
doc.saveas(os.path.join(aqui, "banco.dxf"))

# ---------- dibujo de la hoja ----------
fig, ax = plt.subplots(figsize=(9, 4.2), dpi=170)
estilos = {"CORTE_EXT": dict(color="#c8a97e", ec="#6b4f2a"), "CORTE_INT": dict(color="#f4f2ee", ec="#2b6cb0"),
           "BOLSILLO": dict(color="#a8875c", ec="#2f855a")}
for capa in ("CORTE_EXT", "BOLSILLO", "CORTE_INT"):
    for g in capas[capa]:
        x, y = g.exterior.xy; ax.fill(x, y, lw=1.2, **estilos[capa])
ax.plot([], [], color="#6b4f2a", label="CORTE_EXT"); ax.plot([], [], color="#2b6cb0", label="CORTE_INT")
ax.plot([], [], color="#2f855a", label="BOLSILLO 8 mm")
ax.legend(loc="upper right", fontsize=7)
ancho_total = dx3 + D_ASIENTO / 2
ax.set_title(f"Acomodo en MDF de {T:g} mm — {ancho_total:.0f} × {ALTO:.0f} mm", fontsize=10)
ax.set_aspect("equal"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hoja.png"), facecolor="white"); plt.close(fig)

# ---------- 3D armado ----------
def extruir(p, h=T):
    return mf.Manifold.extrude(mf.CrossSection([list(orient(p, 1.0).exterior.coords)[:-1]]), h)

def pata3d(p, ag):
    m = extruir(p)
    for g in ag:
        m -= extruir(g, T + 2).translate((0, 0, -1))
    return m.rotate((90, 0, 0)).translate((0, T / 2, 0))

A = pata3d(pA, agA)
B = pata3d(pB, agB).rotate((0, 0, 90))
z0 = ALTO - BOLSILLO
seat = extruir(asiento).translate((0, 0, z0)) - extruir(bol, BOLSILLO + 0.01).translate((0, 0, z0 - 0.005))
for n, (u, v) in {"A∩B": (A, B), "A∩asiento": (A, seat), "B∩asiento": (B, seat)}.items():
    print(f"Interferencia {n}: {(u ^ v).volume():.2f} mm³")
render([a_trimesh(A), a_trimesh(B), a_trimesh(seat)], os.path.join(aqui, "vista.png"),
       f"Banco armable — CNC, MDF {T:g} mm", colores=["#c8a97e", "#bf9d6e", "#d4b88f"], elev=20, azim=-35)
print(f"Alto del asiento: {z0 + T:.0f} mm | hoja usada: {ancho_total:.0f} × {ALTO} mm")
