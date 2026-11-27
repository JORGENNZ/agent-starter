"""Librero Skyline — 100 % CNC, MDF de 18 mm, sin tornillos. Versión interiorismo.

4 paredes verticales a distancias distintas + 6 repisas, unidas por encastre a media
madera. Cada repisa entra por el frente y se desliza hacia atrás (una por una).
- Más profundo abajo (320) y más delgado arriba (220): peso abajo, se ve ligero.
- Las paredes sobresalen arriba a distintas alturas con puntas redondas (skyline).
- Repisas con el frente abombado entre paredes y puntas redondas que sobresalen.
- Nichos de distintos tamaños, uno alto (660 mm) para vinilos o plantas.
- Celosía de arcos al fondo del nicho alto (punto focal, filtra la luz).
- 2 paneles de fondo de acento (para pintar de otro color); uno con "ojo" redondo.
- Canal para tira LED fresada bajo las repisas (bolsillo de 8 mm, cara de abajo),
  con salida de cable hacia atrás.
- 3 paletas de acabados: nórdico, terracota y contemporáneo.
- Lo que sobra de las hojas se llena con sujetalibros a juego.

SEGURIDAD: un librero alto SIEMPRE se ancla a la pared (barrenos en la repisa de arriba).

Capas: BOLSILLO_LED_8mm (pocket, 8 mm) -> CORTE_INT (cajas, celosía, barrenos) -> CORTE_EXT.
Las repisas con canal LED salen acomodadas "boca abajo" (la cara de la canal hacia arriba).
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
from lib.nesting import acomodar, aprovechamiento, rellenar, orientar

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
# paneles de fondo: (nombre, pared izq, pared der, repisa de abajo, repisa de arriba, tipo)
PANELES = [("CELOSIA", 2, 3, 1, 3, "celosia"), ("FONDO-1", 1, 2, 0, 1, "ojo"), ("FONDO-2", 2, 3, 4, 5, "liso")]
Y_PANEL = 9                              # el panel va 9 mm adelante de la orilla trasera
SOMBRA = 13                              # junta de sombra arriba del panel (permite subirlo para montarlo)
ESP_ABAJO, ANCHO_ESP = 12, 40            # espiga de abajo (12 mm) y ancho de espigas
LED = dict(ancho=12, prof=8, del_frente=26, repisas=(1, 2, 3, 4, 5))
PALETAS = {
    "Nórdico": dict(estructura="#eee7dc", repisas="#cfa979", acento1="#a3b18a", acento2="#e4e8dc",
                    celosia="#cfa979", pared="#efebe4", piso="#c7a37a", tapete="#ddd5c7"),
    "Terracota": dict(estructura="#eadfce", repisas="#eadfce", acento1="#c0643c", acento2="#dba07a",
                      celosia="#b4572f", pared="#f3e9dc", piso="#a97955", tapete="#e2c8a4"),
    "Contemporáneo": dict(estructura="#2e2c2a", repisas="#7a5638", acento1="#b0905a", acento2="#3e4944",
                          celosia="#b0905a", pared="#d8d3cc", piso="#8b7562", tapete="#4b4845"),
}
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

def panel_info(nombre, a, b, ab, ar, tipo):
    x0, x1 = X_PAREDES[a] + T + 1, X_PAREDES[b] - 1
    z0, z1 = REPISAS[ab][0] + T, REPISAS[ar][0]
    xs_esp = [x0 + (x1 - x0) * f for f in (0.25, 0.75)]
    return dict(nombre=nombre, x0=x0, x1=x1, z0=z0, z1=z1, xs=xs_esp, ab=ab, ar=ar, tipo=tipo, a=a, b=b)
PINFO = [panel_info(*p) for p in PANELES]

def cajas_panel_en_repisa(j):
    cs = []
    for pi in PINFO:
        if j in (pi["ab"], pi["ar"]):
            for xe in pi["xs"]:
                c = [(xe - ANCHO_ESP / 2 - HOLG / 2, Y_PANEL - HOLG / 2), (xe + ANCHO_ESP / 2 + HOLG / 2, Y_PANEL - HOLG / 2),
                     (xe + ANCHO_ESP / 2 + HOLG / 2, Y_PANEL + T + HOLG / 2), (xe - ANCHO_ESP / 2 - HOLG / 2, Y_PANEL + T + HOLG / 2)]
                cs.append(unary_union([Polygon(c)] + [dogbone(q, d) for q, d in zip(c, [(1, 1), (-1, 1), (-1, -1), (1, -1)])]))
        # muesca: si una repisa con vuelo cruza el panel (entre sus repisas de abajo y arriba)
        z = REPISAS[j][0]
        if pi["z0"] < z < pi["z1"]:
            xa, xb = pi["x0"] - 3.0, pi["x1"] + 0.5   # se junta con la ranura de la pared: sin astillas
            yb = Y_PANEL + T + 1.5
            cs.append(unary_union([box(xa, -5, xb, yb), dogbone((xa, yb), (1, -1)), dogbone((xb, yb), (-1, -1))]))
    return cs

def canal_led(j):
    z, a, b = REPISAS[j]
    d = prof(z)
    x0, x1 = xc[a] - T / 2 - VUELO + 25, xc[b] + T / 2 + VUELO - 25
    y1 = d - LED["del_frente"]; y0 = y1 - LED["ancho"]
    frente = box(x0, y0, x1, y1)
    cable = box(x1 - 20, -5, x1 - 20 + LED["ancho"], y1)
    return frente.union(cable).buffer(-2, join_style=1).buffer(2, join_style=1)

def panel(pi):
    w, h = pi["x1"] - pi["x0"], pi["z1"] - pi["z0"] - SOMBRA     # el panel es SOMBRA mm más bajo que el hueco
    p = box(0, 0, w, h).buffer(-4, join_style=1).buffer(4, join_style=1)
    for xe in pi["xs"]:
        u = xe - pi["x0"]
        p = p.union(box(u - ANCHO_ESP / 2, -ESP_ABAJO, u + ANCHO_ESP / 2, 1))
        p = p.union(box(u - ANCHO_ESP / 2, h - 1, u + ANCHO_ESP / 2, h + SOMBRA + T))   # queda al ras arriba
    hue = []
    if pi["tipo"] == "ojo":
        hue.append(Point(w / 2, h * 0.55).buffer(min(w, h) * 0.3, 128))
    elif pi["tipo"] == "celosia":
        m, va, ga, alto = 28, 34, 11, 86                  # margen, ancho de arco, puente, alto de arco
        n = int((w - 2 * m + ga) // (va + ga)); off = (w - (n * va + (n - 1) * ga)) / 2
        filas = int((h - 2 * m + ga) // (alto + ga)); offz = (h - (filas * alto + (filas - 1) * ga)) / 2
        for f in range(filas):
            for c in range(n):
                x = off + c * (va + ga); zz = offz + f * (alto + ga)
                arco = box(x, zz, x + va, zz + alto - va / 2).union(Point(x + va / 2, zz + alto - va / 2).buffer(va / 2, 48))
                hue.append(arco)
    return p.difference(unary_union(hue)) if hue else p

piezas2d = {}
for k in range(len(X_PAREDES)):
    piezas2d[f"PARED-{k+1}"] = pared(k)
for j, (z, a, b) in enumerate(REPISAS):
    g = repisa(z, a, b)
    if j == len(REPISAS) - 1:   # barrenos de anclaje a la pared en la repisa de arriba
        for i in (a + 1, b - 1):
            g = g.difference(Point((xc[i] + xc[i - 1 if i > a else i + 1]) / 2 + 0, 25).buffer(4.5, 32))
    cs = cajas_panel_en_repisa(j)
    if cs:
        g = g.difference(unary_union(cs))
    piezas2d[f"REPISA-{j+1}"] = g
bolsillos = {f"REPISA-{j+1}": canal_led(j).intersection(Polygon(piezas2d[f"REPISA-{j+1}"].exterior.coords))
             for j in LED["repisas"]}   # la canal del cable sale por la orilla trasera
for pi in PINFO:
    piezas2d[pi["nombre"]] = panel(pi)

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
    m = colocar(ext(piezas2d[f"REPISA-{j+1}"]), [0, 0, z], X, Y, Z)
    if f"REPISA-{j+1}" in bolsillos:
        m = m - colocar(ext(bolsillos[f"REPISA-{j+1}"], LED["prof"] + 0.01), [0, 0, z - 0.01], X, Y, Z, LED["prof"])
    p3d[f"REPISA-{j+1}"] = m
for pi in PINFO:
    p3d[pi["nombre"]] = colocar(ext(piezas2d[pi["nombre"]]), [pi["x0"], Y_PANEL, pi["z0"]], X, Z, Y)
nom = list(p3d)
peor = max((p3d[u] ^ p3d[v]).volume() for i, u in enumerate(nom) for v in nom[i + 1:])
print(f"Interferencia máxima entre piezas: {peor:.3f} mm³")
cruces = 0
for j, (z, a, b) in enumerate(REPISAS):
    for k in range(a, b + 1):
        lleno = colocar(ext(Polygon([(0, z - 5), (prof(z) + 40, z - 5), (prof(z) + 40, z + T + 5), (0, z + T + 5)])),
                        [X_PAREDES[k], 0, 0], Y, Z, X)
        cruces += (p3d[f"REPISA-{j+1}"] ^ lleno).volume() > 0.4 * T * T * prof(z) / 2
print(f"Cruces repisa/pared trabados: {cruces} de {sum(b - a + 1 for _, a, b in REPISAS)}")
for pi in PINFO:   # cada panel: sus 4 espigas dentro de las repisas
    dentro = sum((p3d[pi["nombre"]] ^ colocar(ext(box(-2000, -50, 4000, 400)), [0, 0, REPISAS[jj][0]], X, Y, Z)).volume()
                 for jj in (pi["ab"], pi["ar"]))
    esperado = 2 * ANCHO_ESP * T * (ESP_ABAJO + T)
    assert ESP_ABAJO < SOMBRA, "la junta de sombra debe ser mayor que la espiga de abajo"
    print(f"  {pi['nombre']}: espigas dentro de las repisas {dentro / esperado * 100:.0f}% de lo esperado")
    # al montarlo se sube ESP_ABAJO mm: la espiga de arriba sale por la repisa (caja pasante) sin chocar
    subido = p3d[pi["nombre"]].translate((0, 0, ESP_ABAJO + 0.5))
    choque = sum((subido ^ p3d[k]).volume() for k in nom if k.startswith("REPISA") or k.startswith("PARED"))
    print(f"    al subirlo {ESP_ABAJO + 0.5:.1f} mm para montarlo: choque {choque:.2f} mm³")
    assert choque < 0.01, "el panel no se puede montar"

def puente(gm):
    hs = [Polygon(h_) for h_ in gm.interiors]
    ext_ = Polygon(gm.exterior.coords).exterior
    return min([ext_.distance(h_) for h_ in hs] + [hs[a_].distance(hs[b_]) for a_ in range(len(hs)) for b_ in range(a_ + 1, len(hs))] + [99])
for n_, gm in piezas2d.items():
    assert gm.geom_type == "Polygon", f"{n_} sale en pedazos"
    assert puente(gm) >= 6, f"{n_}: puente de {puente(gm):.1f} mm"
    if n_ in bolsillos:
        hs_ = [Polygon(h_) for h_ in gm.interiors]
        assert all(bolsillos[n_].distance(h_) >= 4 for h_ in hs_), f"canal LED de {n_} toca un hueco"
print("Todas las piezas enteras; puentes >= 6 mm; canales LED sin tocar cajas ni barrenos")

# ---------- ambientes ----------
aqui = os.path.dirname(os.path.abspath(__file__))
def caja3(x0, y0, z0, x1, y1, z1):
    return mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
def libros(x0, x1, z, d, semilla, cols):
    rng = np.random.default_rng(semilla); out = []; x = x0 + 4
    while x < x1 - 30:
        w = rng.uniform(16, 38); h = rng.uniform(0.62, 0.95) * min(290, d * 1.15)
        if x + w > x1 - 4: break
        out.append((mf.Manifold.cube((w - 1.5, d * rng.uniform(0.6, 0.75), h)).translate((x, d * 0.1, z + T)),
                    cols[int(rng.integers(len(cols)))]))
        x += w
    return out
def jarron(x, y, z, r, h, col):
    cuerpo = mf.Manifold.cylinder(h * 0.7, r * 0.75, r, 48).translate((x, y, z)) + \
             mf.Manifold.sphere(r, 48).scale((1, 1, 0.8)).translate((x, y, z + h * 0.55)) + \
             mf.Manifold.cylinder(h * 0.3, r * 0.4, r * 0.35, 32).translate((x, y, z + h * 0.7))
    return [(cuerpo, col)]
def planta(x, y, z, r, h, maceta, rng):
    out = [(mf.Manifold.cylinder(h * 0.35, r * 0.8, r, 48).translate((x, y, z)), maceta)]
    for _ in range(14):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.2, 1.0) * r * 1.3
        out.append((mf.Manifold.sphere(rng.uniform(0.35, 0.55) * r, 20).scale((1, 1, 1.4)).translate(
            (x + rr * math.cos(a), y + rr * math.sin(a), z + h * rng.uniform(0.45, 1.0))), "#5f7f4f"))
    return out

def escena(pal, noche=False):
    rng = np.random.default_rng(7)
    mallas, cols, ext_ = [], [], []
    def add(m, c, **kw):
        mallas.append(a_trimesh(m)); cols.append(c); ext_.append(kw or None)
    for k in nom:
        c = pal["estructura"] if k.startswith("PARED") else pal["repisas"]
        if k == "CELOSIA": c = pal["celosia"]
        if k == "FONDO-1": c = pal["acento1"]
        if k == "FONDO-2": c = pal["acento2"]
        add(p3d[k], c)
    # tiras LED
    luces = []
    for j in LED["repisas"]:
        z, a, b = REPISAS[j]; d = prof(z); y1 = d - LED["del_frente"]
        x0, x1 = xc[a] - T / 2 - VUELO + 30, xc[b] + T / 2 + VUELO - 30
        add(caja3(x0, y1 - LED["ancho"] + 2, z + 1, x1, y1 - 2, z + 4), "#fff4dc",
            emisivo="#ffd9a0", intensidad=3.0 if noche else 1.2, aristas=False, sombra=False)
        for i in range(a, b):
            for f in (0.3, 0.7):
                luces.append(dict(tipo="foco", pos=[xc[i] + (xc[i + 1] - xc[i]) * f, y1 - 6, z - 2], color="#ffc977",
                                  intensidad=2.2 if noche else 0.4, distancia=430, angulo=75, penumbra=0.9))
    # cuarto
    add(caja3(-1400, -60, -30, 2600, -2, 2700), pal["pared"], encuadre=False, aristas=False, rugosidad=0.95)
    add(caja3(-1400, -60, -30, 2600, 2400, 0), pal["piso"], encuadre=False, aristas=False, rugosidad=0.6)
    add(caja3(-250, 380, 0, 1450, 1700, 6), pal["tapete"], encuadre=False, aristas=False, rugosidad=1.0)
    # decoración
    paleta_libros = ["#efe6d6", "#c9b79c", "#8a9a7b", "#3f4b5a", "#b86b4b", "#d9cbb0", "#6c6258"]
    for j, (z, a, b) in enumerate(REPISAS[:-1]):
        for i in range(a, b):
            l, rr = xc[i] + T / 2, xc[i + 1] - T / 2
            sel = rng.random()
            if (i, j) in ((2, 1), (1, 0)):   # nichos con panel: objeto, no libros
                if (i, j) == (2, 1):
                    for m, c in planta((l + rr) / 2, prof(z) * 0.55, z + T, 55, 300, "#e9e4dc", rng): add(m, c, aristas=False)
                else:
                    for m, c in jarron((l + rr) / 2, prof(z) * 0.55, z + T, 55, 170, "#f2efe9"): add(m, c, aristas=False)
                continue
            if sel < 0.6:
                ancho = (rr - l) * rng.uniform(0.45, 0.8); x0 = l if rng.random() < 0.5 else rr - ancho
                for m, c in libros(x0, x0 + ancho, z, prof(z), j * 10 + i, paleta_libros): add(m, c, aristas=False)
                resto = (l + ancho + 50) if x0 == l else (l + 50)
                if rr - l - ancho > 110:
                    xj = (x0 + ancho + rr) / 2 if x0 == l else (l + x0) / 2
                    for m, c in jarron(xj, prof(z) * 0.5, z + T, 32, 120, ["#d6c7b0", "#8c8c84", "#b5694a"][int(rng.integers(3))]):
                        add(m, c, aristas=False)
            elif sel < 0.8:
                for m, c in jarron((l + rr) / 2, prof(z) * 0.5, z + T, 40, 150, "#cfc6b8"): add(m, c, aristas=False)
    for m, c in planta(xc[0] + 150, 120, REPISAS[-1][0] + T, 60, 260, "#d8cfc2", rng): add(m, c, aristas=False)
    for m, c in planta(1420, 380, 0, 150, 1050, "#cbbfae", rng): add(m, c, aristas=False)
    kw = dict(fondo=pal["pared"], luces=luces)
    if noche:
        kw.update(ambiente=0.16, sol=0.12, relleno=0.06, fondo="#1d1b19")
    return mallas, cols, ext_, kw

for nombre_p, pal in PALETAS.items():
    ms, cs_, ex, kw = escena(pal)
    clave = nombre_p.lower().replace("á", "a").replace("ó", "o")
    render(ms, os.path.join(aqui, f"ambiente-{clave}.png"), f"Librero Skyline — {nombre_p}", colores=cs_,
           extras=ex, elev=7, azim=62, zoom=0.92, **kw)
ms, cs_, ex, kw = escena(PALETAS["Contemporáneo"], noche=True)
render(ms, os.path.join(aqui, "ambiente-noche.png"), "Librero Skyline — de noche, con LED", colores=cs_,
       extras=ex, elev=7, azim=62, zoom=0.92, **kw)

# ---------- acomodo ----------
# las repisas con canal LED se acomodan volteadas (la cara de la canal hacia arriba en la CNC)
espejo_x = lambda g: affinity.scale(g, -1, 1, origin=(0, 0))
para_cortar = {k: (espejo_x(g) if k in bolsillos else g) for k, g in piezas2d.items()}
hojas = acomodar(list(para_cortar.items()), hoja=HOJA, paso_giro=90, res=4.0, separacion=11,
                 sin_espejo=set(bolsillos))
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
      f"solo librero: {', '.join(f'{a*100:.0f}%' for a in ap0)} | + {n_sl} sujetalibros: {', '.join(f'{a*100:.0f}%' for a in ap)}")

mad = "#dcc19a"
fig, axs = plt.subplots(1, len(hojas), figsize=(4.6 * len(hojas), 8.6), dpi=170, squeeze=False)
for k, ps in enumerate(hojas):
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for nm, cc in (("CORTE_EXT", 1), ("CORTE_INT", 5), ("BOLSILLO_LED_8mm", 3)):
        doc.layers.add(nm, color=cc)
    msp = doc.modelspace(); ax = axs[0][k]
    ax.add_patch(plt.Rectangle((0, 0), *HOJA, fc="#f7f4ee", ec="#999", ls="--"))
    for p in ps:
        g = p["geom"]
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
        for q in g.interiors:
            msp.add_lwpolyline(list(q.coords), close=True, dxfattribs={"layer": "CORTE_INT"})
        xx, yy = g.exterior.xy
        fc = "#8f6a42" if p["nombre"].startswith("SL") else ("#c0643c" if p["nombre"] in ("CELOSIA", "FONDO-1", "FONDO-2") else mad)
        ax.fill(xx, yy, fc=fc, ec="#5a4026", lw=0.5)
        for q in g.interiors:
            xx, yy = q.xy; ax.fill(xx, yy, fc="#f7f4ee", ec="#2b6cb0", lw=0.4)
        if p["nombre"] in bolsillos:
            b_ = affinity.translate(orientar(espejo_x(bolsillos[p["nombre"]]), p["ang"], False), p["dx"], p["dy"])
            msp.add_lwpolyline(list(b_.exterior.coords), close=True, dxfattribs={"layer": "BOLSILLO_LED_8mm"})
            xx, yy = b_.exterior.xy; ax.fill(xx, yy, fc="#f2c14e", ec="#a07a1e", lw=0.4)
        if not p["nombre"].startswith("SL"):
            c = g.representative_point(); ax.text(c.x, c.y, p["nombre"], ha="center", fontsize=6)
    doc.saveas(os.path.join(aqui, f"hoja-{k+1}.dxf"))
    ax.set_title(f"Hoja {k+1}: {ap[k]*100:.0f}% en piezas", fontsize=9)
    ax.set_aspect("equal"); ax.set_xlim(-20, HOJA[0] + 20); ax.set_ylim(-20, HOJA[1] + 20); ax.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hojas.png"), facecolor="white"); plt.close(fig)
mad = "#dcc19a"
ancho_tot = xc[-1] + T / 2 + VUELO - (xc[0] - T / 2 - VUELO)
print(f"Medidas: {ancho_tot:.0f} ancho x {PROF_ABAJO + ABOMBADO:.0f} fondo x {max(TOPES)} alto mm")
