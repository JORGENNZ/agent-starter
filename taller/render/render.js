// Render 3D realista (WebGL en Chromium headless) de una escena JSON generada por Python.
// Uso: node render.js escena.json salida.png
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [escenaPath, salida] = process.argv.slice(2);
  const escena = JSON.parse(fs.readFileSync(escenaPath, 'utf8'));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const W = escena.ancho || 1600, H = escena.alto || 1200;
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.setContent(`<html><body style="margin:0;background:#fff"><canvas id=c width=${W} height=${H}></canvas></body></html>`);
  await page.addScriptTag({ path: path.join(__dirname, 'node_modules/three/build/three.min.js') });
  await page.evaluate((e) => {
    const T = THREE;
    const canvas = document.getElementById('c');
    const r = new T.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    r.setSize(e.ancho, e.alto, false);
    r.shadowMap.enabled = true; r.shadowMap.type = T.PCFSoftShadowMap;
    r.outputColorSpace = T.SRGBColorSpace;
    r.toneMapping = T.ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
    const s = new T.Scene(); s.background = new T.Color(e.fondo || '#f4f2ee');
    const box = new T.Box3();
    for (const m of e.mallas) {
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(m.v, 3));
      g.setIndex(m.f);
      const gf = g.toNonIndexed(); gf.computeVertexNormals();  // normales por cara: aristas nítidas
      const mat = new T.MeshStandardMaterial({ color: m.color, roughness: m.rugosidad ?? 0.75,
        metalness: m.metal ?? 0, transparent: (m.opacidad ?? 1) < 1, opacity: m.opacidad ?? 1 });
      if (m.emisivo) { mat.emissive = new T.Color(m.emisivo); mat.emissiveIntensity = m.intensidad ?? 2.0; }
      const mesh = new T.Mesh(gf, mat); mesh.castShadow = m.sombra !== false; mesh.receiveShadow = true; s.add(mesh);
      if (m.aristas !== false) {
        const ed = new T.LineSegments(new T.EdgesGeometry(g, 25),
          new T.LineBasicMaterial({ color: new T.Color(m.color).multiplyScalar(0.45) }));
        s.add(ed);
      }
      if (m.encuadre !== false) box.expandByObject(mesh);
    }
    for (const L of (e.luces || [])) {
      if (L.tipo === 'foco') {   // foco hacia abajo (como una tira LED bajo la repisa)
        const sp = new T.SpotLight(L.color || '#ffd9a0', L.intensidad ?? 1.0, L.distancia ?? 0,
                                   (L.angulo ?? 70) * Math.PI / 180, L.penumbra ?? 0.8, L.decaimiento ?? 0);
        sp.position.set(...L.pos);
        sp.target.position.set(L.pos[0], L.pos[1], L.pos[2] - 100);
        s.add(sp, sp.target);
      } else {
        const pl = new T.PointLight(L.color || '#ffd9a0', L.intensidad ?? 1.0, L.distancia ?? 0, L.decaimiento ?? 0);
        pl.position.set(...L.pos); s.add(pl);
      }
    }
    const c = box.getCenter(new T.Vector3()), sz = box.getSize(new T.Vector3());
    const rad = sz.length() / 2;
    // piso con sombra
    const piso = new T.Mesh(new T.PlaneGeometry(rad * 12, rad * 12), new T.ShadowMaterial({ opacity: 0.18 }));
    piso.position.set(c.x, c.y, box.min.z - 0.05); piso.receiveShadow = true; s.add(piso);
    s.add(new T.HemisphereLight('#ffffff', '#b9b2a6', e.ambiente ?? 1.1));
    const sol = new T.DirectionalLight(e.sol_color || '#ffffff', e.sol ?? 2.2);
    const azs = ((e.azim ?? -55) + 65) * Math.PI / 180;  // luz a un lado de la cámara
    sol.position.set(c.x + rad * 3 * Math.cos(azs), c.y + rad * 3 * Math.sin(azs), c.z + rad * 4.5); sol.target.position.copy(c);
    sol.castShadow = true; sol.shadow.mapSize.set(4096, 4096);
    const sc = sol.shadow.camera; sc.left = sc.bottom = -rad * 2.5; sc.right = sc.top = rad * 2.5;
    sc.near = 0.1; sc.far = rad * 12; sol.shadow.bias = -0.0004; sol.shadow.normalBias = rad * 0.004;
    s.add(sol, sol.target);
    const azr = ((e.azim ?? -55) - 70) * Math.PI / 180;  // luz de relleno del otro lado
    const rel = new T.DirectionalLight('#ffffff', e.relleno ?? 0.9); rel.position.set(c.x + rad * 3 * Math.cos(azr), c.y + rad * 3 * Math.sin(azr), c.z + rad * 1.5); s.add(rel);
    const cam = new T.PerspectiveCamera(30, e.ancho / e.alto, rad / 100, rad * 50); cam.up.set(0, 0, 1);
    const az = (e.azim ?? -55) * Math.PI / 180, el = (e.elev ?? 28) * Math.PI / 180;
    const dist = rad / Math.sin((30 * Math.PI / 180) / 2) * (e.zoom ?? 1.0) * 0.92;
    cam.position.set(c.x + dist * Math.cos(el) * Math.cos(az), c.y + dist * Math.cos(el) * Math.sin(az), c.z + dist * Math.sin(el));
    cam.lookAt(c);
    if (e.objetivo) cam.lookAt(new T.Vector3(...e.objetivo));
    r.render(s, cam);
  }, { ...escena, ancho: W, alto: H });
  await page.locator('#c').screenshot({ path: salida });
  await browser.close();
})();
