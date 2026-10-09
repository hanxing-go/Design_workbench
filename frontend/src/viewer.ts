import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { addSignText, disposeChunk } from './signText';
import { updatePaintings, paintingAt, slicePaintings } from './paintings';
import type { Atlas, Face, Model, Packet, Point, RenderCell, Selection } from './types';

type Hit = {
  position: Point;
  normal: Point;
  group: string;
  protected: boolean;
  ground: boolean;
  height?: number;
  painting?: string;
};
const key = (p: readonly number[]) => p.join(',');

export class Viewer {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(40, 1, 0.1, 4000);
  controls: OrbitControls;
  ray = new THREE.Raycaster();
  chunks = new Map<string, RenderCell[]>();
  models = new Map<string, Model>();
  meshes = new Map<string, THREE.Group>();
  versions: Record<string, string> = {};
  atlas!: Atlas;
  texture!: THREE.Texture;
  material!: THREE.MeshLambertMaterial;
  translucent!: THREE.MeshLambertMaterial;
  emissive!: THREE.MeshBasicMaterial;
  selection: THREE.Box3Helper | null = null;
  ghosts = new THREE.Group();
  paintings = new THREE.Group();
  layer = Infinity;
  fitted = false;
  frames = 0;
  renderMs = 0;
  rebuilt = 0;
  onHit: (hit: Hit | null, event: PointerEvent) => void = () => {};
  private drawHandle = 0;
  private geometryCache = new Map<string, THREE.BufferGeometry>();
  private resizeObserver: ResizeObserver;

