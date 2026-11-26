"""Utilidades compartidas: exportar mallas y renderizar vistas previas."""
import json, os, subprocess, tempfile
import numpy as np
import trimesh

RENDER_JS = os.path.join(os.path.dirname(__file__), "..", "render", "render.js")


def a_trimesh(m):
    """Convierte un manifold3d.Manifold a trimesh.Trimesh."""
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def exportar(m, ruta_sin_ext):
    """Guarda STL y 3MF (el 3MF se abre directo en Bambu Studio / Bambu Handy)."""
    t = a_trimesh(m)
    t.export(ruta_sin_ext + ".stl")
    try:
        t.export(ruta_sin_ext + ".3mf")
    except Exception as e:  # el STL siempre queda
        print("No se pudo exportar 3MF:", e)
    return t


def render(mallas, ruta_png, titulo="", elev=28, azim=-55, colores=None, zoom=1.0, extras=None):
    """Render WebGL (three.js en Chromium): profundidad correcta, sombras y aristas.
    `extras`: lista de dicts por malla con opciones (rugosidad, metal, opacidad, aristas)."""
    colores = colores or ["#e07a2f"]
    escena = {"elev": elev, "azim": azim, "zoom": zoom, "mallas": []}
    for i, t in enumerate(mallas):
        d = {"v": np.asarray(t.vertices, float).ravel().round(4).tolist(),
             "f": np.asarray(t.faces, int).ravel().tolist(),
             "color": colores[i % len(colores)]}
        if extras and i < len(extras) and extras[i]:
            d.update(extras[i])
        escena["mallas"].append(d)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(escena, f)
    try:
        subprocess.run(["node", RENDER_JS, f.name, os.path.abspath(ruta_png)], check=True)
    finally:
        os.unlink(f.name)
    if titulo:
        _titulo(ruta_png, titulo)


def _titulo(ruta_png, titulo):
    """Agrega una franja de título arriba de la imagen (sin tapar el modelo)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    img = plt.imread(ruta_png)
    h, w = img.shape[:2]
    banda = int(h * 0.09)
    fig = plt.figure(figsize=(w / 200, (h + banda) / 200), dpi=200)
    fig.patch.set_facecolor("#f4f2ee")
    ax = fig.add_axes([0, 0, 1, h / (h + banda)]); ax.imshow(img); ax.set_axis_off()
    fig.text(0.035, 1 - banda / (h + banda) / 2, titulo, fontsize=15, color="#2b2b2b",
             va="center", weight="bold")
    fig.savefig(ruta_png, facecolor=fig.get_facecolor()); plt.close(fig)
