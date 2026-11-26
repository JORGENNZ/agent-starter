"""Porta-fresas para la CNC — impresión en Bambu Lab A2L, PLA.

Bloque con barrenos para fresas de zanco 1/4" (fila trasera, escalonada más alta)
y 1/8" (fila delantera). Cambia los parámetros y vuelve a correr:
    python3 taller/proyectos/porta-fresas/modelo.py
"""
import os, sys
import manifold3d as mf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import exportar, render

# ---------------- Parámetros (mm) ----------------
N_GRANDES = 6           # fresas de 1/4"
N_CHICAS = 8            # fresas de 1/8"
ZANCO_GRANDE = 6.35     # 1/4"
ZANCO_CHICO = 3.175     # 1/8"
HOLGURA = 0.35          # holgura en diámetro: entra y sale fácil sin bailar
PROF = 18               # profundidad del barreno
PASO = 16               # separación entre centros
LARGO = max(N_GRANDES, N_CHICAS) * PASO * 0.75 + 16  # ajusta al número de barrenos
ANCHO = 52
ALTO_BAJO = 22          # escalón delantero (1/8")
ALTO_ALTO = 32          # escalón trasero (1/4"), más alto para verlas y tomarlas
CHAFLAN = 1.2           # chaflán de entrada en cada barreno
# -------------------------------------------------

def barreno(d, z_top):
    d += HOLGURA
    cil = mf.Manifold.cylinder(PROF + 1, d / 2, d / 2, 48).translate((0, 0, z_top - PROF))
    cono = mf.Manifold.cylinder(CHAFLAN + 0.01, d / 2, d / 2 + CHAFLAN, 48).translate((0, 0, z_top - CHAFLAN))
    return cil + cono

def fila(n, d, y, z_top):
    paso = (LARGO - 16) / max(n - 1, 1)
    out = mf.Manifold()
    for i in range(n):
        out += barreno(d, z_top).translate((8 + i * paso, y, 0))
    return out

frente = mf.Manifold.cube((LARGO, ANCHO / 2, ALTO_BAJO))
atras = mf.Manifold.cube((LARGO, ANCHO / 2, ALTO_ALTO)).translate((0, ANCHO / 2, 0))
cuerpo = frente + atras
cuerpo -= fila(N_CHICAS, ZANCO_CHICO, ANCHO / 4, ALTO_BAJO)
cuerpo -= fila(N_GRANDES, ZANCO_GRANDE, 3 * ANCHO / 4, ALTO_ALTO)

aqui = os.path.dirname(os.path.abspath(__file__))
t = exportar(cuerpo, os.path.join(aqui, "porta-fresas"))
render([t], os.path.join(aqui, "vista.png"), "Porta-fresas — A2L, PLA", colores=["#3b82c4"])
print("Medidas:", [round(x, 1) for x in t.extents], "mm | volumen:", round(t.volume / 1000, 1), "cm³")
