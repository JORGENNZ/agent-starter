"""Librero Estribo — minimalismo de lujo silencioso. CNC, MDF 18 mm, sin tornillos.

Principios: pocas piezas, proporción, vacío, oficio discreto.
- 3 paredes iguales: remate de medio punto arriba y arco abajo (silueta de estribo);
  el mueble parece flotar.
- 5 repisas lisas, al ras de los costados (sin vuelos). Separaciones que se cierran
  hacia arriba: 380 / 340 / 300 / 260 mm.
- Claros de 560 mm: la repisa de 18 mm no se pandea con libros.
- Único adorno: una línea de "puntadas" de talabartería grabada (V-bit, 1.2 mm) alrededor
  de las caras exteriores. Se rellena con cera de color coñac o se deja en el tono del mueble.
- Unión a media madera; en los costados la punta de la repisa queda al ras, como incrustación.

Capas: GRABADO_COSTURA (V-bit 90°, 1.2 mm) -> CORTE_INT -> CORTE_EXT
    python3 taller/proyectos/librero-estribo/modelo.py
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
D = 320                      # fondo
CLARO = 560                  # claro libre entre paredes
N_PAREDES = 3
ALTO = 1665                  # alto total (la corona del arco)
SEPARACIONES = [380, 340, 300, 260]          # espacio libre entre repisas, de abajo hacia arriba
Z0 = 120                                     # cara de abajo de la primera repisa
Z_REPISAS = [Z0 + sum(SEPARACIONES[:k]) + k * T for k in range(len(SEPARACIONES) + 1)]
ARCO_PIE = dict(ancho=D - 2 * 62, alto=92)  # arco de abajo
COSTURA = dict(margen=14, puntada=7.0, hueco=4.5, prof=1.2)
HOJA = (1220, 2440)
PALETAS = {
    "Crema y coñac": dict(mueble="#e6ddcf", costura="#a9612d", pared="#eee8df", piso="#b48e66", tapete="#ddd3c4"),
    "Roble y coñac": dict(mueble="#c4a27a", costura="#6e4327", pared="#f1ede7", piso="#9c7a5a", tapete="#e3dbd0"),
    "Grafito y coñac": dict(mueble="#3a3835", costura="#b8692f", pared="#d9d3cb", piso="#8c7663", tapete="#4a4643"),
}
# -------------------------------------------------
S = T + HOLG
r = R_FRESA
X_PAREDES = [i * (CLARO + T) for i in range(N_PAREDES)]
ANCHO = X_PAREDES[-1] + T
R_ARCO = D / 2

def dogbone(c, d):
    d = np.array(d, float); d /= np.linalg.norm(d)
    return Point(c[0] + d[0] * r, c[1] + d[1] * r).buffer(r + 0.05, 32)

# ---------- pared (y = fondo, z = alto) ----------
def silueta():
    zc = ALTO - R_ARCO
    arco = [(R_ARCO + R_ARCO * math.cos(a), zc + R_ARCO * math.sin(a)) for a in np.linspace(0, math.pi, 90)]
    p = Polygon([(0, 0), (D, 0)] + arco + [(0, 0)]).buffer(0)
    a0 = (D - ARCO_PIE["ancho"]) / 2
    pie = [(a0 + ARCO_PIE["ancho"] / 2 * (1 - math.cos(t)), ARCO_PIE["alto"] * math.sin(t) ** 0.85)
           for t in np.linspace(0, math.pi, 60)]
    p = p.difference(Polygon([(a0, -5)] + pie + [(a0 + ARCO_PIE["ancho"], -5)]).buffer(6, join_style=1).buffer(-6, join_style=1))
    return p.buffer(-3, join_style=1).buffer(3, join_style=1)

def ranuras_pared():
    cs = []
    for z in Z_REPISAS:
        ym = D / 2; z0, z1 = z - HOLG / 2, z + T + HOLG / 2
        cs += [box(ym, z0, D + 5, z1), dogbone((ym, z0), (1, 1)), dogbone((ym, z1), (1, -1))]
    return unary_union(cs)

assert Z_REPISAS[-1] + T + 10 <= ALTO - D / 2, "la repisa de arriba se mete en el arco"
huecos_reales = [Z_REPISAS[k + 1] - Z_REPISAS[k] - T for k in range(len(Z_REPISAS) - 1)]
assert huecos_reales == SEPARACIONES, huecos_reales
SIL = silueta()
RAN = ranuras_pared()
PARED = SIL.difference(RAN)

def costura(pol, quitar):
    """Línea de puntadas: el contorno metido COSTURA['margen'] mm, en trazos cortos."""
    linea = pol.buffer(-COSTURA["margen"], join_style=1).exterior
    L = linea.length; paso = COSTURA["puntada"] + COSTURA["hueco"]
    n = int(L // paso); ajuste = L / n          # puntadas parejas en todo el contorno
    trazos = []
    zona_prohibida = quitar.buffer(6)
    for k in range(n):
        a = k * ajuste; b = a + COSTURA["puntada"] * ajuste / paso
        seg = LineString([linea.interpolate(t) for t in np.linspace(a, b, 4)])
        if not seg.intersects(zona_prohibida):
            trazos.append(seg)
    return trazos

COSTURA_PARED = costura(SIL, RAN)

# ---------- repisa (x = ancho, y = fondo) ----------
def repisa():
    p = box(0, 0, ANCHO, D)
    cs = []
    for x in X_PAREDES:
        u0, u1 = x - HOLG / 2, x + T + HOLG / 2
        cs.append(box(u0, -5, u1, D / 2))
        for (u, sx) in ((u0, 1), (u1, -1)):
            if 0 < u < ANCHO:
                cs.append(dogbone((u, D / 2), (sx, -1)))
    return p.difference(unary_union(cs))

REP = repisa()
piezas2d = {f"PARED-{i+1}": PARED for i in range(N_PAREDES)}
for j in range(len(Z_REPISAS)):
    piezas2d[f"REPISA-{j+1}"] = REP
# barrenos de anclaje en la repisa de arriba (atrás, al centro de cada claro)
piezas2d[f"REPISA-{len(Z_REPISAS)}"] = REP.difference(unary_union(
    [Point(X_PAREDES[i] + T + CLARO / 2, 30).buffer(4.5, 32) for i in range(N_PAREDES - 1)]))

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
for i, x in enumerate(X_PAREDES):
    p3d[f"PARED-{i+1}"] = colocar(ext(PARED), [x, 0, 0], Y, Z, X)
for j, z in enumerate(Z_REPISAS):
    p3d[f"REPISA-{j+1}"] = colocar(ext(piezas2d[f"REPISA-{j+1}"]), [0, 0, z], X, Y, Z)
nom = list(p3d)
peor = max((p3d[u] ^ p3d[v]).volume() for i, u in enumerate(nom) for v in nom[i + 1:])
print(f"Interferencia máxima entre piezas: {peor:.3f} mm³")
cruces = 0
for j, z in enumerate(Z_REPISAS):
    for i, x in enumerate(X_PAREDES):
        lleno = colocar(ext(box(0, z - 2, D, z + T + 2)), [x, 0, 0], Y, Z, X)
        cruces += (p3d[f"REPISA-{j+1}"] ^ lleno).volume() > 0.45 * T * T * D / 2
print(f"Cruces trabados: {cruces} de {len(Z_REPISAS) * N_PAREDES}")
for n_, g in piezas2d.items():
    assert g.geom_type == "Polygon", f"{n_} sale en pedazos"
print(f"Puntadas por cara exterior: {len(COSTURA_PARED)} | piezas enteras")
# flecha estimada de la repisa (MDF, 40 kg de libros por metro, con fluencia x2.5)
E, w = 3000.0, 40 * 9.81 / 1000
I = D * T ** 3 / 12
flecha = 5 * w * CLARO ** 4 / (384 * E * I) * 2.5
print(f"Flecha estimada con libros a largo plazo: {flecha:.1f} mm en {CLARO} mm de claro")

# ---------- ambientes ----------
aqui = os.path.dirname(os.path.abspath(__file__))
def caja3(x0, y0, z0, x1, y1, z1):
    return mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
def pila(x, y, z, n, rng, cols):
    out, zz = [], z
    for k in range(n):
        w_, d_, h_ = rng.uniform(190, 250), rng.uniform(140, 175), rng.uniform(16, 30)
        out.append((caja3(x - w_ / 2, y - d_ / 2, zz, x + w_ / 2, y + d_ / 2, zz + h_), cols[k % len(cols)]))
        zz += h_
    return out, zz
def parados(x0, z, n, rng, cols):
    out, x = [], x0
    for k in range(n):
        w_, h_ = rng.uniform(18, 30), rng.uniform(210, 255)
        out.append((caja3(x, 40, z, x + w_ - 1.5, 40 + rng.uniform(150, 175), z + h_), cols[k % len(cols)]))
        x += w_
    return out
def jarron(x, y, z, r_, h_, col):
    m = mf.Manifold.cylinder(h_ * 0.75, r_ * 0.7, r_, 64).translate((x, y, z)) + \
        mf.Manifold.sphere(r_, 64).scale((1, 1, 0.55)).translate((x, y, z + h_ * 0.75)) + \
        mf.Manifold.cylinder(h_ * 0.25, r_ * 0.35, r_ * 0.3, 48).translate((x, y, z + h_ * 0.75))
    return [(m, col)]

def puntadas_3d(i_pared, lado):
    """Puntadas como barritas finas sobre la cara exterior de las paredes de los extremos."""
    x = X_PAREDES[i_pared] + (T if lado > 0 else 0)
    out = []
    for seg in COSTURA_PARED:
        (y0, z0), (y1, z1) = seg.coords[0], seg.coords[-1]
        L = math.hypot(y1 - y0, z1 - z0); ang = math.degrees(math.atan2(z1 - z0, y1 - y0))
        m = mf.Manifold.cube((1.2, L, 1.6), center=True).rotate((ang, 0, 0))   # puntada a lo largo de la línea
        out.append(m.translate((x + lado * 0.3, (y0 + y1) / 2, (z0 + z1) / 2)))
    return mf.Manifold.batch_boolean(out, mf.OpType.Add)

def escena(pal):
    rng = np.random.default_rng(11)
    ms, cs, ex = [], [], []
    def add(m, c, **kw):
        ms.append(a_trimesh(m)); cs.append(c); ex.append(kw or None)
    for k in nom:
        add(p3d[k], pal["mueble"], rugosidad=0.55)
    for i_, lado in ((0, -1), (N_PAREDES - 1, 1)):
        add(puntadas_3d(i_, lado), pal["costura"], aristas=False, rugosidad=0.5)
    add(caja3(-1500, -60, -30, ANCHO + 1500, -2, 2900), pal["pared"], encuadre=False, aristas=False, rugosidad=0.95)
    add(caja3(-1500, -60, -30, ANCHO + 1500, 2600, 0), pal["piso"], encuadre=False, aristas=False, rugosidad=0.55)
    add(caja3(-350, 420, 0, ANCHO + 350, 1900, 5), pal["tapete"], encuadre=False, aristas=False, rugosidad=1.0)
    libros = ["#efe9df", "#d7cbb8", "#a99a84", "#5b4a3d", "#e8e2d8"]
    c1 = X_PAREDES[0] + T + CLARO / 2; c2 = X_PAREDES[1] + T + CLARO / 2
    zt = lambda j: Z_REPISAS[j] + T
    # composición: mucho vacío, pocos objetos
    m_, h1 = pila(c1 - 90, D * 0.5, zt(0), 4, rng, libros); [add(a, b, aristas=False) for a, b in m_]
    [add(a, b, aristas=False) for a, b in jarron(c1 + 150, D * 0.5, zt(0), 60, 230, "#d9d2c6")]
    [add(a, b, aristas=False) for a, b in parados(X_PAREDES[1] + T + 8, zt(1), 9, rng, libros)]
    [add(a, b, aristas=False) for a, b in jarron(c2 + 170, D * 0.5, zt(1), 38, 150, "#5b4a3d")]
    add(mf.Manifold.sphere(70, 64).translate((c1, D * 0.5, zt(2) + 70)), "#c8b59a", aristas=False, rugosidad=0.35)
    m_, h3 = pila(c2 + 60, D * 0.5, zt(2), 3, rng, libros[::-1]); [add(a, b, aristas=False) for a, b in m_]
    add(caja3(c2 + 10, D * 0.5 - 60, h3, c2 + 110, D * 0.5 + 60, h3 + 70), pal["costura"], aristas=False, rugosidad=0.45)
    [add(a, b, aristas=False) for a, b in parados(X_PAREDES[0] + T + 330, zt(3), 7, rng, libros)]
    [add(a, b, aristas=False) for a, b in jarron(c2, D * 0.5, zt(3), 45, 200, "#efe9df")]
    return ms, cs, ex

for nombre_p, pal in PALETAS.items():
    ms, cs, ex = escena(pal)
    clave = nombre_p.lower().replace(" y ", "-").replace("ñ", "n")
    render(ms, os.path.join(aqui, f"ambiente-{clave}.png"), f"Librero Estribo — {nombre_p}", colores=cs, extras=ex,
           elev=6, azim=70, zoom=0.95, fondo=pal["pared"])
# detalle de la costura
ms, cs, ex = escena(PALETAS["Crema y coñac"])
render(ms, os.path.join(aqui, "detalle-costura.png"), "Detalle: costura grabada y unión al ras", colores=cs, extras=ex,
       elev=10, azim=165, zoom=0.5, fondo=PALETAS["Crema y coñac"]["pared"],
       objetivo=[0, D * 0.5, ALTO - 330])

# ---------- acomodo ----------
# las paredes de los extremos llevan costura en su cara exterior: la izquierda se corta volteada
espejo = lambda g: affinity.scale(g, -1, 1, origin=(0, 0))
cortar = dict(piezas2d)
cortar["PARED-1"] = espejo(PARED)
grabados = {"PARED-1": [espejo(s_) for s_ in COSTURA_PARED], f"PARED-{N_PAREDES}": COSTURA_PARED}
hojas = acomodar(list(cortar.items()), hoja=HOJA, paso_giro=90, res=4.0, separacion=11, sin_espejo=set(grabados))
ap0 = aprovechamiento(hojas, HOJA)

def sujetalibros(k):
    """Sujetalibros de medio arco, a juego (respaldo + base, espigas a presión)."""
    a_, h_ = 120, 170
    resp = Polygon([(0, 0), (a_, 0), (a_, h_ - a_)] + [(a_ * math.cos(t), h_ - a_ + a_ * math.sin(t)) for t in np.linspace(0, math.pi / 2, 40)] + [(0, 0)]).buffer(0)
    resp = resp.union(box(20, -(T - 0.5), 50, 1)).union(box(a_ - 50, -(T - 0.5), a_ - 20, 1)).buffer(-1, join_style=1).buffer(1, join_style=1)
    base = box(0, 0, a_, 140).buffer(-8, join_style=1).buffer(8, join_style=1)
    for (u0, u1) in ((20, 50), (a_ - 50, a_ - 20)):
        c_ = [(u0 - HOLG / 2, 10), (u1 + HOLG / 2, 10), (u1 + HOLG / 2, 10 + S), (u0 - HOLG / 2, 10 + S)]
        base = base.difference(unary_union([Polygon(c_)] + [dogbone(c, d) for c, d in zip(c_, [(1, 1), (-1, 1), (-1, -1), (1, -1)])]))
    return [(f"SL{k+1}-A", resp), (f"SL{k+1}-B", base)]
n_sl = rellenar(hojas, sujetalibros, hoja=HOJA, separacion=11, giros=range(0, 360, 90), maximo=4)
ap = aprovechamiento(hojas, HOJA)
print(f"Piezas: {len(piezas2d)} | hojas: {len(hojas)} | librero: {', '.join(f'{a*100:.0f}%' for a in ap0)} | "
      f"+ {n_sl} pares de sujetalibros: {', '.join(f'{a*100:.0f}%' for a in ap)}")

fig, axs = plt.subplots(1, len(hojas), figsize=(4.6 * len(hojas), 8.6), dpi=170, squeeze=False)
for k, ps in enumerate(hojas):
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for nm, cc in (("GRABADO_COSTURA", 30), ("CORTE_INT", 5), ("CORTE_EXT", 1)):
        doc.layers.add(nm, color=cc)
    msp = doc.modelspace(); ax = axs[0][k]
    ax.add_patch(plt.Rectangle((0, 0), *HOJA, fc="#f7f4ee", ec="#999", ls="--"))
    for p in ps:
        g = p["geom"]
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CORTE_EXT"})
        for q in g.interiors:
            msp.add_lwpolyline(list(q.coords), close=True, dxfattribs={"layer": "CORTE_INT"})
        xx, yy = g.exterior.xy
        ax.fill(xx, yy, fc="#e6ddcf", ec="#7a6a55", lw=0.5)
        if p["nombre"] in grabados:
            for s_ in grabados[p["nombre"]]:
                s2 = affinity.translate(orientar(s_, p["ang"], False), p["dx"], p["dy"])
                assert g.buffer(-2).contains(s2), "puntada fuera de la pieza"
                msp.add_lwpolyline(list(s2.coords), dxfattribs={"layer": "GRABADO_COSTURA"})
                ax.plot(*s2.xy, color="#a9612d", lw=0.6)
        if not p["nombre"].startswith("SL"):
            c = g.representative_point(); ax.text(c.x, c.y, p["nombre"], ha="center", fontsize=6)
    doc.saveas(os.path.join(aqui, f"hoja-{k+1}.dxf"))
    ax.set_title(f"Hoja {k+1}: {ap[k]*100:.0f}% en piezas", fontsize=9)
    ax.set_aspect("equal"); ax.set_xlim(-20, HOJA[0] + 20); ax.set_ylim(-20, HOJA[1] + 20); ax.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(aqui, "hojas.png"), facecolor="white"); plt.close(fig)
print(f"Medidas: {ANCHO:.0f} ancho x {D} fondo x {ALTO} alto mm")
