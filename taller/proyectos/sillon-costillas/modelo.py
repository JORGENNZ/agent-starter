"""Sillón lounge de costillas paramétricas — 100 % CNC, MDF de 18 mm, UNA sola hoja.

17 costillas en forma de banda curva (asiento + respaldo en una pieza), cada una
distinta: el asiento hace cuna (más bajo al centro), el frente hace ola, el respaldo
envuelve (las de afuera se adelantan arriba) y es más alto al centro.

Estructura (sin tornillos):
  - 2 caballetes (patas): las costillas se asientan en ellos por ranuras desde abajo.
    El trasero va inclinado hacia atrás para que el sillón no se vaya de espaldas.
  - 1 cresta superior: barra curva que amarra las puntas del respaldo.
Las costillas trabajan de canto (en su plano), donde el MDF es fuerte.

Diseñado para el corte: las bandas en "J" se acomodan una dentro de otra, por eso
todo el sillón sale de una hoja de 1220 x 2440.

Salidas: hoja-1.dxf (CORTE_EXT / CORTE_INT / GRABADO), hojas.png, vista*.png
    python3 taller/proyectos/sillon-costillas/modelo.py
"""
import math, os, sys
import numpy as np
import ezdxf
import manifold3d as mf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString, box, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, polylabel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import render, a_trimesh
from lib.nesting import acomodar_grupos, acomodar_mirando, aprovechamiento, pila

# ---------------- Parámetros (mm) ----------------
T = 18.0            # grosor real del MDF
HOLG = 0.3          # holgura de ranuras
R_FRESA = 3.175     # fresa plana 1/4"
N = 15              # costillas
HUECO = 23.1        # espacio entre costillas (ancho total 594)
BANDA = 60          # peralte de cada costilla
# perfil de la superficie (costilla central): x adelante->atrás, z arriba
CURVA = [(30, 345), (44, 392), (115, 410), (245, 384), (365, 356), (445, 372), (495, 452),
         (540, 592), (582, 742), (614, 890)]
CUNA_ASIENTO = 24   # cuánto baja el asiento al centro
OLA_FRENTE = 18     # cuánto sale el frente al centro
ENVOLVER = 46       # cuánto se adelantan arriba las costillas de los extremos
ALTO_EXTRA = 60     # cuánto más alto es el respaldo al centro
# caballetes: punto en el piso y punto hacia donde suben (línea de su plano central)
CAB_DEL = ((60, 0), (165, 400))
CAB_TRAS = ((712, 0), (478, 400))
PIE = 78            # ancho de cada pata de los caballetes
VIGA = 80           # peralte de la viga superior de los caballetes
Z_CRESTA = 770      # altura de la cresta superior
HOJA = (1220, 2440)
GIRO = 5            # paso de giro al acomodar (MDF no tiene veta; en triplay usa 90)
# -------------------------------------------------
S = T + HOLG
PASO = T + HUECO
ANCHO = N * T + (N - 1) * HUECO
ys = [i * PASO + T / 2 for i in range(N)]
r = R_FRESA
unit = lambda v: np.asarray(v, float) / np.linalg.norm(v)

