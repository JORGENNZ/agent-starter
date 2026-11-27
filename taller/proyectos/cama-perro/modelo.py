"""Cama sofá para perro — 100 % CNC, MDF de 18 mm, una sola hoja, sin tornillos.

Piezas: 2 laterales (brazos de sofá con patas), respaldo con hueso calado, frente
bajo con curva de entrada, piso con huellas caladas (ventilan el cojín) y cuñas.
Todas las uniones son espigas pasantes que se aprietan con cuñas: se arma y desarma a mano.

Tallas por tamaño de cojín (cambia TALLA):
  S: cojín 65 x 50 cm (perros hasta ~10 kg)
  M: cojín 80 x 60 cm (perros de ~10 a 25 kg)
  L: cojín 100 x 70 cm (perros de ~25 a 40 kg)

Capas: CORTE_INT (cajas, huellas, hueso, agujeros de cuña) -> primero
       CORTE_EXT (perfil de cada pieza)
    python3 taller/proyectos/cama-perro/modelo.py [S|M|L]
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
from lib.nesting import acomodar, aprovechamiento

# ---------------- Parámetros (mm) ----------------
TALLAS = {  # cojín (ancho x fondo), alto del respaldo, alto del brazo al frente, escala de huellas
    "S": dict(cojin=(650, 500), alto=300, brazo=175, huella=32),
    "M": dict(cojin=(800, 600), alto=380, brazo=220, huella=40),
    "L": dict(cojin=(1000, 700), alto=450, brazo=260, huella=46),
}
TALLA = sys.argv[1].upper() if len(sys.argv) > 1 else "M"
T = 18.0              # grosor real del MDF
HOLG = 0.3
R_FRESA = 3.175
HOLGURA_COJIN = 20    # espacio extra alrededor del cojín
Z_PISO = 80           # altura del piso de la cama sobre el suelo (aire abajo)
P = 34                # cuánto sale la espiga por fuera del lateral
HUECO_CUNA = 16
CUNA = dict(largo=80, a=12, b=22)
VUELO = 40            # cuánto sobresale el lateral al frente y atrás de los paneles
HOJA = (1220, 2440)
# comedero elevado a juego (sale del sobrante de la hoja)
COMEDERO = {"S": dict(alto=150, plato=150), "M": dict(alto=240, plato=180), "L": dict(alto=330, plato=220)}
# -------------------------------------------------
cfg = TALLAS[TALLA]
W = cfg["cojin"][0] + HOLGURA_COJIN          # ancho interior (entre laterales)
D = cfg["cojin"][1] + HOLGURA_COJIN          # fondo interior (entre frente y respaldo)
ALTO, BRAZO, HU = cfg["alto"], cfg["brazo"], cfg["huella"]
S = T + HOLG
r = R_FRESA
L_LAT = D + 2 * T + 2 * VUELO
y_fr0, y_fr1 = VUELO, VUELO + T                  # frente
y_re0, y_re1 = VUELO + T + D, VUELO + 2 * T + D  # respaldo
z_p0, z_p1 = Z_PISO, Z_PISO + T                  # piso

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

def catmull(pts, n=16):
    p = np.array(pts, float); p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2]); return out

def dogbones_rect(cs):
    out = []
    for i in range(4):
        c, a, b = np.array(cs[i]), np.array(cs[i - 1]), np.array(cs[(i + 1) % 4])
        bis = unit(unit(a - c) + unit(b - c))
        out.append(Point(*(c + bis * r)).buffer(r + 0.05, 32))
    return out

def caja(x0, y0, x1, y1):
    cs = [np.array(p, float) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return unary_union([box(x0, y0, x1, y1)] + dogbones_rect(cs))

# ---------- espigas (en coordenadas del panel: u a lo largo, v a lo ancho 0..W) ----------
def espigas(p, rangos, Wp=None):
    Wp = W if Wp is None else Wp
    huecos, cortes = [], []
    for (a, b) in rangos:
        p = p.union(box(a, -(T + P), b, 0)).union(box(a, Wp, b, Wp + T + P))
        for (vc, sv) in ((0, -1), (Wp, 1)):
            for (uc, su) in ((a, -1), (b, 1)):
                cortes.append(Point(uc + su * r / math.sqrt(2), vc + sv * r / math.sqrt(2)).buffer(r + 0.05, 32))
        uc, hu = (a + b) / 2, (T + 0.5) / 2
        for (v0, v1) in ((-T - HUECO_CUNA + 2, -T + 2), (Wp + T - 2, Wp + T + HUECO_CUNA - 2)):
            huecos.append(caja(uc - hu, v0, uc + hu, v1))
    p = p.buffer(-5, join_style=1).buffer(5, join_style=1).difference(unary_union(cortes))
    return p, huecos

# rangos de espigas (u) de cada panel
R_PISO = [(D * f - 50, D * f + 50) for f in (0.17, 0.5, 0.83)]      # u = y desde el frente interior
ALTO_FR = 170 - Z_PISO + 60                                         # frente: de z=Z_PISO-60 a 170
R_FRENTE = [(15, ALTO_FR - 15)]                                    # u = z desde abajo del frente
z_fr_base = Z_PISO - 60
z_re_base = Z_PISO - 60
ALTO_RE = ALTO - 20 - z_re_base
R_RESP = [(25, 25 + (ALTO_RE - 70) * 0.42), (ALTO_RE - 25 - (ALTO_RE - 70) * 0.42, ALTO_RE - 25)]

# ---------- piso con huellas ----------
def huella(cx, cy, s, ang):
    partes = [affinity.scale(Point(0, 0).buffer(1, 48), 0.55 * s, 0.46 * s)]
    for (x, y) in ((-0.75, 0.52), (-0.27, 0.92), (0.27, 0.92), (0.75, 0.52)):
        partes.append(affinity.scale(Point(0, 0).buffer(1, 32), 0.16 * s, 0.21 * s).buffer(0).__class__(
            affinity.translate(affinity.scale(Point(0, 0).buffer(1, 32), 0.16 * s, 0.21 * s), x * s, y * s)))
    g = [affinity.rotate(affinity.translate(q, cx, cy), ang, origin=(cx, cy)) for q in partes]
    return g

def piso():
    p = box(0, 0, D, W)
    p, huecos = espigas(p, R_PISO)
    # camino de huellas en diagonal (u = fondo, v = ancho)
    zona = box(45, 45, D - 45, W - 45)
    a = np.array([D * 0.12, W * 0.12]); b = np.array([D * 0.88, W * 0.88])
    dirv = unit(b - a); perp = np.array([-dirv[1], dirv[0]])
    ang = math.degrees(math.atan2(dirv[1], dirv[0])) - 90
    paso = HU * 2.6
    n = int(np.linalg.norm(b - a) // paso) + 1
    hs = []
    for k in range(n):
        c = a + dirv * (k * paso) + perp * (HU * 0.75 * (1 if k % 2 else -1))
        hu = huella(c[0], c[1], HU, ang)
        if all(zona.contains(q) for q in hu):
            hs += hu
    return p.difference(unary_union(huecos + hs)), huecos + hs

# ---------- frente con curva de entrada ----------
def frente():
    top = [(ALTO_FR - (60 * math.sin(math.pi * v / W) ** 2), v) for v in np.linspace(0, W, 60)]
    p = Polygon([(0, 0)] + [(u, v) for u, v in top] + [(0, W)]).buffer(0)
    return espigas(p, R_FRENTE)

# ---------- respaldo con hueso ----------
def respaldo():
    top = [(ALTO_RE + 18 * math.sin(math.pi * v / W), v) for v in np.linspace(0, W, 60)]
    p = Polygon([(0, 0)] + top + [(0, W)]).buffer(0)
    p, huecos = espigas(p, R_RESP)
    uc, vc, Lh = ALTO_RE - 62, W / 2, 110 * HU / 40
    rr = 16 * HU / 40
    hueso = unary_union([box(uc - rr * 0.75, vc - Lh / 2, uc + rr * 0.75, vc + Lh / 2)] +
                        [Point(uc + du * rr * 0.85, vc + dv * Lh / 2).buffer(rr, 48)
                         for du in (-1, 1) for dv in (-1, 1)])
    return p.difference(unary_union(huecos + [hueso])), huecos + [hueso]

# ---------- laterales ----------
def lateral():
    tope = catmull([(0, BRAZO - 45), (22, BRAZO - 5), (95, BRAZO + 8), (L_LAT * 0.45, BRAZO + 22),
                    (L_LAT * 0.78, ALTO - 50), (L_LAT * 0.93, ALTO), (L_LAT, ALTO - 8)])
    pie = 88
    arco = [(y, 52 * math.sin(math.pi * (y - pie) / (L_LAT - 2 * pie)) ** 0.5) for y in np.linspace(pie, L_LAT - pie, 40)]
    p = Polygon([(0, 0), (pie, 0)] + arco + [(L_LAT - pie, 0), (L_LAT, 0)] + tope[::-1]).buffer(0)
    p = p.buffer(-12, join_style=1).buffer(12, join_style=1)
    cajas = []
    for (a, b) in R_PISO:
        y0 = y_fr1 + a
        cajas.append(caja(y0 - HOLG / 2, z_p0 - HOLG / 2, y0 + (b - a) + HOLG / 2, z_p1 + HOLG / 2))
    for (a, b) in R_FRENTE:
        cajas.append(caja(y_fr0 - HOLG / 2, z_fr_base + a - HOLG / 2, y_fr1 + HOLG / 2, z_fr_base + b + HOLG / 2))
    for (a, b) in R_RESP:
        cajas.append(caja(y_re0 - HOLG / 2, z_re_base + a - HOLG / 2, y_re1 + HOLG / 2, z_re_base + b + HOLG / 2))
    return p.difference(unary_union(cajas)), cajas, p

def revisar_pieza(nombre, g, minimo=6.0):
    assert g.geom_type == "Polygon", f"{nombre} sale en varios pedazos"
    hs = [Polygon(h) for h in g.interiors]
    d_borde = min([Polygon(g.exterior.coords).exterior.distance(h) for h in hs], default=99)
    d_hh = min([hs[i].distance(hs[j]) for i in range(len(hs)) for j in range(i + 1, len(hs))], default=99)
    assert min(d_borde, d_hh) >= minimo, f"{nombre}: puente de {min(d_borde, d_hh):.1f} mm"
    return min(d_borde, d_hh)

cuna = Polygon([(0, 0), (CUNA["largo"], 0), (CUNA["largo"], CUNA["b"]), (0, CUNA["a"])]).buffer(-2, join_style=1).buffer(2, join_style=1)

LAT, cajas_lat, lat_lleno = lateral()
PISO, h_piso = piso()
FRE, h_fre = frente()
RES, h_res = respaldo()
n_cunas = 2 * (len(R_PISO) + len(R_FRENTE) + len(R_RESP))
# ---------- comedero ----------
cc = COMEDERO[TALLA]
DP = cc["plato"]                       # diámetro exterior del plato
HUECO_PLATO = DP - 12                  # el plato se apoya en su borde
Wc = 2 * DP + 3 * 45                   # ancho interior entre patas
Dc = DP + 2 * 45                       # fondo de la cubierta
Hc = cc["alto"]
L_PC = Dc + 2 * 30                     # largo de las patas del comedero
R_CUB = [(Dc * 0.5 - 45, Dc * 0.5 + 45)]
def cubierta():
    p = box(0, 0, Dc, Wc)
    p, hh = espigas(p, R_CUB, Wc)
    platos = [Point(Dc / 2, 45 + DP / 2 + k * (DP + 45)).buffer(HUECO_PLATO / 2, 96) for k in (0, 1)]
    return p.difference(unary_union(hh + platos)), hh + platos
z_cub = Hc - T - 22                     # 22 mm de ceja arriba: los platos no se resbalan
z_trc = 40
ALTO_TR = min(90, z_cub - z_trc - 15)    # el travesaño no debe tocar la cubierta
R_TRAV = [(15, ALTO_TR - 15)]
def trav_comedero():
    p = Polygon([(0, 0)] + [(ALTO_TR - 22 * math.sin(math.pi * v / Wc) ** 2, v) for v in np.linspace(0, Wc, 40)] + [(0, Wc)]).buffer(0)
    return espigas(p, R_TRAV, Wc)
def pata_comedero():
    tope = catmull([(0, Hc - 30), (25, Hc), (L_PC / 2, Hc + 6), (L_PC - 25, Hc), (L_PC, Hc - 30)])
    pie = 55
    arco = [(y, 70 * math.sin(math.pi * (y - pie) / (L_PC - 2 * pie)) ** 0.6) for y in np.linspace(pie, L_PC - pie, 30)]
    p = Polygon([(0, 0), (pie, 0)] + arco + [(L_PC - pie, 0), (L_PC, 0)] + tope[::-1]).buffer(0)
    p = p.buffer(-10, join_style=1).buffer(10, join_style=1)
    cj = []
    for (a, b) in R_CUB:
        cj.append(caja(30 + a - HOLG / 2, z_cub - HOLG / 2, 30 + b + HOLG / 2, z_cub + T + HOLG / 2))
    y_t = L_PC - 30 - T  # travesaño atrás, a ras del borde trasero de la cubierta
    for (a, b) in R_TRAV:
        cj.append(caja(y_t - HOLG / 2, z_trc + a - HOLG / 2, y_t + T + HOLG / 2, z_trc + b + HOLG / 2))
    # huella decorativa: la más grande que quepa con 8 mm de material alrededor
    zona = p.buffer(-8).difference(unary_union(cj).buffer(8))
    hu = []
    for f in (0.9, 0.8, 0.7, 0.6, 0.5):
        s_ = HU * f
        zc = (70 + z_cub) / 2 - s_ * 0.3
        cand = huella(L_PC / 2, zc, s_, 0)
        if all(zona.contains(q) for q in cand):
            hu = cand; break
    return p.difference(unary_union(cj + hu)), p, y_t
CUB, h_cub = cubierta()
TRC, h_trc = trav_comedero()
PCO, pco_lleno, y_trc = pata_comedero()
n_cunas += 2 * (len(R_CUB) + len(R_TRAV))

piezas2d = {"LAT-1": LAT, "LAT-2": LAT, "PISO": PISO, "FRENTE": FRE, "RESPALDO": RES,
            "COM-PATA-1": PCO, "COM-PATA-2": PCO, "COM-CUBIERTA": CUB, "COM-TRAV": TRC}
for k in range(n_cunas + 2):
    piezas2d[f"CU{k+1}"] = cuna
puente = min(revisar_pieza(k, g) for k, g in piezas2d.items() if not k.startswith("CU"))
print(f"[{TALLA}] Todas las piezas salen enteras; puente mínimo de material: {puente:.1f} mm")

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
p3d = {
    "LAT-1": colocar(ext(LAT), [-T, 0, 0], Y, Z, X),
    "LAT-2": colocar(ext(LAT), [W, 0, 0], Y, Z, X),
    "PISO": colocar(ext(PISO), [0, y_fr1, z_p0], Y, X, Z),
    "FRENTE": colocar(ext(FRE), [0, y_fr0, z_fr_base], Z, X, Y),
    "RESPALDO": colocar(ext(RES), [0, y_re0, z_re_base], Z, X, Y),
}
# cuñas en su lugar (para la vista)
def cunas_panel(O, eu, ev, ew, rangos):
    out = []
    t_mid = (HUECO_CUNA - 2 - CUNA["a"]) / (CUNA["b"] - CUNA["a"]) * CUNA["largo"]
    for (a, b) in rangos:
        uc = (a + b) / 2
        for (v_in, sg) in ((-T, -1), (W + T, 1)):
            base = np.asarray(O) + eu * (uc - T / 2) + ev * v_in + ew * (T / 2 - t_mid)
            out.append(colocar(ext(cuna), base, ew, ev * sg, eu))
    return out
cunas3d = (cunas_panel([0, y_fr1, z_p0], Y, X, Z, R_PISO) +
           cunas_panel([0, y_fr0, z_fr_base], Z, X, Y, R_FRENTE) +
           cunas_panel([0, y_re0, z_re_base], Z, X, Y, R_RESP))

OX = W + 2 * (T + P) + 180        # comedero a la derecha de la cama
OY = -L_PC - 120
com3d = {
    "C-PATA-1": colocar(ext(PCO), [OX - T, OY, 0], Y, Z, X),
    "C-PATA-2": colocar(ext(PCO), [OX + Wc, OY, 0], Y, Z, X),
    "C-CUB": colocar(ext(CUB), [OX, OY + 30, z_cub], Y, X, Z),
    "C-TRAV": colocar(ext(TRC), [OX, OY + y_trc, z_trc], Z, X, Y),
}
cn = list(com3d)
peor_c = max((com3d[a] ^ com3d[b]).volume() for i, a in enumerate(cn) for b in cn[i + 1:])
print(f"[{TALLA}] Comedero: interferencia {peor_c:.3f} mm³ | platos de {DP} mm, hueco {HUECO_PLATO} mm | alto {Hc} mm")
llc = colocar(ext(pco_lleno), [OX - T, OY, 0], Y, Z, X)
for k in ("C-CUB", "C-TRAV"):
    print(f"  {k}: espiga dentro de la pata = {(com3d[k] ^ llc).volume() / 1000:.1f} cm³")
_Wbak = W
W = Wc
cunas3d += (cunas_panel([OX, OY + 30, z_cub], Y, X, Z, R_CUB) +
            cunas_panel([OX, OY + y_trc, z_trc], Z, X, Y, R_TRAV))
W = _Wbak
nom = list(p3d)
peor = max((p3d[a] ^ p3d[b]).volume() for i, a in enumerate(nom) for b in nom[i + 1:])
print(f"[{TALLA}] Interferencia máxima entre piezas: {peor:.3f} mm³")
lleno = colocar(ext(lat_lleno), [-T, 0, 0], Y, Z, X)
for k in ("PISO", "FRENTE", "RESPALDO"):
    print(f"  {k}: espiga dentro del lateral = {(p3d[k] ^ lleno).volume() / 1000:.1f} cm³")
print(f"  cuñas vs laterales/patas: {max((c ^ p3d['LAT-1']).volume() + (c ^ p3d['LAT-2']).volume() + (c ^ com3d['C-PATA-1']).volume() + (c ^ com3d['C-PATA-2']).volume() for c in cunas3d):.2f} mm³")
# huellas: puente mínimo de material entre agujeros
hs = [h for h in h_piso if h.area < 4000]
puente = min(hs[i].distance(hs[j]) for i in range(len(hs)) for j in range(i + 1, len(hs)) if hs[i].distance(hs[j]) < 60)
print(f"  huellas: {len(hs) // 5} | puente mínimo entre agujeros: {puente:.1f} mm")

# cojín para la vista
def cojin():
    cw, cd = cfg["cojin"]; h = 110; rr = 45
    pts = []
    for x in (HOLGURA_COJIN / 2 + rr, HOLGURA_COJIN / 2 + cw - rr):
        for y in (y_fr1 + HOLGURA_COJIN / 2 + rr, y_fr1 + HOLGURA_COJIN / 2 + cd - rr):
            for z in (z_p1 + rr * 0.8, z_p1 + h - rr * 0.8):
                pts.append(mf.Manifold.sphere(rr * 0.8 if z > z_p1 + h / 2 else rr * 0.8, 24).scale((1, 1, 1)).translate((x, y, z)))
    return mf.Manifold.batch_hull(pts)

aqui = os.path.dirname(os.path.abspath(__file__))
mad, osc = "#dcc19a", "#8f6a42"
def plato(cx, cy):
    rr = DP / 2
    m = mf.Manifold.cylinder(60, rr * 0.82, rr, 64) - mf.Manifold.cylinder(60, rr * 0.82 - 3, rr - 3, 64).translate((0, 0, 3))
    return m.translate((cx, cy, z_cub + T - 50))
platos = [plato(OX + Wc / 2 + (k - 0.5) * (DP + 45) , OY + 30 + Dc / 2) for k in (0, 1)]
platos = [plato(OX + 45 + DP / 2 + k * (DP + 45), OY + 30 + Dc / 2) for k in (0, 1)]
mallas = [a_trimesh(p3d[k]) for k in nom] + [a_trimesh(com3d[k]) for k in cn] + [a_trimesh(c) for c in cunas3d]
col = [mad] * (len(nom) + len(cn)) + [osc] * len(cunas3d)
render(mallas, os.path.join(aqui, f"vista-{TALLA}.png"), f"Cama sofá para perro — talla {TALLA}, MDF 18 mm",
       colores=col, elev=24, azim=-125, zoom=1.08)
render(mallas + [a_trimesh(cojin())] + [a_trimesh(p) for p in platos], os.path.join(aqui, f"vista-cojin-{TALLA}.png"),
       f"Cama sofá + comedero — talla {TALLA}, de una hoja", colores=col + ["#7f8c99", "#b9c3cc", "#b9c3cc"],
       elev=22, azim=-58, zoom=1.0,
       extras=[None] * len(mallas) + [{"aristas": False, "rugosidad": 0.95}] + [{"aristas": False, "metal": 0.8, "rugosidad": 0.3}] * 2)

# ---------- acomodo ----------
hojas = acomodar(list(piezas2d.items()), hoja=HOJA, paso_giro=15, res=4.0, separacion=11)
comedero_aparte = None
if len(hojas) > 1:
    n_cu_com = 2 * (len(R_CUB) + len(R_TRAV))
    cama = {k: g for k, g in piezas2d.items() if not k.startswith("COM-")}
    cus = [k for k in cama if k.startswith("CU")]
    for k in cus[len(cus) - n_cu_com:]:
        cama.pop(k)
    h1 = acomodar(list(cama.items()), hoja=HOJA, paso_giro=15, res=4.0, separacion=11)
    if len(h1) == 1:
        com = {k: g for k, g in piezas2d.items() if k.startswith("COM-")}
        com.update({f"CU-C{j+1}": cuna for j in range(n_cu_com)})
        comedero_aparte = acomodar(list(com.items()), hoja=(1220, 700), paso_giro=15, res=4.0, separacion=11)
        hojas = h1
        print(f"  la cama cabe sola en 1 hoja; el comedero va aparte (sobrante de 1220 x 700)")
ap = aprovechamiento(hojas, HOJA)
print(f"  piezas: {sum(len(h) for h in hojas)} | hojas: {len(hojas)} | aprovechamiento: {', '.join(f'{a*100:.0f}%' for a in ap)}")
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
        ax.fill(xx, yy, fc=osc if p["nombre"].startswith("CU") else mad, ec="#5a4026", lw=0.5)
        for q in g.interiors:
            xx, yy = q.xy; ax.fill(xx, yy, fc="#f7f4ee", ec="#2b6cb0", lw=0.4)
        if not p["nombre"].startswith("CU"):
            c = g.representative_point(); ax.text(c.x, c.y, p["nombre"].replace("COM-", "COMEDERO\n"), ha="center", fontsize=5.5)
    doc.saveas(os.path.join(aqui, f"cama-{TALLA}-hoja-{k+1}.dxf"))
    ax.set_title(f"Talla {TALLA} — hoja {k+1}: {len(ps)} piezas · {ap[k]*100:.0f}% en piezas", fontsize=9)
    ax.set_aspect("equal"); ax.set_xlim(-20, HOJA[0] + 20); ax.set_ylim(-20, HOJA[1] + 20); ax.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(aqui, f"hoja-{TALLA}.png"), facecolor="white"); plt.close(fig)
if comedero_aparte:
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for nm, cc_ in (("CORTE_EXT", 1), ("CORTE_INT", 5)):
        doc.layers.add(nm, color=cc_)
    msp = doc.modelspace()
    for ps in comedero_aparte:
        for p in ps:
            g = p["geom"]
            msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
            for q in g.interiors:
                msp.add_lwpolyline(list(q.coords), close=True, dxfattribs={"layer": "CORTE_INT"})
    doc.saveas(os.path.join(aqui, f"comedero-{TALLA}.dxf"))
print(f"  exterior: {W + 2 * (T + P):.0f} ancho x {L_LAT:.0f} fondo x {ALTO:.0f} alto mm")
