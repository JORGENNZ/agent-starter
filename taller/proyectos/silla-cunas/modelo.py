"""Silla de cuñas — 100 % CNC, sin tornillos ni pegamento.

2 laterales esculpidos + asiento + respaldo + 2 travesaños. Todas las uniones son
espigas pasantes (tusk tenon) que se aprietan con cuñas: se arma y se desarma a mano.

Material: diseñada con T = 25 (MDF de 25). Para uso diario se recomienda TRIPLAY
(contrachapado) de 18 mm o más: cambia T y todo se recalcula (cajas, espigas, cuñas).

Capas del DXF:  CORTE_INT (cajas, agujeros de cuña, agarradera) -> cortar PRIMERO
                CORTE_EXT (perfil exterior de cada pieza, con tabs)
    python3 taller/proyectos/silla-cunas/modelo.py
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

# ---------------- Parámetros (mm) ----------------
T = 25.0              # grosor real del material
HOLG = 0.3            # holgura total de caja vs espiga
R_FRESA = 3.175       # fresa plana 1/4"
W = 430               # ancho interior del asiento (entre laterales)
P = 42                # cuánto sale la espiga por fuera del lateral
HUECO_CUNA = 22       # ancho del agujero de la cuña (sentido hacia afuera)
REBAJE = 20           # el asiento y respaldo quedan 20 mm hundidos en el perfil lateral
# perfil lateral (x adelante->atrás, z arriba)
S0, S1 = np.array([20., 440.]), np.array([440., 425.])     # línea del asiento
B0, B1 = np.array([440., 425.]), np.array([580., 815.])    # línea del respaldo
LADO = [(0, 0), (95, 0), (108, 250), (165, 318), (385, 318), (425, 250), (440, 0), (530, 0),
        (662, 795), (640, 822), (585, 822), (440, 425), (20, 440), (0, 418)]
SEAT = dict(s0=25, largo=395, cajas=[(55, 145), (295, 385)])
BACK = dict(s0=150, largo=230, cajas=[(168, 248), (290, 370)])
TRAV = [dict(x=34, z=85), dict(x=474, z=85)]   # cajas de travesaños (esquina inferior-delantera)
ALTO_ESP_TRAV = 100
HOMBRO = 20
CUNA = dict(largo=110, a=16, b=30)             # cuña: ancho de 16 a 30 mm
SEP = 22                                       # separación entre piezas en la hoja
HOJA = (1220, 2440)
MARGEN = 15                                    # orilla de la hoja sin usar
# -------------------------------------------------
r = R_FRESA

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
d_s = unit(S1 - S0); n_s = np.array([-d_s[1], d_s[0]])        # n_s: hacia arriba
d_b = unit(B1 - B0); n_b = np.array([d_b[1], -d_b[0]])        # n_b: hacia atrás (dentro del lateral)

def dogbones_rect(cs):
    """Dog-bones en las 4 esquinas internas de un rectángulo (lista de 4 esquinas en orden)."""
    out = []
    for i in range(4):
        c, a, b = np.array(cs[i]), np.array(cs[i - 1]), np.array(cs[(i + 1) % 4])
        bis = unit(unit(a - c) + unit(b - c))
        out.append(Point(*(c + bis * r)).buffer(r + 0.05, 32))
    return out

def caja(p0, du, dv, lu, lv):
    cs = [p0, p0 + du * lu, p0 + du * lu + dv * lv, p0 + dv * lv]
    return unary_union([Polygon(cs)] + dogbones_rect(cs))

# ---------- Lateral ----------
lado = Polygon(LADO)
lado = lado.buffer(-14, join_style=1).buffer(14, join_style=1)      # redondea esquinas exteriores
lado = lado.buffer(30, join_style=1).buffer(-30, join_style=1)      # suaviza curvas interiores
cajas_lado = []
for (a, b) in SEAT["cajas"]:
    cajas_lado.append(caja(S0 + d_s * (a - HOLG) - n_s * (REBAJE - HOLG / 2), d_s, -n_s, b - a + 2 * HOLG, T + HOLG))
for (a, b) in BACK["cajas"]:
    cajas_lado.append(caja(B0 + d_b * (a - HOLG) + n_b * (REBAJE - HOLG / 2), d_b, n_b, b - a + 2 * HOLG, T + HOLG))
for t in TRAV:
    cajas_lado.append(caja(np.array([t["x"], t["z"]], float), np.array([1., 0]), np.array([0., 1]),
                           T + HOLG, ALTO_ESP_TRAV + 2 * HOLG))
lado_ext = lado
lado = lado.difference(unary_union(cajas_lado))

# ---------- Panel genérico con espigas (asiento, respaldo, travesaño) ----------
def panel(largo, espigas, redondear=False, extra=None):
    """u: a lo largo (0..largo), v: a lo ancho (0..W). Espigas en u=[a,b], salen T+P por cada lado."""
    p = box(0, 0, largo, W)
    if redondear:
        p = p.buffer(-10, join_style=1).buffer(10, join_style=1)
    huecos, cortes = [], []
    for (a, b) in espigas:
        p = p.union(box(a, -(T + P), b, 0)).union(box(a, W, b, W + T + P))
        for (vc, sv) in ((0, -1), (W, 1)):         # dog-bones en la raíz de la espiga
            for (uc, su) in ((a, -1), (b, 1)):
                cortes.append(Point(uc + su * r / math.sqrt(2), vc + sv * r / math.sqrt(2)).buffer(r + 0.05, 32))
        uc = (a + b) / 2; hu = (T + 0.5) / 2
        for (v0, v1) in ((-T - HUECO_CUNA + 2, -T + 2), (W + T - 2, W + T + HUECO_CUNA - 2)):
            cs = [(uc - hu, v0), (uc + hu, v0), (uc + hu, v1), (uc - hu, v1)]
            huecos.append(unary_union([Polygon(cs)] + dogbones_rect([np.array(c) for c in cs])))
    p = p.buffer(-6, join_style=1).buffer(6, join_style=1)   # suaviza esquinas exteriores de espigas
    p = p.difference(unary_union(cortes))
    if extra is not None:
        huecos.append(extra)
    return p.difference(unary_union(huecos)), huecos

asiento, h_as = panel(SEAT["largo"], [(a - SEAT["s0"], b - SEAT["s0"]) for a, b in SEAT["cajas"]], redondear=True)
agarre = LineString([(BACK["largo"] * 0.62, W / 2 - 60), (BACK["largo"] * 0.62, W / 2 + 60)]).buffer(16, 32)
respaldo, h_re = panel(BACK["largo"], [(a - BACK["s0"], b - BACK["s0"]) for a, b in BACK["cajas"]], redondear=True, extra=agarre)
L_TRAV = ALTO_ESP_TRAV + 2 * HOMBRO
travesano, h_tr = panel(L_TRAV, [(HOMBRO, HOMBRO + ALTO_ESP_TRAV)])
cuna = Polygon([(0, 0), (CUNA["largo"], 0), (CUNA["largo"], CUNA["b"]), (0, CUNA["a"])])
cuna = cuna.buffer(-2, join_style=1).buffer(2, join_style=1)

# ---------- 3D armado ----------
def ext(poly, h=T):
    poly = orient(poly, 1.0)
    return mf.Manifold.extrude(mf.CrossSection([list(poly.exterior.coords)[:-1]] +
                                                [list(i.coords)[:-1] for i in poly.interiors]), h)

def colocar(m, O, eu, ev, ew, h=T):
    eu, ev, ew, O = map(lambda a: np.asarray(a, float), (eu, ev, ew, O))
    if np.linalg.det(np.column_stack([eu, ev, ew])) < 0:
        O, ew = O + ew * h, -ew
    M = np.column_stack([eu, ev, ew, O])
    return m.transform(M.tolist())

X, Y, Z = np.eye(3)
def p3(v2, y=0.0): return np.array([v2[0], y, v2[1]])
def v3(v2): return np.array([v2[0], 0.0, v2[1]])

piezas3d = {}
piezas3d["lateral 1"] = colocar(ext(lado), [0, -T, 0], X, Z, Y)
piezas3d["lateral 2"] = colocar(ext(lado), [0, W, 0], X, Z, Y)
fr_as = (p3(S0 + d_s * SEAT["s0"] - n_s * REBAJE), v3(d_s), Y, -v3(n_s))
fr_re = (p3(B0 + d_b * BACK["s0"] + n_b * REBAJE), v3(d_b), Y, v3(n_b))
piezas3d["asiento"] = colocar(ext(asiento), *fr_as)
piezas3d["respaldo"] = colocar(ext(respaldo), *fr_re)
fr_tr = []
for i, t in enumerate(TRAV):
    fr = (np.array([t["x"] + HOLG / 2, 0, t["z"] + HOLG - HOMBRO]), Z, Y, X)
    fr_tr.append(fr)
    piezas3d[f"travesaño {i+1}"] = colocar(ext(travesano), *fr)

def cunas_de(fr, espigas):
    O, eu, ev, ew = fr
    out = []
    t_mid = (HUECO_CUNA - 2 - CUNA["a"]) / (CUNA["b"] - CUNA["a"]) * CUNA["largo"]
    for (a, b) in espigas:
        uc = (a + b) / 2
        for (v_in, sgn) in ((-T, -1), (W + T, 1)):
            base = O + eu * (uc - T / 2) + ev * v_in + ew * (T / 2 - t_mid)
            out.append(colocar(ext(cuna), base, ew, ev * sgn, eu))
    return out

cunas3d = (cunas_de(fr_as, [(a - SEAT["s0"], b - SEAT["s0"]) for a, b in SEAT["cajas"]]) +
           cunas_de(fr_re, [(a - BACK["s0"], b - BACK["s0"]) for a, b in BACK["cajas"]]) +
           sum((cunas_de(fr, [(HOMBRO, HOMBRO + ALTO_ESP_TRAV)]) for fr in fr_tr), []))

# revisión de interferencias entre piezas (sin cuñas: esas van a presión a propósito)
nombres = list(piezas3d)
peor = 0
for i in range(len(nombres)):
    for j in range(i + 1, len(nombres)):
        v = (piezas3d[nombres[i]] ^ piezas3d[nombres[j]]).volume()
        peor = max(peor, v)
        if v > 0.01:
            print(f"  ¡Interferencia {nombres[i]} / {nombres[j]}: {v:.1f} mm³!")
print(f"Interferencia máxima entre piezas: {peor:.2f} mm³")
cuna_libre = max((c ^ piezas3d["lateral 1"]).volume() + (c ^ piezas3d["lateral 2"]).volume() for c in cunas3d)
print(f"Cuñas vs laterales: {cuna_libre:.2f} mm³ (la cuña debe recargarse, no meterse)")

# ---------- DXF acomodado en hoja ----------
lista = [("LATERAL", lado, cajas_lado, lado_ext)] * 2 + [("ASIENTO", asiento, h_as, None),
         ("RESPALDO", respaldo, h_re, None)] + [("TRAVESAÑO", travesano, h_tr, None)] * 2 + \
        [("CUÑA", cuna, [], None)] * (len(cunas3d) + 2)

def acomodar(lista):
    """Empaque simple por estantes, girando piezas 90° si ayuda."""
    puestos, x, y, alto_estante = [], MARGEN, MARGEN, 0.0
    for nombre, g, hs, gext in lista:
        gg = g
        mnx, mny, mxx, mxy = gg.bounds
        if (mxx - mnx) > (mxy - mny) and nombre not in ("CUÑA",):
            gg = affinity.rotate(gg, 90, origin=(0, 0)); hs = [affinity.rotate(h, 90, origin=(0, 0)) for h in hs]
            if gext is not None: gext = affinity.rotate(gext, 90, origin=(0, 0))
            mnx, mny, mxx, mxy = gg.bounds
        w, h = mxx - mnx, mxy - mny
        if x + w > HOJA[0] - MARGEN:
            x, y, alto_estante = MARGEN, y + alto_estante + SEP, 0.0
        dx, dy = x - mnx, y - mny
        t = lambda q: affinity.translate(q, dx, dy)
        puestos.append((nombre, t(gg), [t(h) for h in hs], t(gext) if gext is not None else None))
        x += w + SEP; alto_estante = max(alto_estante, h)
    return puestos, y + alto_estante

puestos, alto_usado = acomodar(lista)
doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
for n, c in (("CORTE_EXT", 1), ("CORTE_INT", 5), ("NOTAS", 8)):
    doc.layers.add(n, color=c)
msp = doc.modelspace()
for nombre, g, hs, gext in puestos:
    msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
    for i in g.interiors:
        msp.add_lwpolyline(list(i.coords), close=True, dxfattribs={"layer": "CORTE_INT"})
    if nombre != "CUÑA":
        c = g.representative_point()
        msp.add_text(nombre, height=12, dxfattribs={"layer": "NOTAS"}).set_placement((c.x - 40, c.y))
aqui = os.path.dirname(os.path.abspath(__file__))
doc.saveas(os.path.join(aqui, "silla.dxf"))

# las piezas no deben encimarse en la hoja
gs = [g for _, g, _, _ in puestos]
choque = max((gs[i].buffer(SEP / 2 - 1).intersection(gs[j].buffer(SEP / 2 - 1)).area
              for i in range(len(gs)) for j in range(i + 1, len(gs))), default=0)
print(f"Hoja: {HOJA[0]} × {alto_usado:.0f} mm usados de {HOJA[0]} × {HOJA[1]} | encimadas: {choque:.1f} mm²")

fig, ax = plt.subplots(figsize=(5, 9), dpi=170)
ax.add_patch(plt.Rectangle((0, 0), *HOJA, fill=False, ls="--", ec="#999"))
for nombre, g, _, _ in puestos:
    x, y = g.exterior.xy; ax.fill(x, y, color="#c8a97e", ec="#6b4f2a", lw=0.8)
    for i in g.interiors:
        x, y = i.xy; ax.fill(x, y, color="white", ec="#2b6cb0", lw=0.8)
    if nombre != "CUÑA":
        c = g.representative_point(); ax.text(c.x, c.y, nombre, ha="center", fontsize=6)
ax.set_title(f"Silla de cuñas — hoja {HOJA[0]}×{HOJA[1]}, material {T:g} mm", fontsize=9)
ax.set_aspect("equal"); ax.set_xlim(-30, HOJA[0] + 30); ax.set_ylim(-30, HOJA[1] + 30)
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hoja.png"), facecolor="white"); plt.close(fig)

# ---------- render ----------
mallas = [a_trimesh(m) for m in piezas3d.values()] + [a_trimesh(c) for c in cunas3d]
col = ["#c8a97e", "#c8a97e", "#d9bf94", "#d9bf94", "#b8935f", "#b8935f"] + ["#3d2c1e"] * len(cunas3d)
render(mallas, os.path.join(aqui, "vista.png"), f"Silla de cuñas — CNC, material {T:g} mm",
       colores=col, elev=20, azim=140, zoom=1.18)
render(mallas, os.path.join(aqui, "vista-atras.png"), "Silla de cuñas — vista trasera",
       colores=col, elev=16, azim=-48, zoom=1.18)
zs = piezas3d["asiento"].bounding_box()
print(f"Alto de asiento ≈ {zs[5]:.0f} mm | ancho total ≈ {W + 2 * (T + P):.0f} mm | alto total ≈ 822 mm")
