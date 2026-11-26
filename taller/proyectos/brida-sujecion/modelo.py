"""Brida de sujeción (clamp) para la mesa de la CNC — impresión en Bambu Lab P2S, PETG o ASA.

Detiene la hoja de MDF contra la mesa con un tornillo M8 (mesa de ranuras T).
La pata trasera mide lo mismo que el grosor de la pieza, así la brida queda nivelada
y aprieta parejo. Se generan variantes para MDF de 18 y 25 mm.

Los archivos .stl/.3mf ya salen orientados para imprimir (boca abajo, sin soportes,
con las capas a lo largo de la brida para que no se rompa al apretar).
    python3 taller/proyectos/brida-sujecion/modelo.py
"""
import os, sys
import manifold3d as mf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import exportar, render, a_trimesh

# ---------------- Parámetros (mm) ----------------
GROSORES = [18, 25]     # grosor de la pieza a sujetar (MDF real: mídelo)
LARGO = 90
ANCHO = 28
ESPESOR = 14            # espesor del brazo
RANURA = 8.8            # para tornillo M8
RANURA_X = (24, 60)     # dónde empieza y termina la ranura
CAJA_RONDANA = 18       # ancho del rebaje para la rondana
PROF_RONDANA = 3
PAD = 2                 # la nariz baja 2 mm para apretar solo en la punta
LARGO_NARIZ = 14
LARGO_PATA = 16
# -------------------------------------------------

def ranura(ancho, alto, z0):
    r = ancho / 2
    x0, x1 = RANURA_X
    c = mf.Manifold.cube((x1 - x0, ancho, alto)).translate((x0, ANCHO / 2 - r, z0))
    c += mf.Manifold.cylinder(alto, r, r, 48).translate((x0, ANCHO / 2, z0))
    c += mf.Manifold.cylinder(alto, r, r, 48).translate((x1, ANCHO / 2, z0))
    return c

def brida(h):
    z_brazo = h + PAD
    brazo = mf.Manifold.cube((LARGO, ANCHO, ESPESOR)).translate((0, 0, z_brazo))
    nariz = mf.Manifold.cube((LARGO_NARIZ, ANCHO, PAD + 0.01)).translate((0, 0, h))
    pata = mf.Manifold.cube((LARGO_PATA, ANCHO, z_brazo + 0.01)).translate((LARGO - LARGO_PATA, 0, 0))
    b = brazo + nariz + pata
    b -= ranura(RANURA, ESPESOR + 2, z_brazo - 1)
    b -= ranura(CAJA_RONDANA, PROF_RONDANA + 1, z_brazo + ESPESOR - PROF_RONDANA)
    return b

aqui = os.path.dirname(os.path.abspath(__file__))
for h in GROSORES:
    b = brida(h)
    tope = h + PAD + ESPESOR
    impresion = b.rotate((180, 0, 0)).translate((0, ANCHO, tope))  # boca abajo sobre la cama
    t = exportar(impresion, os.path.join(aqui, f"brida-mdf{h}"))
    print(f"MDF {h} mm ->", [round(x, 1) for x in t.extents], "mm")

# vista: brida de 18 sobre una hoja de MDF, 
h = GROSORES[0]
mdf = mf.Manifold.cube((70, 70, h)).translate((-55, -21, 0))
render([a_trimesh(brida(h)), a_trimesh(mdf)],
       os.path.join(aqui, "vista.png"), "Brida de sujeción — P2S, PETG/ASA",
       colores=["#e07a2f", "#c8a97e"], azim=-60)
