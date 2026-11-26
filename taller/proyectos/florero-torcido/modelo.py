"""Florero torcido — Bambu Lab A2L, PLA (modo espiral / vase mode).

Pieza decorativa para producir en serie: el modelo es sólido y el slicer lo imprime
como una sola pared continua (Spiral vase), así sale rápido y con muy poco material.
Cambia LOBULOS, GIRO o ESCALA_ARRIBA para hacer variantes de la misma colección.
    python3 taller/proyectos/florero-torcido/modelo.py
"""
import math, os, sys
import manifold3d as mf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.util3d import exportar, render, a_trimesh

# ---------------- Parámetros (mm) ----------------
VARIANTES = {           # nombre: (radio base, alto, lóbulos, profundidad lóbulo, giro°, escala arriba)
    "alto":   (45, 180, 9, 0.14, 120, 1.25),
    "bajo":   (55, 110, 12, 0.10, -90, 0.80),
    "botella": (38, 200, 6, 0.18, 200, 0.55),
}
SEG = 360
# -------------------------------------------------

def florero(r, alto, lobulos, prof, giro, escala):
    pts = []
    for k in range(SEG):
        th = 2 * math.pi * k / SEG
        rr = r * (1 + prof * math.cos(lobulos * th))
        pts.append((rr * math.cos(th), rr * math.sin(th)))
    return mf.Manifold.extrude(mf.CrossSection([pts]), alto, n_divisions=int(alto / 1.5),
                               twist_degrees=giro, scale_top=(escala, escala))

aqui = os.path.dirname(os.path.abspath(__file__))
mallas, x = [], 0
for i, (nombre, p) in enumerate(VARIANTES.items()):
    m = florero(*p)
    t = exportar(m, os.path.join(aqui, f"florero-{nombre}"))
    print(f"{nombre}: {t.extents[0]:.0f} × {t.extents[1]:.0f} × {t.extents[2]:.0f} mm")
    if i: x += p[0] * 1.3 + 12
    mallas.append(a_trimesh(m.translate((x, 0, 0))))
    x += p[0] * 1.3 + 12

render(mallas, os.path.join(aqui, "vista.png"), "Colección de floreros — A2L, PLA (vase mode)",
       colores=["#d9c8f0", "#f2b5a7", "#a8d5ba"], elev=14, azim=-80,
       extras=[{"aristas": False, "rugosidad": 0.5}] * 3)
