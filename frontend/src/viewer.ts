import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergedChunk, triangleOwner, type GeometryPart } from './chunkGeometry';
import { addSignText, disposeChunk } from './signText';
import { Transparency, type TextPart } from './transparency';
import type { Atlas, Face, Model, Packet, Point, RenderCell, Selection } from './types';

type Hit = { position: Point; normal: Point; group: string; protected: boolean; ground: boolean };
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
  layer = Infinity;
  fitted = false;
  frames = 0;
  renderMs = 0;
  rebuilt = 0;
  onHit: (hit: Hit | null, event: PointerEvent) => void = () => {};
  private drawHandle = 0;
  private geometryCache = new Map<string, THREE.BufferGeometry>();
  private occupancy = new Map<string, RenderCell>();
  private transparentParts = new Map<string, GeometryPart[]>();
  private transparency: Transparency | null = null;
  private sortedMaterial!: THREE.MeshLambertMaterial;
  private resourceHash = '';
  private thumbnailRenderer: THREE.WebGLRenderer | null = null;
  private thumbnails = new Map<string, string>();
  pendingBuilds = new Set<string>();
  building = false;
  private buildPromise: Promise<void> = Promise.resolve();
  private textureReady: Promise<void> = Promise.resolve();
  private chunkGenerations = new Map<string, number>();
  private builtKeys = new Map<string, string>();
  private transparencyDirty = false;
  private resizeObserver: ResizeObserver;

  constructor(readonly container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true,
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    const theme = getComputedStyle(document.documentElement);
    this.renderer.setClearColor(theme.getPropertyValue('--stage-background').trim() || '#eef2f2');
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.append(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = false;
    this.controls.addEventListener('change', () => this.requestDraw());
    this.scene.add(new THREE.AmbientLight(0xffffff, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 2.1);
    sun.position.set(-35, 60, 25);
    this.scene.add(sun);
    const grid = new THREE.GridHelper(
      128,
      128,
      new THREE.Color(theme.getPropertyValue('--grid-major').trim() || '#b1beb9'),
      new THREE.Color(theme.getPropertyValue('--grid-minor').trim() || '#d6dfda'),
    );
    grid.position.y = -0.01;
    this.scene.add(grid, this.ghosts);
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
    this.texture = await this.loadTexture('/api/atlas.png');
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
    this.sortedMaterial = this.translucent.clone();
    this.sortedMaterial.forceSinglePass = true;
    this.emissive = new THREE.MeshBasicMaterial({
      map: this.texture,
      side: THREE.DoubleSide,
      vertexColors: true,
    });
  }

  private async loadTexture(url: string): Promise<THREE.Texture> {
    const texture = await new THREE.TextureLoader().loadAsync(url);
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    texture.generateMipmaps = false;
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  private async refreshTexture(hash: string) {
    const texture = await this.loadTexture(
      '/api/atlas.png?resource_hash=' + encodeURIComponent(hash),
    );
    // A newer resource packet can arrive before the image finishes loading.
    if (hash !== this.resourceHash) {
      texture.dispose();
      return;
    }
    const previous = this.texture;
    this.texture = texture;
    for (const material of [this.material, this.translucent, this.sortedMaterial, this.emissive]) {
      material.map = texture;
      material.needsUpdate = true;
    }
    previous.dispose();
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
      this.drawNow();
      this.renderMs = performance.now() - start;
      this.frames++;
    });
  }
  drawNow() {
    this.camera.updateMatrixWorld();
    this.transparency?.sort(this.camera);
    this.renderer.render(this.scene, this.camera);
  }

  update(packet: Packet) {
    if (packet.resource_hash && this.resourceHash !== packet.resource_hash) {
      this.clearScene();
      this.resourceHash = packet.resource_hash;
      this.thumbnails.clear();
      this.clearGhosts();
      this.textureReady = this.refreshTexture(this.resourceHash);
    }
    const changed = new Set<string>([...Object.keys(packet.chunks), ...packet.removed_chunks]);
    for (const [id, model] of Object.entries(packet.models)) this.models.set(id, model);
    this.atlas = packet.atlas;
    for (const id of changed) {
      this.chunkGenerations.set(id, (this.chunkGenerations.get(id) ?? 0) + 1);
      for (const cell of this.chunks.get(id) ?? [])
        this.occupancy.delete(key([cell[0], cell[1], cell[2]]));
      const cells = packet.chunks[id];
      if (cells) {
        this.chunks.set(id, cells);
        for (const cell of cells) this.occupancy.set(key([cell[0], cell[1], cell[2]]), cell);
      } else this.chunks.delete(id);
    }
    this.versions = packet.chunk_versions;
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
    this.scheduleBuild(changed);
    if (!this.fitted && packet.summary.occupied_bounds) {
      this.fit(packet.summary.occupied_bounds);
      this.fitted = true;
    }
    this.requestDraw();
  }

  occupied() {
    return this.occupancy;
  }

  clearScene() {
    this.pendingBuilds.clear();
    this.chunkGenerations.clear();
    this.builtKeys.clear();
    for (const group of this.meshes.values()) {
      this.scene.remove(group);
      disposeChunk(group);
    }
    this.meshes.clear();
    this.chunks.clear();
    this.occupancy.clear();
    this.transparentParts.clear();
    if (this.transparency) {
      this.scene.remove(this.transparency.mesh);
      this.transparency.dispose();
      this.transparency = null;
    }
    this.versions = {};
    for (const geometry of this.geometryCache.values()) geometry.dispose();
    this.geometryCache.clear();
    this.models.clear();
  }

  whenReady(): Promise<void> {
    return this.buildPromise;
  }

  private scheduleBuild(ids: Iterable<string>) {
    for (const id of ids) this.pendingBuilds.add(id);
    if (!this.pendingBuilds.size || this.building) return;
    this.building = true;
    this.buildPromise = this.runBuilds().finally(() => {
      this.building = false;
    });
  }

  private async runBuilds() {
    this.rebuilt = 0;
    // Yield before expensive geometry work. Rapid slider inputs then replace one
    // queued job, instead of rebuilding five complete scenes in the same task.
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    while (this.pendingBuilds.size) {
      const textureReady = this.textureReady;
      await textureReady;
      if (textureReady !== this.textureReady) continue;
      const start = performance.now();
      while (this.pendingBuilds.size && performance.now() - start < 6) {
        const id = this.pendingBuilds.values().next().value!;
        this.pendingBuilds.delete(id);
        this.rebuild(id, this.occupancy);
        this.rebuilt++;
      }
      this.requestDraw();
      if (this.pendingBuilds.size)
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
    if (this.transparencyDirty) this.flushTransparency();
    this.requestDraw();
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
    if (this.geometryCache.size > 4096) {
      const oldest = this.geometryCache.keys().next().value!;
      this.geometryCache.get(oldest)!.dispose();
      this.geometryCache.delete(oldest);
    }
    return geometry;
  }

  rebuild(id: string, occupied: Map<string, RenderCell>) {
    const chunk = id.split(',').map(Number);
    const bottom = chunk[1] * 16;
    const generations = [
      id,
      ...[
        [1, 0, 0],
        [-1, 0, 0],
        [0, 1, 0],
        [0, -1, 0],
        [0, 0, 1],
        [0, 0, -1],
      ].map((d) => key(chunk.map((v, i) => v + d[i]))),
    ].map((k) => this.chunkGenerations.get(k) ?? 0);
    const buildKey =
      generations.join(':') + ':' + Math.max(bottom - 1, Math.min(bottom + 16, this.layer));
    if (this.builtKeys.get(id) === buildKey) return;
    this.builtKeys.set(id, buildKey);
    const previousParts = this.transparentParts.get(id) ?? [];
    const old = this.meshes.get(id);
    const hadTexts = old?.children.some((object) => object.userData.signText) ?? false;
    if (old) {
      this.scene.remove(old);
      disposeChunk(old);
    }
    this.meshes.delete(id);
    this.transparentParts.delete(id);
    const cells = this.chunks.get(id);
    if (!cells) {
      this.transparencyDirty ||= previousParts.length > 0 || hadTexts;
      return;
    }
    const group = new THREE.Group();
    group.name = id;
    const opaque = new Map<THREE.Material, GeometryPart[]>();
    const transparent: GeometryPart[] = [];
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
          if (!neighbour || neighbour[1] > this.layer) return '1';
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
    for (const batch of batches.values()) {
      const geometry = this.geometry(batch.id, batch.model.faces, batch.mask);
      if (!geometry.attributes.position.count) continue;
      if (batch.model.render_layer === 'cutout' && batch.model.name.endsWith('_leaves')) {
        // Preserve leaf instance transforms and object sorting: neighbouring
        // double-sided alpha-tested faces can compete at the same depth.
        // The chunk owns its GPU geometry even if the source cache is evicted.
        const mesh = new THREE.InstancedMesh(
          geometry.clone(),
          this.materialFor(batch.model),
          batch.cells.length,
        );
        const matrix = new THREE.Matrix4();
        batch.cells.forEach((cell, index) => {
          matrix.makeTranslation(cell[0], cell[1], cell[2]);
          mesh.setMatrixAt(index, matrix);
        });
        mesh.userData.cells = batch.cells;
        mesh.userData.chunkGeometry = true;
        mesh.computeBoundingSphere();
        group.add(mesh);
        if (batch.model.texts) {
          for (const cell of batch.cells) addSignText(group, batch.model, cell);
        }
        continue;
      }
      if (batch.model.render_layer !== 'translucent') {
        const material = this.materialFor(batch.model);
        let parts = opaque.get(material);
        if (!parts) opaque.set(material, (parts = []));
        for (const cell of batch.cells) parts.push({ geometry, cell });
        if (batch.model.texts) {
          for (const cell of batch.cells) addSignText(group, batch.model, cell);
        }
        continue;
      }
      for (const cell of batch.cells) transparent.push({ geometry, cell });
      if (batch.model.texts) {
        for (const cell of batch.cells) addSignText(group, batch.model, cell);
      }
    }
    const sameTransparency =
      previousParts.length === transparent.length &&
      previousParts.every(
        (part, index) =>
          part.geometry === transparent[index].geometry &&
          part.cell.every((value, field) => value === transparent[index].cell[field]),
      );
    // Text textures belong to rebuilt chunks: always replace their merged copy.
    this.transparencyDirty ||=
      !sameTransparency || hadTexts || group.children.some((object) => object.userData.signText);
    if (transparent.length) this.transparentParts.set(id, transparent);
    for (const [material, parts] of opaque) {
      group.add(mergedChunk(parts, material));
    }
    group.traverse((object) => {
      object.updateMatrix();
      object.matrixAutoUpdate = false;
    });
    this.meshes.set(id, group);
    this.scene.add(group);
  }

  private flushTransparency() {
    this.transparencyDirty = false;
    if (this.transparency) {
      this.scene.remove(this.transparency.mesh);
      this.transparency.dispose();
      this.transparency = null;
    }
    const parts = [...this.transparentParts.values()].flat();
    const texts: TextPart[] = [];
    for (const group of this.meshes.values()) {
      for (const object of group.children) {
        if (!(object instanceof THREE.Mesh) || !object.userData.signText) continue;
        object.visible = false;
        const cell = this.occupancy.get(key(object.position.toArray()));
        if (!cell) continue;
        const geometry = object.geometry.toNonIndexed();
        geometry.computeVertexNormals();
        const count = geometry.attributes.position.count;
        geometry.setAttribute(
          'color',
          new THREE.BufferAttribute(new Float32Array(count * 3).fill(1), 3),
        );
        const material = (object.material as THREE.MeshBasicMaterial).clone();
        material.forceSinglePass = true;
        texts.push({ geometry, cell, material });
      }
    }
    if (parts.length || texts.length) {
      this.transparency = new Transparency(parts, this.sortedMaterial, texts);
      this.scene.add(this.transparency.mesh);
    }
    for (const text of texts) text.geometry.dispose();
  }

  setLayer(layer: number) {
    if (this.layer === layer) return;
    const previous = this.layer;
    this.layer = layer;
    const low = Math.min(previous, layer),
      high = Math.max(previous, layer);
    const changed = new Set<string>();
    for (const id of this.chunks.keys()) {
      const bottom = Number(id.split(',')[1]) * 16;
      if (bottom <= high && bottom + 15 >= low) {
        changed.add(id);
      }
    }
    this.scheduleBuild(changed);
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
        object.dispose();
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
    if (this.building) return null;
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.ray.setFromCamera(
      new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      ),
      this.camera,
    );
    const objects = [...this.meshes.values()]
      .filter((group) => group.visible)
      .flatMap((group) => group.children);
    if (this.transparency) objects.push(this.transparency.mesh);
    const intersections = this.ray.intersectObjects(objects, false);
    const hit = intersections[0];
    const cell =
      hit &&
      (hit.instanceId !== undefined
        ? (hit.object.userData.cells[hit.instanceId] as RenderCell)
        : triangleOwner(hit.object, hit.faceIndex ?? -1));
    if (hit && cell) {
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
    const cacheKey = this.resourceHash + ':' + size + ':' + JSON.stringify(model);
    const cached = this.thumbnails.get(cacheKey);
    if (cached) return cached;
    if (!this.thumbnailRenderer) {
      this.thumbnailRenderer = new THREE.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: true,
      });
      this.thumbnailRenderer.setPixelRatio(1);
      this.thumbnailRenderer.setClearColor('#eef2f2');
      this.thumbnailRenderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    const renderer = this.thumbnailRenderer;
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
    renderer.setSize(size, size, false);
    renderer.render(temporary, camera);
    const image = renderer.domElement.toDataURL('image/png');
    this.models.delete(id);
    this.geometryCache.delete(id + ':' + '1'.repeat(model.faces.length));
    geometry.dispose();
    this.thumbnails.set(cacheKey, image);
    if (this.thumbnails.size > 256) this.thumbnails.delete(this.thumbnails.keys().next().value!);
    return image;
  }
}