  constructor(readonly container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true,
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor('#eef2f2');
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.append(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = false;
    this.controls.addEventListener('change', () => this.requestDraw());
    this.scene.add(new THREE.AmbientLight(0xffffff, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 2.1);
    sun.position.set(-35, 60, 25);
    this.scene.add(sun);
    const grid = new THREE.GridHelper(128, 128, 0xb1beb9, 0xd6dfda);
    grid.position.y = -0.01;
    this.scene.add(grid, this.ghosts, this.paintings);
    this.camera.position.set(20, 17, 24);
    this.controls.target.set(0, 3, 0);
    this.controls.update();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    let down: { x: number; y: number } | null = null;
    this.renderer.domElement.addEventListener('pointerdown', (e) => {
      if (e.button === 0) down = { x: e.clientX, y: e.clientY };
    });
    this.renderer.domElement.addEventListener('pointerup', (e) => {
      if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 5) {
        this.onHit(this.pick(e), e);
      }
      down = null;
    });
    this.resize();
  }

  async initializeTexture() {
    this.texture = await new THREE.TextureLoader().loadAsync('/api/atlas.png');
    this.texture.magFilter = THREE.NearestFilter;
    this.texture.minFilter = THREE.NearestFilter;
    this.texture.generateMipmaps = false;
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.material = new THREE.MeshLambertMaterial({
      map: this.texture,
      alphaTest: 0.1,
      side: THREE.DoubleSide,
      vertexColors: true,
    });
    this.translucent = new THREE.MeshLambertMaterial({
      map: this.texture,
      side: THREE.DoubleSide,
      vertexColors: true,
      transparent: true,
      alphaTest: 0.01,
      depthWrite: false,
    });
    this.emissive = new THREE.MeshBasicMaterial({
      map: this.texture,
      side: THREE.DoubleSide,
      vertexColors: true,
    });
  }

  materialFor(model: Model): THREE.Material {
    return model.render_layer === 'translucent'
      ? this.translucent
      : model.render_layer === 'emissive'
        ? this.emissive
        : this.material;
  }

  resize() {
    const w = Math.max(1, this.container.clientWidth),
      h = Math.max(1, this.container.clientHeight);
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.requestDraw();
  }
  requestDraw() {
    if (this.drawHandle) return;
    this.drawHandle = requestAnimationFrame(() => {
      this.drawHandle = 0;
      const start = performance.now();
      this.renderer.render(this.scene, this.camera);
      this.renderMs = performance.now() - start;
      this.frames++;
    });
  }
  drawNow() {
    this.renderer.render(this.scene, this.camera);
  }

  update(packet: Packet) {
    const changed = new Set<string>([...Object.keys(packet.chunks), ...packet.removed_chunks]);
    for (const [id, model] of Object.entries(packet.models)) this.models.set(id, model);
    this.atlas = packet.atlas;
    for (const [id, cells] of Object.entries(packet.chunks)) this.chunks.set(id, cells);
    for (const id of packet.removed_chunks) this.chunks.delete(id);
    this.versions = packet.chunk_versions;
    updatePaintings(this.paintings, packet.paintings ?? [], this.atlas, this.material);
    slicePaintings(this.paintings, this.layer);
    for (const id of [...changed]) {
      const p = id.split(',').map(Number);
      for (const d of [
        [1, 0, 0],
        [-1, 0, 0],
        [0, 1, 0],
        [0, -1, 0],
        [0, 0, 1],
        [0, 0, -1],
      ])
        changed.add(key(p.map((v, i) => v + d[i])));
    }
    const occupied = this.occupied();
    this.rebuilt = 0;
    for (const id of changed) {
      this.rebuild(id, occupied);
      this.rebuilt++;
    }
    if (!this.fitted && packet.summary.occupied_bounds) {
      this.fit(packet.summary.occupied_bounds);
      this.fitted = true;
    }
    this.requestDraw();
  }

  occupied() {
    const result = new Map<string, RenderCell>();
    for (const cells of this.chunks.values())
      for (const cell of cells)
        if (cell[1] <= this.layer) result.set(key([cell[0], cell[1], cell[2]]), cell);
    return result;
  }

  geometry(id: string, faces: Face[], mask: string): THREE.BufferGeometry {
    const cacheKey = id + ':' + mask;
    const cached = this.geometryCache.get(cacheKey);
    if (cached) return cached;
    const positions: number[] = [],
      uvs: number[] = [],
      colors: number[] = [];
    const model = this.models.get(id)!;
    for (const [index, face] of faces.entries()) {
      if (mask[index] === '0') continue;
      const rect = this.atlas.uv[face.texture];
      if (!rect) continue;
      const tint = face.color
        ? new THREE.Color(face.color)
        : face.tint && !model.name.includes('cherry')
          ? new THREE.Color('#91ae63')
          : new THREE.Color('#ffffff');
      for (const vertex of [0, 1, 2, 0, 2, 3]) {
        positions.push(...face.vertices.slice(vertex * 3, vertex * 3 + 3));
        uvs.push(
          (rect[0] + face.uv[vertex * 2] * rect[2]) / this.atlas.width,
          1 - (rect[1] + face.uv[vertex * 2 + 1] * rect[3]) / this.atlas.height,
        );
        colors.push(tint.r, tint.g, tint.b);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.computeVertexNormals();
    this.geometryCache.set(cacheKey, geometry);
    return geometry;
  }

  rebuild(id: string, occupied: Map<string, RenderCell>) {
    const old = this.meshes.get(id);
    if (old) {
      this.scene.remove(old);
      disposeChunk(old);
    }
    this.meshes.delete(id);
    const cells = this.chunks.get(id);
    if (!cells) return;
    const group = new THREE.Group();
    group.name = id;
    const batches = new Map<
      string,
      { model: Model; id: string; mask: string; cells: RenderCell[] }
    >();
    for (const cell of cells) {
      if (cell[1] > this.layer) continue;
      const model = this.models.get(cell[3]);
      if (!model || model.status !== 'static') continue;
      const mask = model.faces
        .map((face) => {
          if (!face.cull) return '1';
          const neighbour = occupied.get(
            key([cell[0] + face.cull[0], cell[1] + face.cull[1], cell[2] + face.cull[2]]),
          );
          if (!neighbour) return '1';
          const adjacent = this.models.get(neighbour[3]);
          return adjacent?.opaque_cube ||
            ((model.name.includes('glass') ||
              model.name === 'minecraft:water' ||
              model.name === 'minecraft:lava') &&
              adjacent?.name === model.name)
            ? '0'
            : '1';
        })
        .join('');
      if (!mask.includes('1')) continue;
      const batchKey =
        (model.render_layer === 'translucent' ? key([cell[0], cell[1], cell[2]]) : cell[3]) +
        ':' +
        mask;
      if (!batches.has(batchKey)) batches.set(batchKey, { model, id: cell[3], mask, cells: [] });
      batches.get(batchKey)!.cells.push(cell);
    }
    const matrix = new THREE.Matrix4();
    for (const batch of batches.values()) {
      const geometry = this.geometry(batch.id, batch.model.faces, batch.mask);
      if (!geometry.attributes.position.count) continue;
      const mesh = new THREE.InstancedMesh(
        geometry,
        this.materialFor(batch.model),
        batch.cells.length,
      );
      batch.cells.forEach((cell, index) => {
        if (batch.model.render_layer === 'translucent') {
          mesh.position.set(cell[0], cell[1], cell[2]);
          matrix.identity();
        } else matrix.makeTranslation(cell[0], cell[1], cell[2]);
        mesh.setMatrixAt(index, matrix);
      });
      mesh.userData.cells = batch.cells;
      mesh.computeBoundingSphere();
      group.add(mesh);
      if (batch.model.texts) {
        for (const cell of batch.cells) addSignText(group, batch.model, cell);
      }
    }
    this.meshes.set(id, group);
    this.scene.add(group);
  }

  setLayer(layer: number) {
    this.layer = layer;
    slicePaintings(this.paintings, layer);
    const occupied = this.occupied();
    for (const id of this.chunks.keys()) this.rebuild(id, occupied);
    this.requestDraw();
  }
  fit(bounds: { low: Point; high: Point }) {
    const low = new THREE.Vector3(...bounds.low),
      high = new THREE.Vector3(...bounds.high).addScalar(1);
    const center = low.clone().add(high).multiplyScalar(0.5);
    const extent = high.clone().sub(low).length();
    this.controls.target.copy(center);
    this.camera.position
      .copy(center)
      .add(
        new THREE.Vector3(1.2, 0.9, 1.4).normalize().multiplyScalar(Math.max(12, extent * 1.25)),
      );
    this.camera.far = Math.max(4000, extent * 10);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.requestDraw();
  }
  view(direction: 'front' | 'side' | 'top' | 'iso') {
    const target = this.controls.target.clone(),
      distance = this.camera.position.distanceTo(target);
    const vector =
      direction === 'front'
        ? new THREE.Vector3(0, 0.1, 1)
        : direction === 'side'
          ? new THREE.Vector3(1, 0.1, 0)
          : direction === 'top'
            ? new THREE.Vector3(0, 1, 0.001)
            : new THREE.Vector3(1.2, 0.9, 1.4);
    this.camera.position.copy(target).add(vector.normalize().multiplyScalar(distance));
    this.controls.update();
    this.requestDraw();
  }
  showSelection(selection: Selection | null) {
    if (this.selection) {
      this.scene.remove(this.selection);
      this.selection.geometry.dispose();
      (this.selection.material as THREE.Material).dispose();
      this.selection = null;
    }
    if (selection) {
      const box = new THREE.Box3(
        new THREE.Vector3(...selection.low),
        new THREE.Vector3(...selection.high).addScalar(1),
      );
      this.selection = new THREE.Box3Helper(box, 0x138d75);
      this.scene.add(this.selection);
    }
    this.requestDraw();
  }
  clearGhosts() {
    for (const object of [...this.ghosts.children]) {
      this.ghosts.remove(object);
      if (object instanceof THREE.InstancedMesh) {
        object.geometry.dispose();
        (object.material as THREE.Material).dispose();
      }
    }
    this.requestDraw();
  }
  showGhosts(changes: { position: Point; after: unknown }[]) {
    this.clearGhosts();
    const groups = [changes.filter((c) => c.after), changes.filter((c) => !c.after)];
    groups.forEach((entries, i) => {
      if (!entries.length) return;
      const mesh = new THREE.InstancedMesh(
        new THREE.BoxGeometry(1.025, 1.025, 1.025),
        new THREE.MeshBasicMaterial({
          color: i ? 0xdf745a : 0x20b396,
          transparent: true,
          opacity: 0.35,
          depthWrite: false,
        }),
        entries.length,
      );
      entries.forEach((entry, index) =>
        mesh.setMatrixAt(
          index,
          new THREE.Matrix4().makeTranslation(
            entry.position[0] + 0.5,
            entry.position[1] + 0.5,
            entry.position[2] + 0.5,
          ),
        ),
      );
      this.ghosts.add(mesh);
    });
    this.requestDraw();
  }

  pick(event: PointerEvent): Hit | null {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.ray.setFromCamera(
      new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      ),
      this.camera,
    );
    const objects = [...this.meshes.values()]
      .flatMap((group) => group.children)
      .concat(this.paintings.children.filter((m) => m.visible));
    const intersections = this.ray.intersectObjects(objects, false);
    const hit = intersections[0];
    const painting = hit && paintingAt(hit.object);
    if (painting) {
      const vectors: Record<string, Point> = {
        north: [0, 0, -1],
        south: [0, 0, 1],
        east: [1, 0, 0],
        west: [-1, 0, 0],
      };
      return {
        position: painting.anchor,
        normal: vectors[painting.facing],
        group: '画',
        protected: painting.protected,
        ground: false,
        painting: painting.id,
      };
    }
    if (hit && hit.instanceId !== undefined) {
      const cell: RenderCell = hit.object.userData.cells[hit.instanceId];
      const n = hit.face?.normal ?? new THREE.Vector3(0, 1, 0);
      const normal: Point = [0, 0, 0];
      const axis =
        Math.abs(n.x) > Math.abs(n.y) && Math.abs(n.x) > Math.abs(n.z)
          ? 0
          : Math.abs(n.y) > Math.abs(n.z)
            ? 1
            : 2;
      normal[axis] = Math.sign([n.x, n.y, n.z][axis]);
      return {
        position: [cell[0], cell[1], cell[2]],
        normal,
        group: cell[4],
        protected: cell[5],
        ground: false,
        height: Math.min(1, Math.max(0, hit.point.y - cell[1])),
      };
    }
    const point = this.ray.ray.intersectPlane(
      new THREE.Plane(new THREE.Vector3(0, 1, 0), 0),
      new THREE.Vector3(),
    );
    return point
      ? {
          position: [Math.floor(point.x), -1, Math.floor(point.z)],
          normal: [0, 1, 0],
          group: 'main',
          protected: false,
          ground: true,
        }
      : null;
  }

  thumbnail(model: Model, size = 72): string {
    const temporary = new THREE.Scene();
    temporary.add(new THREE.AmbientLight(0xffffff, 2.2));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(-2, 4, 3);
    temporary.add(light);
    const id = 'thumb:' + JSON.stringify(model);
    this.models.set(id, model);
    const geometry = this.geometry(id, model.faces, '1'.repeat(model.faces.length));
    temporary.add(new THREE.Mesh(geometry, this.materialFor(model)));
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 20);
    camera.position.set(2.4, 1.9, 2.6);
    camera.lookAt(0.5, 0.5, 0.5);
    const oldSize = this.renderer.getSize(new THREE.Vector2());
    this.renderer.setSize(size, size, false);
    this.renderer.render(temporary, camera);
    const image = this.renderer.domElement.toDataURL('image/png');
    this.renderer.setSize(oldSize.x, oldSize.y, false);
    this.models.delete(id);
    this.requestDraw();
    return image;
  }
}
