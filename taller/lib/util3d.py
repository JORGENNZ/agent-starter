"""Utilidades compartidas: exportar mallas y renderizar vistas previas."""
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


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


def render(mallas, ruta_png, titulo="", elev=28, azim=-55, colores=None):
    """Vista previa sombreada simple con matplotlib."""
    fig = plt.figure(figsize=(8, 6), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    luz = np.array([0.4, -0.5, 0.8]); luz /= np.linalg.norm(luz)
    todos = []
    for i, t in enumerate(mallas):
        base = np.array(matplotlib.colors.to_rgb((colores or ["#e07a2f"])[i % len(colores or [1])]))
        # triángulos pequeños = mejor orden de dibujo en matplotlib
        tam = max(t.extents) / 45
        vs, fs = trimesh.remesh.subdivide_to_size(t.vertices, t.faces, max_edge=tam)
        t = trimesh.Trimesh(vs, fs, process=False)
        tri = t.vertices[t.faces]
        sh = np.clip(t.face_normals @ luz, 0, 1) * 0.65 + 0.35
        col = np.clip(base[None, :] * sh[:, None], 0, 1)
        ax.add_collection3d(Poly3DCollection(tri, facecolors=col, edgecolors=col, linewidths=0.3))
        todos.append(t.vertices)
    v = np.vstack(todos)
    c = (v.max(0) + v.min(0)) / 2; r = (v.max(0) - v.min(0)).max() / 2 * 0.72
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    if titulo:
        ax.set_title(titulo, fontsize=12)
    fig.tight_layout(); fig.savefig(ruta_png, facecolor="white"); plt.close(fig)
