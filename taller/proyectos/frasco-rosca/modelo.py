"""Frasco con tapa de rosca — Bambu Lab P2S, PETG.

La rosca es trapezoidal de 4 mm de paso, con flancos de menos de 45°, así que la
tapa se imprime boca abajo sin soportes. Holgura radial de 0.4 mm entre frasco y tapa.
    python3 taller/proyectos/frasco-rosca/modelo.py
"""
import math, os, sys
import manifold3d as mf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import exportar, render, a_trimesh

# ---------------- Parámetros (mm) ----------------
R_CUERPO = 42.0       # radio exterior del frasco (y de la tapa)
ALTO_CUERPO = 85.0
PARED = 2.4
FONDO = 2.0
PASO = 4.0            # paso de la rosca
PROF_ROSCA = 1.4
R_RAIZ = 37.0         # radio del cuello en la raíz de la rosca
ALTO_CUELLO = 14.0
HOLGURA = 0.4         # radial, entre rosca macho y hembra
TECHO_TAPA = 2.5
ESTRIAS = 36          # estrías de agarre de la tapa
SEG = 180
# -------------------------------------------------

def perfil_rosca(u):
    """Perfil trapezoidal de un paso (u de 0 a 1) -> fracción de profundidad."""
    cresta, flanco, raiz = 0.6 / 4, 1.2 / 4, 1.0 / 4
    if u < cresta: return 1.0
    u -= cresta
    if u < flanco: return 1 - u / flanco
    u -= flanco
    if u < raiz: return 0.0
    u -= raiz
    return u / flanco

def rosca(r_raiz, alto, extra=0.0):
    pts = []
    for k in range(SEG):
        th = 2 * math.pi * k / SEG
        r = r_raiz + PROF_ROSCA * perfil_rosca(k / SEG) + extra
        pts.append((r * math.cos(th), r * math.sin(th)))
    cs = mf.CrossSection([pts])
    return mf.Manifold.extrude(cs, alto, n_divisions=int(alto / PASO * 90),
                               twist_degrees=360 * alto / PASO)

z_cuello = ALTO_CUERPO
z_top = z_cuello + ALTO_CUELLO

# ---------- Frasco ----------
cuerpo = mf.Manifold.cylinder(ALTO_CUERPO, R_CUERPO, R_CUERPO, SEG)
cuello = mf.Manifold.cylinder(ALTO_CUELLO, R_RAIZ, R_RAIZ, SEG).translate((0, 0, z_cuello))
hilo = rosca(R_RAIZ - 0.5, z_top)  # se extruye desde z=0 para que la fase coincida con la tapa
zona = mf.Manifold.cylinder(ALTO_CUELLO - 3, R_RAIZ + 3, R_RAIZ + 3, SEG).translate((0, 0, z_cuello + 1.5))
# chaflán de entrada arriba de la rosca
chaflan = (mf.Manifold.cylinder(ALTO_CUELLO - 1.5, R_RAIZ + 3, R_RAIZ + 3, SEG).translate((0, 0, z_cuello))
           + mf.Manifold.cylinder(1.5, R_RAIZ + 3, R_RAIZ, SEG).translate((0, 0, z_top - 1.5)))
frasco = cuerpo + cuello + (hilo ^ zona ^ chaflan)
r_in_cuerpo, r_in_cuello = R_CUERPO - PARED, R_RAIZ - PARED
hueco = (mf.Manifold.cylinder(ALTO_CUERPO - 5 - FONDO, r_in_cuerpo, r_in_cuerpo, SEG).translate((0, 0, FONDO))
         + mf.Manifold.cylinder(5, r_in_cuerpo, r_in_cuello, SEG).translate((0, 0, ALTO_CUERPO - 5))   # cono a 45°
         + mf.Manifold.cylinder(ALTO_CUELLO + 1, r_in_cuello, r_in_cuello, SEG).translate((0, 0, ALTO_CUERPO)))
frasco -= hueco

# ---------- Tapa (en posición armada) ----------
z_tapa0 = z_cuello + 1.0
alto_tapa = (z_top + 0.5 + TECHO_TAPA) - z_tapa0
pts = []
for k in range(ESTRIAS * 8):
    th = 2 * math.pi * k / (ESTRIAS * 8)
    r = R_CUERPO + 0.8 * max(0, math.cos(ESTRIAS * th)) ** 0.5
    pts.append((r * math.cos(th), r * math.sin(th)))
tapa = mf.Manifold.extrude(mf.CrossSection([pts]), alto_tapa).translate((0, 0, z_tapa0))
cavidad_alto = z_top + 0.5 - z_tapa0
nucleo = mf.Manifold.cylinder(cavidad_alto, R_RAIZ + HOLGURA, R_RAIZ + HOLGURA, SEG).translate((0, 0, z_tapa0))
hembra = rosca(R_RAIZ - 0.5, z_top + 0.5, extra=HOLGURA) ^ mf.Manifold.cylinder(
    cavidad_alto, R_RAIZ + 4, R_RAIZ + 4, SEG).translate((0, 0, z_tapa0))
entrada = mf.Manifold.cylinder(1.0, R_RAIZ + PROF_ROSCA + HOLGURA + 0.8, R_RAIZ + PROF_ROSCA + HOLGURA,
                               SEG).translate((0, 0, z_tapa0))
tapa -= nucleo + hembra + entrada

# ---------- Revisión de ajuste ----------
choque = (frasco ^ tapa).volume()
print(f"Interferencia frasco/tapa: {choque:.3f} mm³ (debe ser 0)")
print(f"Capacidad aprox: {math.pi * r_in_cuerpo**2 * (ALTO_CUERPO - FONDO - 5) / 1e6 * 1000:.0f} ml")

aqui = os.path.dirname(os.path.abspath(__file__))
exportar(frasco, os.path.join(aqui, "frasco"))
tapa_imp = tapa.rotate((180, 0, 0))
b = tapa_imp.bounding_box()
exportar(tapa_imp.translate((0, 0, -b[2])), os.path.join(aqui, "tapa"))

# vista: frasco y tapa levantada para ver la rosca
render([a_trimesh(frasco), a_trimesh(tapa.translate((0, 0, 30)))], os.path.join(aqui, "vista.png"),
       "Frasco con tapa de rosca — P2S, PETG", colores=["#5fa8a0", "#e07a2f"], elev=18, azim=-60,
       extras=[{"aristas": False, "rugosidad": 0.45}, {"aristas": False, "rugosidad": 0.6}])
