"""Librero Skyline — 100 % CNC, MDF de 18 mm, sin tornillos.

4 paredes verticales a distancias distintas + 6 repisas, unidas por encastre a media
madera. Cada repisa entra por el frente y se desliza hacia atrás (una por una).
- Más profundo abajo (320) y más delgado arriba (220): peso abajo, se ve ligero.
- Las paredes sobresalen arriba a distintas alturas con puntas redondas (skyline).
- Repisas con el frente abombado entre paredes y puntas redondas que sobresalen.
- Nichos de distintos tamaños, uno alto (660 mm) para vinilos o plantas.
- Lo que sobra de las hojas se llena con sujetalibros a juego.

SEGURIDAD: un librero alto SIEMPRE se ancla a la pared (barrenos en la repisa de arriba).

Capas: CORTE_INT (barrenos de anclaje, cajas de sujetalibros) -> primero; CORTE_EXT.
    python3 taller/proyectos/librero-skyline/modelo.py
"""
import math, os, sys
import numpy as np
import ezdxf
import manifold3d as mf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, box, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import render, a_trimesh
from lib.nesting import acomodar, aprovechamiento, rellenar

# ---------------- Parámetros (mm) ----------------
T = 18.0
HOLG = 0.3
R_FRESA = 3.175
PROF_ABAJO, PROF_ARRIBA = 320, 220      # profundidad de las paredes abajo y arriba
H = 1650                                # altura de referencia (repisa de arriba ~1640)
X_PAREDES = [0, 340, 700, 1040]         # cara izquierda de cada pared
TOPES = [1735, 1810, 1700, 1770]        # altura de cada pared (skyline)
REPISAS = [  # (z de la cara de abajo, primera pared, última pared)
    (70, 0, 3), (400, 0, 3), (730, 0, 2), (1060, 0, 3), (1340, 1, 3), (1622, 0, 3)]
VUELO = 60                              # cuánto sobresale la repisa después de la última pared
ABOMBADO = 18                           # cuánto sale el frente de la repisa entre paredes
HOJA = (1220, 2440)
# -------------------------------------------------
S = T + HOLG
r = R_FRESA
xc = [x + T / 2 for x in X_PAREDES]     # centro de cada pared

def prof(z):
    """Profundidad de las paredes a la altura z (frente con una ola suave)."""
    base = PROF_ABAJO - (PROF_ABAJO - PROF_ARRIBA) * min(z, H) / H
    return base + 10 * math.sin(2 * math.pi * z / 560)

def dogbone(c, d):
    d = np.array(d, float); d /= np.linalg.norm(d)
    return Point(c[0] + d[0] * r, c[1] + d[1] * r).buffer(r + 0.05, 32)

# ---------- paredes (y = profundidad desde la pared del cuarto, z = altura) ----------
def pared(k):
    top = TOPES[k]
    zs = np.linspace(0, top - 60, 80)
    frente = [(prof(z), z) for z in zs]
    yt = prof(top - 60)
    punta = [(yt / 2 + (yt / 2) * math.cos(a), top - 60 + 60 * math.sin(a)) for a in np.linspace(0, math.pi, 30)]
    p = Polygon([(0, 0)] + frente + punta[1:] + [(0, top - 60)]).buffer(0)
    # patas: arco entre pata trasera y delantera
    d0 = prof(0)
    arco = [(y, 45 * math.sin(math.pi * (y - 55) / (d0 - 110)) ** 0.6) for y in np.linspace(55, d0 - 55, 30)]
    p = p.difference(Polygon([(55, -10)] + arco + [(d0 - 55, -10)]).buffer(8, join_style=1).buffer(-8, join_style=1))
    p = p.buffer(-6, join_style=1).buffer(6, join_style=1)
    cortes = []
    for (z, a, b) in REPISAS:
        if a <= k <= b or (k == b + 1 and False):
            ym = prof(z) / 2
            z0, z1 = z - HOLG / 2, z + T + HOLG / 2
            cortes += [box(ym, z0, prof(z) + 60, z1), dogbone((ym, z0), (1, 1)), dogbone((ym, z1), (1, -1))]
    return p.difference(unary_union(cortes))

# ---------- repisas (x = a lo ancho, y = profundidad) ----------
def repisa(z, a, b):
    d = prof(z)
    x0, x1 = xc[a] - T / 2 - VUELO, xc[b] + T / 2 + VUELO
    xs = np.linspace(x0, x1, 200)
    def frente(x):
        for i in range(a, b):
            l, rr = xc[i] + T / 2 + 6, xc[i + 1] - T / 2 - 6
            if l <= x <= rr:
                return d + ABOMBADO * math.sin(math.pi * (x - l) / (rr - l)) ** 2
        return d
    p = Polygon([(x0, 0)] + [(x, frente(x)) for x in xs] + [(x1, 0)]).buffer(0)
    p = p.buffer(-25, join_style=1).buffer(25, join_style=1)       # puntas redondas
    p = p.union(box(x0 + 30, 0, x1 - 30, 30))                      # la orilla de atrás queda recta
    cortes = []
    ym = d / 2
    for i in range(a, b + 1):
        u0, u1 = xc[i] - S / 2, xc[i] + S / 2
        cortes += [box(u0, -10, u1, ym), dogbone((u0, ym), (1, -1)), dogbone((u1, ym), (-1, -1))]
    return p.difference(unary_union(cortes))

