"""Acomodo (nesting) de piezas en hojas, por forma real.

- Cada pieza se rasteriza (con separación para la fresa) y se busca dónde cabe con
  correlación por FFT: encuentra TODOS los lugares libres de un jalón, incluidos los
  huecos interiores de otras piezas.
- Prueba rotaciones (cada `paso_giro` grados) y espejo. Espejo = voltear la pieza; en
  corte 2D es la misma pieza física.
- Criterio: dejar todo lo más abajo y compacto posible (tipo "bottom-left").
- Al final verifica con la geometría vectorial exacta que nada se encime ni salga de la hoja.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import fftconvolve
from shapely import affinity
from shapely.geometry import box


def _raster(geom, res, minx, miny, w, h):
    img = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(img)
    polys = getattr(geom, "geoms", [geom])
    for p in polys:
        dr.polygon([((x - minx) / res, (y - miny) / res) for x, y in p.exterior.coords], fill=1)
        for i in p.interiors:
            dr.polygon([((x - minx) / res, (y - miny) / res) for x, y in i.coords], fill=0)
    return np.array(img, dtype=np.float32)


def orientar(g, ang, espejo):
    if espejo:
        g = affinity.scale(g, -1, 1, origin=(0, 0))
    return affinity.rotate(g, ang, origin=(0, 0))


def acomodar(piezas, hoja=(1220, 2440), margen=12, separacion=12, res=4.0,
             paso_giro=15, espejo=True, giros=None, fijas=None, sin_espejo=()):
    """piezas: lista de (nombre, polígono shapely). Devuelve lista de hojas;
    cada hoja es una lista de dicts {nombre, geom, ang, espejo, dx, dy}."""
    W, H = int(hoja[0] / res), int(hoja[1] / res)
    giros = giros if giros is not None else list(range(0, 360, paso_giro))
    hojas, ocup = [], []

    def hoja_nueva():
        o = np.zeros((H, W), np.float32)
        m = int(math.ceil(margen / res))
        o[:m, :] = o[-m:, :] = o[:, :m] = o[:, -m:] = 1
        hojas.append([]); ocup.append(o)

    orden = sorted(piezas, key=lambda p: -p[1].area)
    hoja_nueva()
    for nombre, g in (fijas or []):
        gd = g.buffer(separacion / 2 + res * 0.75, join_style=1)
        ocup[0] += _raster(gd, res, 0, 0, W, H)
        hojas[0].append(dict(nombre=nombre, geom=g, ang=0, espejo=False, dx=0, dy=0))
    for nombre, g in orden:
        k = 0
        while True:
            if k == len(hojas):
                hoja_nueva()
            mejor = None
            for ang in giros:
                for esp in ([False, True] if (espejo and nombre not in sin_espejo) else [False]):
                    go = orientar(g, ang, esp)
                    gd = go.buffer(separacion / 2 + res * 0.75, join_style=1)
                    mnx, mny, mxx, mxy = gd.bounds
                    w, h = int(math.ceil((mxx - mnx) / res)) + 1, int(math.ceil((mxy - mny) / res)) + 1
                    if w >= W or h >= H:
                        continue
                    msk = _raster(gd, res, mnx, mny, w, h)
                    corr = fftconvolve(ocup[k], msk[::-1, ::-1], mode="valid")
                    libres = np.argwhere(corr < 0.5)
                    if not len(libres):
                        continue
                    # criterio: lo más abajo (fila + alto), luego lo más a la izquierda
                    score = (libres[:, 0] + h) * 10000 + libres[:, 1]
                    j = int(np.argmin(score))
                    if mejor is None or score[j] < mejor[0]:
                        mejor = (score[j], libres[j], ang, esp, go, msk, mnx, mny)
            if mejor is None:
                if not hojas[k] and k == len(hojas) - 1:
                    raise ValueError(f"{nombre} no cabe en una hoja vacía")
                k += 1
                continue
            _, (r, c), ang, esp, go, msk, mnx, mny = mejor
            dx, dy = c * res - mnx, r * res - mny
            ocup[k][r:r + msk.shape[0], c:c + msk.shape[1]] += msk
            hojas[k].append(dict(nombre=nombre, geom=affinity.translate(go, dx, dy),
                                 ang=ang, espejo=esp, dx=dx, dy=dy))
            break
    verificar(hojas, hoja, margen, separacion)
    return hojas


def verificar(hojas, hoja, margen, separacion):
    marco = box(margen - 0.5, margen - 0.5, hoja[0] - margen + 0.5, hoja[1] - margen + 0.5)
    for k, ps in enumerate(hojas):
        for i, p in enumerate(ps):
            assert marco.contains(p["geom"]), f"{p['nombre']} se sale de la hoja {k+1}"
            for q in ps[i + 1:]:
                d = p["geom"].distance(q["geom"])
                assert d >= separacion - 1.0, f"{p['nombre']} y {q['nombre']} a {d:.1f} mm"


def aprovechamiento(hojas, hoja=(1220, 2440)):
    area = hoja[0] * hoja[1]
    return [sum(p["geom"].area for p in ps) / area for ps in hojas]


def _paso(a, b, u, sep):
    """Distancia mínima para mover b en dirección u sin acercarse a menos de sep de a."""
    lo, hi = 0.0, 2000.0
    if affinity.translate(b, *(u * hi)).distance(a) < sep:
        return None
    for _ in range(30):
        m = (lo + hi) / 2
        if affinity.translate(b, *(u * m)).distance(a) >= sep:
            hi = m
        else:
            lo = m
    return hi


def pila(piezas, separacion=12, paso_ang=4):
    """Anida piezas parecidas una dentro de otra (como cucharas). Prueba direcciones de
    deslizamiento y se queda con la que deja el bloque de menor área (rectángulo mínimo).
    Devuelve lista de (nombre, geom) en posición relativa."""
    from shapely.ops import unary_union
    mejor = None
    for th in np.arange(0, 360, paso_ang):
        u = np.array([math.cos(math.radians(th)), math.sin(math.radians(th))])
        pos, off = [piezas[0][1]], np.zeros(2)
        for (_, a), (_, b) in zip(piezas, piezas[1:]):
            d = _paso(affinity.translate(a, *off), affinity.translate(b, *off), u, separacion)
            if d is None:
                pos = None; break
            off = off + u * d
            pos.append(affinity.translate(b, *off))
        if pos is None:
            continue
        area = unary_union(pos).minimum_rotated_rectangle.area
        if mejor is None or area < mejor[0]:
            mejor = (area, pos)
    return [(n, g) for (n, _), g in zip(piezas, mejor[1])]


def acomodar_grupos(grupos, sueltas, hoja=(1220, 2440), **kw):
    """grupos: listas de (nombre, geom) que se mueven juntos (pilas). Se acomodan como un
    solo bloque (con giro/espejo) y luego se separan en piezas."""
    from shapely.geometry import MultiPolygon
    from shapely.ops import unary_union
    bloques = [(f"__G{k}", unary_union([g for _, g in grp])) for k, grp in enumerate(grupos)]
    hojas = acomodar(bloques + list(sueltas), hoja=hoja, **kw)
    salida = []
    for ps in hojas:
        lst = []
        for p in ps:
            if p["nombre"].startswith("__G"):
                for n, g in grupos[int(p["nombre"][3:])]:
                    gg = affinity.translate(orientar(g, p["ang"], p["espejo"]), p["dx"], p["dy"])
                    lst.append(dict(nombre=n, geom=gg, ang=p["ang"], espejo=p["espejo"], dx=p["dx"], dy=p["dy"]))
            else:
                lst.append(p)
        salida.append(lst)
    verificar(salida, hoja, kw.get("margen", 12), kw.get("separacion", 12))
    return salida


def acomodar_mirando(grupo, sueltas, hoja=(1220, 2440), margen=12, separacion=12,
                     giro_busqueda=10, **kw):
    """Prueba cada orientación del bloque grande (grupo) en la orilla de la hoja y acomoda
    el resto en lo que queda; se queda con la combinación que use menos hojas / menos largo."""
    from shapely.ops import unary_union
    bloque = unary_union([g for _, g in grupo])
    mejor = None
    for ang in range(0, 360, giro_busqueda):
        for esp in (False, True):
            b = orientar(bloque, ang, esp)
            mnx, mny, mxx, mxy = b.bounds
            if mxx - mnx > hoja[0] - 2 * margen or mxy - mny > hoja[1] - 2 * margen:
                continue
            for lado in ("izq", "der"):
              dx = margen - mnx if lado == "izq" else hoja[0] - margen - mxx
              dy = margen - mny
              fijo = affinity.translate(b, dx, dy)
              try:
                  hs = acomodar(list(sueltas), hoja=hoja, margen=margen, separacion=separacion,
                                res=kw.get("res_busqueda", 6.0),
                                giros=list(range(0, 360, kw.get("giro_sueltas", 15))),
                                fijas=[("__B", fijo)])
              except AssertionError:
                  continue
              usado = max(p["geom"].bounds[3] for p in hs[-1])
              clave = (len(hs), usado)
              if mejor is None or clave < mejor[0]:
                  mejor = (clave, ang, esp, dx, dy, hs)
    clave, ang, esp, dx, dy, hs_burdo = mejor
    fijas = [(n, affinity.translate(orientar(g, ang, esp), dx, dy)) for n, g in grupo]
    hs = acomodar(list(sueltas), hoja=hoja, margen=margen, separacion=separacion,
                  res=kw.get("res", 4.0), paso_giro=kw.get("paso_giro", 5), fijas=fijas)
    if (len(hs), max(p["geom"].bounds[3] for p in hs[-1])) > clave:
        # el acomodo fino salió peor: usa el de la búsqueda (también está verificado)
        hs = [[p for p in ps if p["nombre"] != "__B"] for ps in hs_burdo]
        hs[0] = [dict(nombre=n, geom=g, ang=ang, espejo=esp, dx=dx, dy=dy) for n, g in fijas] + hs[0]
    verificar(hs, hoja, margen, separacion)
    return hs


def rellenar(hojas, generador, hoja=(1220, 2440), margen=12, separacion=12, res=4.0,
             giros=range(0, 360, 15), maximo=200):
    """Llena el sobrante de hojas ya acomodadas con copias de un juego de piezas.
    generador(k) -> lista de (nombre, geom) que forman UN juego (se coloca completo o nada)."""
    W, H = int(hoja[0] / res), int(hoja[1] / res)
    agregados = 0
    for ps in hojas:
        o = np.zeros((H, W), np.float32)
        m = int(math.ceil(margen / res))
        o[:m, :] = o[-m:, :] = o[:, :m] = o[:, -m:] = 1
        for p in ps:
            o += _raster(p["geom"].buffer(separacion / 2 + res * 0.75, join_style=1), res, 0, 0, W, H)
        while agregados < maximo:
            juego = generador(agregados)
            o_try, puestos = o.copy(), []
            for nombre, g in juego:
                mejor = None
                for ang in giros:
                    go = orientar(g, ang, False)
                    gd = go.buffer(separacion / 2 + res * 0.75, join_style=1)
                    mnx, mny, mxx, mxy = gd.bounds
                    w, h = int(math.ceil((mxx - mnx) / res)) + 1, int(math.ceil((mxy - mny) / res)) + 1
                    msk = _raster(gd, res, mnx, mny, w, h)
                    corr = fftconvolve(o_try, msk[::-1, ::-1], mode="valid")
                    lib = np.argwhere(corr < 0.5)
                    if not len(lib):
                        continue
                    sc = lib[:, 0] * 10000 + lib[:, 1]
                    j = int(np.argmin(sc))
                    if mejor is None or sc[j] < mejor[0]:
                        mejor = (sc[j], lib[j], ang, go, msk, mnx, mny)
                if mejor is None:
                    puestos = None; break
                _, (r, c), ang, go, msk, mnx, mny = mejor
                o_try[r:r + msk.shape[0], c:c + msk.shape[1]] += msk
                dx, dy = c * res - mnx, r * res - mny
                puestos.append(dict(nombre=nombre, geom=affinity.translate(go, dx, dy), ang=ang,
                                    espejo=False, dx=dx, dy=dy))
            if not puestos:
                break
            o = o_try; ps.extend(puestos); agregados += 1
    verificar(hojas, hoja, margen, separacion)
    return agregados
