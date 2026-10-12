import * as THREE from 'three';
import type { Model, Packet, RenderCell } from './types';

// One lazy renderer serves every visible card. Cards never run animation loops.
const snapshots = new Map<string, string>();
let renderer: THREE.WebGLRenderer | null = null;
let queue = Promise.resolve();
const observers = new Set<IntersectionObserver>();

export function clearProjectPreviews() {
  observers.forEach((observer) => observer.disconnect());
  observers.clear();
}

export function observeProjectPreview(host: HTMLElement, id: string, revision: number) {
  const observer = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      observers.delete(observer);
      queue = queue.then(async () => {
        if (!host.isConnected) return;
        try {
          const key = `${id}:${revision}`;
          let source = snapshots.get(key);
          if (!source) {
            const response = await fetch(`/api/projects/${encodeURIComponent(id)}/render`, {
              method: 'POST',
              signal: AbortSignal.timeout(20000),
            });
            if (!response.ok) throw new Error('preview unavailable');
            const packet: Packet = await response.json();
            source = await snapshot(packet, id);
            snapshots.set(`${id}:${packet.revision}`, source);
            if (snapshots.size > 48) snapshots.delete(snapshots.keys().next().value!);
          }
          if (!host.isConnected) return;
          const image = new Image();
          image.alt = '';
          image.src = source;
          host.replaceChildren(image);
          host.classList.add('has-preview');
        } catch {
          if (host.isConnected) {
            host.textContent = '预览暂不可用 · 点击进入设计';
            host.classList.add('preview-unavailable');
          }
        }
      });
    },
    { rootMargin: '160px' },
  );
  observer.observe(host);
  observers.add(observer);
}

function geometry(model: Model, packet: Packet) {
  const positions: number[] = [],
    uvs: number[] = [],
    colors: number[] = [];
  for (const face of model.faces) {
    const rect = packet.atlas.uv[face.texture];
    if (!rect) continue;
    const tint = new THREE.Color(face.color ?? (face.tint ? '#91ae63' : '#ffffff'));
    for (const vertex of [0, 1, 2, 0, 2, 3]) {
      positions.push(...face.vertices.slice(vertex * 3, vertex * 3 + 3));
      uvs.push(
        (rect[0] + face.uv[vertex * 2] * rect[2]) / packet.atlas.width,
        1 - (rect[1] + face.uv[vertex * 2 + 1] * rect[3]) / packet.atlas.height,
      );
      colors.push(tint.r, tint.g, tint.b);
    }
  }
  const result = new THREE.BufferGeometry();
  result.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  result.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  result.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  result.computeVertexNormals();
  return result;
}

async function snapshot(packet: Packet, id: string) {
  const texture = await new THREE.TextureLoader().loadAsync(
    `/api/atlas.png?project=${encodeURIComponent(id)}`,
  );
  texture.magFilter = texture.minFilter = THREE.NearestFilter;
  texture.colorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const geometries: THREE.BufferGeometry[] = [];
  const materials: THREE.Material[] = [];
  const meshes: THREE.InstancedMesh[] = [];
  try {
    if (!renderer) {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      renderer.setPixelRatio(1);
      renderer.setSize(560, 300, false);
      renderer.setClearColor('#202820');
      renderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    scene.add(new THREE.AmbientLight(0xffffff, 2));
    const sun = new THREE.DirectionalLight(0xfff1d7, 2.5);
    sun.position.set(-3, 7, 5);
    scene.add(sun);
    const batches = new Map<string, RenderCell[]>();
    for (const cells of Object.values(packet.chunks))
      for (const cell of cells) {
        if (!batches.has(cell[3])) batches.set(cell[3], []);
        batches.get(cell[3])!.push(cell);
      }
    for (const [key, cells] of batches) {
      const model = packet.models[key];
      if (!model?.faces.length) continue;
      const buffer = geometry(model, packet);
      geometries.push(buffer);
      const material = new THREE.MeshLambertMaterial({
        map: texture,
        vertexColors: true,
        alphaTest: 0.1,
        side: THREE.DoubleSide,
        transparent: model.render_layer === 'translucent',
        depthWrite: model.render_layer !== 'translucent',
      });
      materials.push(material);
      const mesh = new THREE.InstancedMesh(buffer, material, cells.length);
      meshes.push(mesh);
      const matrix = new THREE.Matrix4();
      cells.forEach((cell, index) =>
        mesh.setMatrixAt(index, matrix.makeTranslation(cell[0], cell[1], cell[2])),
      );
      scene.add(mesh);
    }
    const bounds = packet.summary.occupied_bounds;
    if (!bounds) throw new Error('empty project');
    const box = new THREE.Box3(
      new THREE.Vector3(...bounds.low),
      new THREE.Vector3(...bounds.high).addScalar(1),
    );
    const center = box.getCenter(new THREE.Vector3());
    const radius = box.getSize(new THREE.Vector3()).length() / 2;
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, Math.max(100, radius * 12));
    camera.position
      .copy(center)
      .add(
        new THREE.Vector3(1, 0.8, 1.3)
          .normalize()
          .multiplyScalar((radius / Math.sin(THREE.MathUtils.degToRad(17.5))) * 1.06),
      );
    camera.lookAt(center);
    camera.updateMatrixWorld();
    let extentX = 0,
      extentY = 0;
    for (const x of [box.min.x, box.max.x])
      for (const y of [box.min.y, box.max.y])
        for (const z of [box.min.z, box.max.z]) {
          const projected = new THREE.Vector3(x, y, z).applyMatrix4(camera.matrixWorldInverse);
          extentX = Math.max(extentX, Math.abs(projected.x));
          extentY = Math.max(extentY, Math.abs(projected.y));
        }
    const halfHeight = Math.max(extentY, extentX / (560 / 300)) * 1.08;
    camera.left = -halfHeight * (560 / 300);
    camera.right = halfHeight * (560 / 300);
    camera.top = halfHeight;
    camera.bottom = -halfHeight;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    return renderer.domElement.toDataURL('image/png');
  } finally {
    meshes.forEach((mesh) => mesh.dispose());
    geometries.forEach((buffer) => buffer.dispose());
    materials.forEach((material) => material.dispose());
    texture.dispose();
  }
}

window.addEventListener('pagehide', () => {
  clearProjectPreviews();
  renderer?.dispose();
  renderer = null;
});