piezas2d = {}
for k in range(len(X_PAREDES)):
    piezas2d[f"PARED-{k+1}"] = pared(k)
for j, (z, a, b) in enumerate(REPISAS):
    g = repisa(z, a, b)
    if j == len(REPISAS) - 1:   # barrenos de anclaje a la pared en la repisa de arriba
        for i in (a + 1, b - 1):
            g = g.difference(Point((xc[i] + xc[i - 1 if i > a else i + 1]) / 2 + 0, 25).buffer(4.5, 32))
    piezas2d[f"REPISA-{j+1}"] = g

# ---------- 3D ----------
def ext(poly, h=T):
    poly = orient(poly, 1.0)
    return mf.Manifold.extrude(mf.CrossSection([list(poly.exterior.coords)[:-1]] +
                                                [list(q.coords)[:-1] for q in poly.interiors]), h)

def colocar(m, O, eu, ev, ew, h=T):
    eu, ev, ew, O = (np.asarray(a_, float) for a_ in (eu, ev, ew, O))
    if np.linalg.det(np.column_stack([eu, ev, ew])) < 0:
        O, ew = O + ew * h, -ew
    return m.transform(np.column_stack([eu, ev, ew, O]).tolist())

X, Y, Z = np.eye(3)
p3d = {}
for k, x in enumerate(X_PAREDES):
    p3d[f"PARED-{k+1}"] = colocar(ext(piezas2d[f"PARED-{k+1}"]), [x, 0, 0], Y, Z, X)
for j, (z, a, b) in enumerate(REPISAS):
    p3d[f"REPISA-{j+1}"] = colocar(ext(piezas2d[f"REPISA-{j+1}"]), [0, 0, z], X, Y, Z)
nom = list(p3d)
peor = max((p3d[u] ^ p3d[v]).volume() for i, u in enumerate(nom) for v in nom[i + 1:])
print(f"Interferencia máxima entre piezas: {peor:.3f} mm³")
# cada cruce repisa/pared debe estar trabado: la repisa ocupa la ranura de la pared
cruces = 0
for j, (z, a, b) in enumerate(REPISAS):
    for k in range(a, b + 1):
        lleno = colocar(ext(Polygon([(0, z - 5), (prof(z) + 40, z - 5), (prof(z) + 40, z + T + 5), (0, z + T + 5)])),
                        [X_PAREDES[k], 0, 0], Y, Z, X)
        v = (p3d[f"REPISA-{j+1}"] ^ lleno).volume()
        cruces += v > 0.4 * T * T * prof(z) / 2
print(f"Cruces repisa/pared trabados: {cruces} de {sum(b - a + 1 for _, a, b in REPISAS)}")
zmin = min(p3d[k].bounding_box()[2] for k in nom)
print(f"Punto más bajo: {zmin:.2f} mm")

# ---------- render ----------
aqui = os.path.dirname(os.path.abspath(__file__))
mad = "#dcc19a"
def libros(x0, x1, z, d, semilla):
    rng = np.random.default_rng(semilla); out = []; x = x0 + 4
    while x < x1 - 30:
        w = rng.uniform(18, 42); h = rng.uniform(0.62, 0.95) * min(300, d * 1.2)
        if x + w > x1 - 4: break
        out.append(mf.Manifold.cube((w - 1.5, d * rng.uniform(0.6, 0.78), h)).translate((x, d * 0.08, z + T)))
        x += w
    return out
deco, cols_deco = [], []
paleta = ["#3d5a80", "#ee6c4d", "#98c1d9", "#293241", "#e0c068", "#6a994e", "#bc4749"]
rng = np.random.default_rng(3)
for j, (z, a, b) in enumerate(REPISAS[:-1]):
    for i in range(a, b):
        if rng.random() < 0.75:
            l, rr = xc[i] + T / 2, xc[i + 1] - T / 2
            ancho = (rr - l) * rng.uniform(0.45, 0.85)
            x0 = l if rng.random() < 0.5 else rr - ancho
            for m in libros(x0, x0 + ancho, z, prof(z), j * 10 + i):
                deco.append(m); cols_deco.append(paleta[len(deco) % len(paleta)])