def catmull(pts, n=20):
    p = np.array(pts, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return np.array(out)

def dogbone(c, d):
    d = unit(d)
    return Point(c[0] + d[0] * r, c[1] + d[1] * r).buffer(r + 0.05, 32)

def banda(i):
    t = -1 + 2 * i / (N - 1)
    c = [list(p) for p in CURVA]
    for k in (0, 1):
        c[k][0] -= OLA_FRENTE * (1 - t * t)
    for k in (3, 4):
        c[k][1] -= CUNA_ASIENTO * (1 - t * t)
    c[5][1] -= CUNA_ASIENTO * 0.5 * (1 - t * t)
    c[-2][0] -= ENVOLVER * 0.5 * t * t; c[-2][1] += ALTO_EXTRA * 0.5 * (1 - t * t)
    c[-1][0] -= ENVOLVER * t * t;       c[-1][1] += ALTO_EXTRA * (1 - t * t)
    sup = LineString(catmull(c))
    centro = sup.offset_curve(-BANDA / 2, join_style=1)          # lado de abajo/atrás
    return centro.buffer(BANDA / 2 - 0.01, cap_style=1, join_style=1), sup

def cruce(geom, a, b):
    """Primer tramo donde la recta a->b atraviesa geom: (s_entrada, s_salida) en mm desde a."""
    a, b = np.array(a, float), np.array(b, float)
    d = unit(b - a)
    seg = geom.intersection(LineString([a, a + d * 3000]))
    tramos = [g for g in getattr(seg, "geoms", [seg]) if g.length > 1]
    tramos.sort(key=lambda g: min(np.dot(np.array(p) - a, d) for p in g.coords))
    g = tramos[0]
    ss = [np.dot(np.array(p) - a, d) for p in g.coords]
    return min(ss), max(ss)

bandas = [banda(i) for i in range(N)]

# ---------- caballetes ----------
cabs = {}
for nombre, (F, A) in (("P1", CAB_DEL), ("P2", CAB_TRAS)):
    F = np.array(F, float); d = unit(np.array(A) - F); n = np.array([d[1], -d[0]])
    s_mid = []
    for b, _ in bandas:
        s_in, s_out = cruce(b, F, F + d)
        s_mid.append((s_in + s_out) / 2)
    cabs[nombre] = dict(F=F, d=d, n=n, s_mid=s_mid)

# ---------- cresta ----------
x_mid_cr, x_out_cr = [], []
for b, _ in bandas:
    x0, x1 = cruce(b, (-100, Z_CRESTA), (0, Z_CRESTA))
    x_mid_cr.append(-100 + (x0 + x1) / 2); x_out_cr.append(-100 + x1)

# ---------- piezas 2D ----------
piezas2d = {}
for i, (b, _) in enumerate(bandas):
    cortes = []
    for c in cabs.values():
        F, d, n, sm = c["F"], c["d"], c["n"], c["s_mid"][i]
        P = lambda s, w: F + d * s + n * w
        cortes.append(Polygon([P(sm - 140, -S / 2), P(sm - 140, S / 2), P(sm, S / 2), P(sm, -S / 2)]))
        cortes += [dogbone(P(sm, S / 2), -d - n), dogbone(P(sm, -S / 2), -d + n)]
    xm = x_mid_cr[i]; z0, z1 = Z_CRESTA - S / 2, Z_CRESTA + S / 2
    cortes += [box(xm, z0, x_out_cr[i] + 60, z1), dogbone((xm, z1), (1, -1)), dogbone((xm, z0), (1, 1))]
    piezas2d[f"C{i+1:02d}"] = b.difference(unary_union(cortes))

def caballete(c):
    F, d, n, sm = c["F"], c["d"], c["n"], c["s_mid"]
    v0 = T / 2 * abs(d[0]) / d[1] + 0.5          # que la esquina no se meta al piso
    E = 22                                       # cuánto sale después de la última costilla
    top = [(-E, sm[0] - 30)]
    for y, s in zip(ys, sm):
        top += [(y - S / 2 - 3, s), (y + S / 2 + 3, s)]
    top += [(ANCHO + E, sm[-1] - 30)]
    p = Polygon([(-E, v0)] + top + [(ANCHO + E, v0)]).buffer(0)
    alto_arco = min(sm) - v0 - VIGA
    arco = [(u, v0 + alto_arco * max(0.0, math.sin(math.pi * (u - PIE) / (ANCHO - 2 * PIE))) ** 0.35)
            for u in np.linspace(PIE, ANCHO - PIE, 80)]
    p = p.difference(Polygon([(PIE, v0 - 50)] + arco + [(ANCHO - PIE, v0 - 50)]).buffer(40, join_style=1)
                     .buffer(-40, join_style=1))
    return p.buffer(-10, join_style=1).buffer(10, join_style=1), v0

for k in cabs:
    piezas2d[k], cabs[k]["v0"] = caballete(cabs[k])

def cresta():
    frente = []
    for y, xm in zip(ys, x_mid_cr):
        frente += [(xm, y - S / 2 - 3), (xm, y + S / 2 + 3)]
    cf = np.polyfit(ys, np.array(x_out_cr) + 46, 4)
    atras = [(float(np.polyval(cf, y)), y) for y in np.linspace(ys[0], ys[-1], 40)]
    a0, a1 = atras[0], atras[-1]
    p = Polygon(frente + [(a1[0], ANCHO + 26), (a1[0] - 20, ANCHO + 26)][::-1][::-1] + atras[::-1] +
                [(a0[0], -26)]).buffer(0)
    p = Polygon(frente + [(frente[-1][0] + 8, ANCHO + 24), (a1[0], ANCHO + 24)] + atras[::-1] +
                [(a0[0], -24), (frente[0][0] + 8, -24)]).buffer(0)
    return p.buffer(-12, join_style=1).buffer(12, join_style=1)

piezas2d["CR"] = cresta()

# ---------- 3D ----------
def ext(poly, h=T):
    poly = orient(poly, 1.0)
    return mf.Manifold.extrude(mf.CrossSection([list(poly.exterior.coords)[:-1]] +
                                                [list(q.coords)[:-1] for q in poly.interiors]), h)

def colocar(m, O, eu, ev, ew, h=T):
    eu, ev, ew, O = (np.asarray(a, float) for a in (eu, ev, ew, O))
    if np.linalg.det(np.column_stack([eu, ev, ew])) < 0:
        O, ew = O + ew * h, -ew
    return m.transform(np.column_stack([eu, ev, ew, O]).tolist())

X, Y, Z = np.eye(3)
p3d = {}
for i in range(N):
    p3d[f"C{i+1:02d}"] = colocar(ext(piezas2d[f"C{i+1:02d}"]), [0, ys[i] - T / 2, 0], X, Z, Y)
for k, c in cabs.items():
    d3, n3 = np.array([c["d"][0], 0, c["d"][1]]), np.array([c["n"][0], 0, c["n"][1]])
    O = np.array([c["F"][0], 0, c["F"][1]]) - n3 * T / 2
    p3d[k] = colocar(ext(piezas2d[k]), O, Y, d3, n3)
p3d["CR"] = colocar(ext(piezas2d["CR"]), [0, 0, Z_CRESTA - T / 2], X, Y, Z)

nom = list(p3d)
peor = max((p3d[a] ^ p3d[b]).volume() for ia, a in enumerate(nom) for b in nom[ia + 1:])
print(f"Interferencia máxima entre piezas: {peor:.3f} mm³")
for k in ("P1", "P2", "CR"):
    n_ok = sum((p3d[k] ^ colocar(ext(bandas[i][0]), [0, ys[i] - T / 2, 0], X, Z, Y)).volume() > 50
               for i in range(N))
    print(f"{k} entra en {n_ok} de {N} costillas")
zmin = min(p3d[k].bounding_box()[2] for k in nom)
print(f"Punto más bajo: {zmin:.2f} mm (no debe ser < 0)")

aqui = os.path.dirname(os.path.abspath(__file__))
mad, osc = "#dcc19a", "#8f6a42"
col = [mad] * N + [osc, osc, osc]
ms = [a_trimesh(p3d[k]) for k in nom]
render(ms, os.path.join(aqui, "vista.png"), "Sillón de costillas — CNC, MDF 18 mm, 1 hoja", colores=col,
       elev=20, azim=148, zoom=1.08)
render(ms, os.path.join(aqui, "vista-atras.png"), "Sillón de costillas — vista trasera", colores=col,
       elev=26, azim=-38, zoom=1.08)
render(ms, os.path.join(aqui, "vista-lado.png"), "Sillón de costillas — perfil", colores=col,
       elev=3, azim=-90.01, zoom=1.0)

# ---------- acomodo ----------
# las costillas se apilan una dentro de otra (ordenadas por parecido: centro -> extremos);
# se prueba partir la pila en 1, 2 o 3 bloques y se queda la opción que use menos hojas.
orden_c = [N // 2] + [j for k in range(1, N // 2 + 1) for j in (N // 2 - k, N // 2 + k)]
costillas = [(f"C{i+1:02d}", piezas2d[f"C{i+1:02d}"]) for i in orden_c]
sueltas = [(k, g) for k, g in piezas2d.items() if not (k.startswith("C") and k != "CR")]
grupo = pila(costillas, separacion=11)
hojas = acomodar_mirando(grupo, sueltas, hoja=HOJA, separacion=11, giro_busqueda=6,
                         giro_sueltas=5, res_busqueda=5.0)
ap = aprovechamiento(hojas, HOJA)
print(f"Piezas: {len(piezas2d)} | área: {sum(g.area for g in piezas2d.values())/1e6:.2f} m² | hojas: {len(hojas)} | "
      f"aprovechamiento: {', '.join(f'{a*100:.0f}%' for a in ap)}")

SEG7 = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
        "7": "abc", "8": "abcdefg", "9": "abcdfg", "C": "afed", "P": "abfge", "R": "efab gc"}
def glifo(ch, x, y, h):
    w = h * 0.55
    seg = {"a": [(0, h), (w, h)], "b": [(w, h), (w, h / 2)], "c": [(w, h / 2), (w, 0)], "d": [(0, 0), (w, 0)],
           "e": [(0, 0), (0, h / 2)], "f": [(0, h / 2), (0, h)], "g": [(0, h / 2), (w, h / 2)]}
    if ch == "R":
        return [[(x, y), (x, y + h), (x + w, y + h), (x + w, y + h / 2), (x, y + h / 2), (x + w, y)]]
    return [[(x + a, y + b) for a, b in seg[s]] for s in SEG7[ch]]

def etiqueta(texto, g, h=14):
    zona = g.buffer(-h * 0.9)
    c = polylabel(zona, tolerance=1) if not zona.is_empty and zona.area > 0 else g.representative_point()
    w = len(texto) * h * 0.8
    lineas = []
    for j, ch in enumerate(texto):
        lineas += glifo(ch, c.x - w / 2 + j * h * 0.8, c.y - h / 2, h)
    ok = all(g.contains(LineString(l)) for l in lineas)
    return lineas if ok else []

fig, axs = plt.subplots(1, len(hojas), figsize=(4.6 * len(hojas), 8.6), dpi=170, squeeze=False)
for k, ps in enumerate(hojas):
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for nm, cc in (("CORTE_EXT", 1), ("CORTE_INT", 5), ("GRABADO", 3)):
        doc.layers.add(nm, color=cc)
    msp = doc.modelspace()
    ax = axs[0][k]
    ax.add_patch(plt.Rectangle((0, 0), *HOJA, fc="#f7f4ee", ec="#999", ls="--"))
    for p in ps:
        g = p["geom"]
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
        for q in g.interiors:
            msp.add_lwpolyline(list(q.coords), close=True, dxfattribs={"layer": "CORTE_INT"})
        xx, yy = g.exterior.xy
        ax.fill(xx, yy, fc=mad if p["nombre"][0] == "C" and p["nombre"] != "CR" else osc, ec="#5a4026", lw=0.5)
        for ln in etiqueta(p["nombre"], g):
            msp.add_lwpolyline(ln, dxfattribs={"layer": "GRABADO"})
            ax.plot(*zip(*ln), color="#1f5f9f", lw=0.6)
    doc.saveas(os.path.join(aqui, f"hoja-{k+1}.dxf"))
    ax.set_title(f"Hoja {k+1} de {len(hojas)}: {len(ps)} piezas · {ap[k]*100:.0f}% de la hoja en piezas", fontsize=9)
    ax.set_aspect("equal"); ax.set_xlim(-20, HOJA[0] + 20); ax.set_ylim(-20, HOJA[1] + 20); ax.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hojas.png"), facecolor="white"); plt.close(fig)

bb = [p3d[k].bounding_box() for k in nom]
alto = max(b[5] for b in bb); fondo = max(b[3] for b in bb) - min(b[0] for b in bb)
z_asiento = min(cruce(bandas[N // 2][1].buffer(0.5), (300, 0), (300, 1))) if False else None
print(f"Ancho {ANCHO:.0f} | fondo {fondo:.0f} | alto {alto:.0f} mm")