mallas = [a_trimesh(p3d[k]) for k in nom]
render(mallas, os.path.join(aqui, "vista.png"), "Librero Skyline — CNC, MDF 18 mm", colores=[mad],
       elev=14, azim=-62, zoom=1.0)
render(mallas + [a_trimesh(m) for m in deco], os.path.join(aqui, "vista-libros.png"), "Librero Skyline — en uso",
       colores=[mad] * len(mallas) + cols_deco, elev=8, azim=-75, zoom=0.98,
       extras=[None] * len(mallas) + [{"aristas": False, "rugosidad": 0.8}] * len(deco))
render(mallas, os.path.join(aqui, "vista-lado.png"), "Librero Skyline — perfil", colores=[mad],
       elev=4, azim=-150, zoom=1.0)

# ---------- acomodo + sujetalibros en el sobrante ----------
hojas = acomodar(list(piezas2d.items()), hoja=HOJA, paso_giro=90, res=4.0, separacion=11)
ap0 = aprovechamiento(hojas, HOJA)

def sujetalibros(k):
    """Un sujetalibros = respaldo con ola + base, unidos por 2 espigas a presión."""
    ancho, alto, fondo = 130, 175, 150
    tope = [(x, alto - 28 + 22 * math.sin(math.pi * x / ancho + 0.6) ** 2) for x in np.linspace(0, ancho, 30)]
    resp = Polygon([(0, 0)] + tope + [(ancho, 0)]).buffer(-8, join_style=1).buffer(8, join_style=1)
    resp = resp.union(box(18, -(T - 0.5), 48, 1)).union(box(ancho - 48, -(T - 0.5), ancho - 18, 1))
    base = box(0, 0, ancho, fondo).buffer(-10, join_style=1).buffer(10, join_style=1)
    for (u0, u1) in ((18, 48), (ancho - 48, ancho - 18)):
        cs = [(u0 - HOLG / 2, 10), (u1 + HOLG / 2, 10), (u1 + HOLG / 2, 10 + S), (u0 - HOLG / 2, 10 + S)]
        base = base.difference(unary_union([Polygon(cs)] + [dogbone(c, d) for c, d in zip(cs, [(1, 1), (-1, 1), (-1, -1), (1, -1)])]))
    return [(f"SL{k+1}-A", resp), (f"SL{k+1}-B", base)]

n_sl = rellenar(hojas, sujetalibros, hoja=HOJA, separacion=11, giros=range(0, 360, 30))
ap = aprovechamiento(hojas, HOJA)
area_lib = sum(g.area for g in piezas2d.values()) / 1e6
print(f"Librero: {len(piezas2d)} piezas, {area_lib:.2f} m² | hojas: {len(hojas)} | "
      f"aprovechamiento solo librero: {', '.join(f'{a*100:.0f}%' for a in ap0)}")
print(f"+ {n_sl} sujetalibros en el sobrante -> aprovechamiento: {', '.join(f'{a*100:.0f}%' for a in ap)}")

fig, axs = plt.subplots(1, len(hojas), figsize=(4.6 * len(hojas), 8.6), dpi=170, squeeze=False)
for k, ps in enumerate(hojas):
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for nm, cc in (("CORTE_EXT", 1), ("CORTE_INT", 5)):
        doc.layers.add(nm, color=cc)
    msp = doc.modelspace(); ax = axs[0][k]
    ax.add_patch(plt.Rectangle((0, 0), *HOJA, fc="#f7f4ee", ec="#999", ls="--"))
    for p in ps:
        g = p["geom"]
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
        for q in g.interiors:
            msp.add_lwpolyline(list(q.coords), close=True, dxfattribs={"layer": "CORTE_INT"})
        xx, yy = g.exterior.xy
        ax.fill(xx, yy, fc="#8f6a42" if p["nombre"].startswith("SL") else mad, ec="#5a4026", lw=0.5)
        for q in g.interiors:
            xx, yy = q.xy; ax.fill(xx, yy, fc="#f7f4ee", ec="#2b6cb0", lw=0.4)
        if not p["nombre"].startswith("SL"):
            c = g.representative_point(); ax.text(c.x, c.y, p["nombre"], ha="center", fontsize=6, rotation=0)
    doc.saveas(os.path.join(aqui, f"hoja-{k+1}.dxf"))
    ax.set_title(f"Hoja {k+1}: {ap[k]*100:.0f}% en piezas", fontsize=9)
    ax.set_aspect("equal"); ax.set_xlim(-20, HOJA[0] + 20); ax.set_ylim(-20, HOJA[1] + 20); ax.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hojas.png"), facecolor="white"); plt.close(fig)
ancho_tot = xc[-1] + T / 2 + VUELO - (xc[0] - T / 2 - VUELO)
print(f"Medidas: {ancho_tot:.0f} ancho x {PROF_ABAJO + ABOMBADO:.0f} fondo x {max(TOPES)} alto mm")
