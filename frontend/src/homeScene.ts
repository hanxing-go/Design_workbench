import * as THREE from 'three';

import {
  HOME_BUILDINGS,
  type Block,
  type BlockKind,
  type HomeBuilding,
  type HomeBuildingPart,
} from './homeBuildings';

type Batch = { mesh: THREE.InstancedMesh; blocks: Block[]; originY: number };
type BuildingModel = {
  building: HomeBuilding;
  group: THREE.Group;
  batches: Batch[];
  parts: { group: THREE.Group; spec: HomeBuildingPart }[];
  top: number;
};
export type HomeSceneState = {
  name: string;
  index: number;
  total: number;
  phase: 'build' | 'hold' | 'dismantle' | 'switch';
};

// Leave time to enjoy each finished building before its blocks float away.
const BUILD_SECONDS = 8;
const HOLD_SECONDS = 10;
const DISMANTLE_SECONDS = 5;
const CYCLE_SECONDS = BUILD_SECONDS + HOLD_SECONDS + DISMANTLE_SECONDS + 1;

// A local fallback keeps the scene available before vanilla resources are installed.
function pixelTexture(kind: BlockKind | 'grass-side' | 'log-top'): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 16;
  const ctx = canvas.getContext('2d')!;
  const colors: Record<string, string[]> = {
    grass: ['#708f3e', '#7e9e46', '#658338', '#8ca750', '#56732f'],
    'grass-side': ['#795839', '#86613e', '#6c4c31', '#92714c'],
    dirt: ['#795839', '#86613e', '#6c4c31', '#92714c'],
    stone: ['#73766a', '#686c62', '#828479', '#5c6358'],
    brick: ['#999d8a', '#a5a894', '#8b927f', '#b0b39f'],
    planks: ['#c1a376', '#c9ad80', '#b7986d', '#d1b98e'],
    log: ['#665035', '#765d3b', '#57442e', '#856b47'],
    beam: ['#665035', '#765d3b', '#57442e', '#856b47'],
    'log-top': ['#ad8c58', '#b69a65', '#957a4e', '#c1a673'],
    roof: ['#715a40', '#7d6547', '#665039', '#8a7050'],
    tile: ['#4a645e', '#56716a', '#3b554f', '#648078'],
    leaves: ['#4e7333', '#5b7e3a', '#41682c', '#628840', '#719248'],
    cherry: ['#d6a6ae', '#e7bdc2', '#bd899b', '#f1d3cc', '#c99aaa'],
    water: ['#3c8d95', '#509da2', '#2c7d87', '#64adb0'],
    window: ['#edc57b', '#e8bb6f', '#f1d795', '#daa961'],
    door: ['#795e3b', '#8e7046', '#6b5032', '#9b7f52'],
    'door-top': ['#795e3b', '#8e7046', '#6b5032', '#9b7f52'],
    path: ['#a48f65', '#b09b6e', '#97855e', '#b8a67b'],
    flower: ['#edbe73', '#f2d198', '#dda565'],
    stem: ['#71913e', '#829f4a', '#5f7f33'],
    lantern: ['#edbf70', '#f5d290', '#d8a455', '#ffdf9d'],
    canvas: ['#d9d1af', '#e5dec0', '#cfc6a3', '#ece5cc'],
    'red-wool': ['#ad715b', '#b67c65', '#9e624e', '#c48b70'],
    copper: ['#ad8052', '#bd9163', '#997044', '#cca676'],
    crystal: ['#9e88b9', '#b39acb', '#8770a4', '#c6add8'],
    'dark-stone': ['#485451', '#56605b', '#3e4947', '#626d65'],
    rope: ['#aa9c72', '#b8ac82', '#908663'],
    wheat: ['#c7ab57', '#dbc273', '#ad9643', '#e5ce81'],
  };
  const palette = colors[kind];
  let seed = [...kind].reduce((value, letter) => value + letter.charCodeAt(0), 7);
  for (let y = 0; y < 16; y++) {
    for (let x = 0; x < 16; x++) {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      ctx.fillStyle = palette[Math.floor((seed / 0x100000000) * palette.length)];
      ctx.fillRect(x, y, 1, 1);
    }
  }
  if (kind === 'grass-side') {
    for (let x = 0; x < 16; x++) {
      ctx.fillStyle = colors.grass[x % colors.grass.length];
      ctx.fillRect(x, 0, 1, 3 + ((x * 7) % 4));
    }
  }
  if (kind === 'planks' || kind === 'roof' || kind === 'tile') {
    ctx.fillStyle = kind === 'tile' ? '#2e4842' : kind === 'roof' ? '#4e3d2b' : '#9c8055';
    for (let y = 3; y < 16; y += 4) ctx.fillRect(0, y, 16, 1);
    ctx.fillRect(4, 0, 1, 3);
    ctx.fillRect(12, 4, 1, 3);
    ctx.fillRect(7, 8, 1, 3);
    ctx.fillRect(2, 12, 1, 3);
  }
  if (kind === 'log' || kind === 'beam') {
    ctx.fillStyle = '#423522';
    for (let offset = 1; offset < 16; offset += 4) {
      if (kind === 'beam') ctx.fillRect(offset % 3, offset, 14, 1);
      else ctx.fillRect(offset, offset % 3, 1, 14);
    }
  }
  if (kind === 'log-top') {
    ctx.strokeStyle = '#80633d';
    ctx.lineWidth = 1;
    ctx.strokeRect(2.5, 2.5, 11, 11);
    ctx.strokeRect(5.5, 5.5, 5, 5);
  }
  if (kind === 'stone' || kind === 'dark-stone') {
    ctx.strokeStyle = kind === 'dark-stone' ? '#2a3633' : '#50594b';
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, 8, 6);
    ctx.strokeRect(8.5, 2.5, 7, 8);
    ctx.strokeRect(1.5, 9.5, 10, 6);
  }
  if (kind === 'brick') {
    ctx.fillStyle = '#606c5c';
    for (let y = 3; y < 16; y += 4) {
      ctx.fillRect(0, y, 16, 1);
      for (let x = y % 8 === 3 ? 3 : 7; x < 16; x += 8) ctx.fillRect(x, y - 3, 1, 3);
    }
  }
  if (kind === 'lantern') {
    ctx.fillStyle = '#485148';
    ctx.fillRect(0, 0, 16, 3);
    ctx.fillRect(0, 13, 16, 3);
    ctx.fillRect(0, 0, 2, 16);
    ctx.fillRect(14, 0, 2, 16);
    ctx.fillStyle = '#fff0b8';
    ctx.fillRect(4, 4, 3, 7);
  }
  if (kind === 'canvas' || kind === 'red-wool') {
    ctx.fillStyle = kind === 'canvas' ? '#beb59655' : '#86523f55';
    for (let y = 0; y < 16; y += 4) ctx.fillRect(0, y, 16, 1);
    for (let x = 0; x < 16; x += 4) ctx.fillRect(x, 0, 1, 16);
  }
  if (kind === 'copper') {
    ctx.strokeStyle = '#745635';
    ctx.strokeRect(0.5, 0.5, 15, 15);
    ctx.fillStyle = '#d7b27f';
    for (const x of [2, 12]) {
      for (const y of [2, 12]) ctx.fillRect(x, y, 2, 2);
    }
  }
  if (kind === 'crystal') {
    ctx.fillStyle = '#dcc5ec';
    ctx.fillRect(2, 2, 2, 10);
    ctx.fillRect(4, 2, 6, 2);
    ctx.fillStyle = '#705c90';
    ctx.fillRect(12, 5, 2, 9);
    ctx.fillRect(6, 12, 6, 2);
  }
  if (kind === 'wheat') {
    ctx.fillStyle = '#927d35';
    for (let x = 2; x < 16; x += 4) ctx.fillRect(x, 2, 1, 14);
    ctx.fillStyle = '#f0d98a';
    for (let x = 1; x < 16; x += 4) ctx.fillRect(x, 2 + (x % 3), 3, 5);
  }
  if (kind === 'window') {
    ctx.fillStyle = '#9b7950';
    ctx.fillRect(0, 0, 16, 1);
    ctx.fillRect(0, 15, 16, 1);
    ctx.fillRect(0, 0, 1, 16);
    ctx.fillRect(15, 0, 1, 16);
    ctx.fillRect(7, 0, 2, 16);
    ctx.fillRect(0, 7, 16, 2);
    ctx.fillStyle = '#f8e8b3';
    ctx.fillRect(2, 2, 2, 4);
    ctx.fillRect(10, 10, 2, 3);
  }
  if (kind === 'door' || kind === 'door-top') {
    ctx.strokeStyle = '#4c3c28';
    ctx.strokeRect(2.5, 2.5, 11, 11);
    if (kind === 'door') {
      ctx.fillStyle = '#d8bc73';
      ctx.fillRect(12, 3, 2, 2);
    } else {
      ctx.fillStyle = '#dcb776';
      ctx.fillRect(4, 3, 3, 5);
      ctx.fillRect(9, 3, 3, 5);
    }
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.magFilter = texture.minFilter = THREE.NearestFilter;
  texture.colorSpace = THREE.SRGBColorSpace;
  const vanilla: Partial<Record<BlockKind | 'grass-side' | 'log-top', string>> = {
    grass: 'grass_block_top',
    'grass-side': 'grass_block_side',
    dirt: 'dirt',
    stone: 'stone',
    brick: 'stone_bricks',
    planks: 'oak_planks',
    log: 'oak_log',
    beam: 'oak_log',
    'log-top': 'oak_log_top',
    roof: 'spruce_planks',
    tile: 'dark_prismarine',
    leaves: 'oak_leaves',
    cherry: 'cherry_leaves',
    water: 'water_still',
    path: 'dirt_path_top',
    canvas: 'white_wool',
    'red-wool': 'red_wool',
    copper: 'copper_block',
    crystal: 'amethyst_block',
    'dark-stone': 'deepslate_tiles',
    wheat: 'hay_block_side',
  };
  if (vanilla[kind]) {
    const image = new Image();
    image.onload = () => {
      if (texture.userData.disposed) return;
      ctx.clearRect(0, 0, 16, 16);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(image, 0, 0, image.width, image.width, 0, 0, 16, 16);
      texture.needsUpdate = true;
    };
    image.src = `/api/ui/sprites/${vanilla[kind]}.png`;
  }
  return texture;
}

export class HomeScene {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera: THREE.OrthographicCamera;
  private world = new THREE.Group();
  private models: BuildingModel[] = [];
  private buildingIndex = 0;
  private buildingDirection = 1;
  private cycleTime = 0;
  private settled = false;
  private stateKey = '';
  private floaters: THREE.Mesh[] = [];
  private smoke: THREE.Mesh[] = [];
  private textures = new Map<string, THREE.Texture>();
  private materials = new Map<BlockKind, THREE.Material | THREE.Material[]>();
  private geometry = new THREE.BoxGeometry(0.995, 0.995, 0.995);
  private dummy = new THREE.Object3D();
  private frame = 0;
  private lastFrame = 0;
  private time = 0;
  private angle = 0;
  private drag: { x: number; angle: number } | null = null;
  private inView = true;
  private paused = false;
  private disposed = false;
  private motionQuery = matchMedia('(prefers-reduced-motion: reduce)');
  private resizeObserver: ResizeObserver;
  private intersectionObserver: IntersectionObserver;

  constructor(
    private container: HTMLElement,
    private onChange: (state: HomeSceneState) => void = () => {},
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.2;
    container.append(this.renderer.domElement);
    this.camera = new THREE.OrthographicCamera(-16, 16, 13, -13, 0.1, 160);
    this.camera.position.set(24, 19, 27);
    this.camera.lookAt(0, 2, 0);
    this.scene.add(new THREE.HemisphereLight(0xf5f0d8, 0x454e35, 2.3));
    const sunlight = new THREE.DirectionalLight(0xffebc7, 2.6);
    sunlight.position.set(-10, 20, 15);
    this.scene.add(sunlight, this.world);

    for (const building of HOME_BUILDINGS) {
      const group = new THREE.Group();
      group.visible = false;
      group.scale.setScalar(building.framing?.scale ?? 1);
      group.position.y = building.framing?.y ?? 0;
      this.world.add(group);
      const model: BuildingModel = {
        building,
        group,
        batches: [],
        parts: [],
        top: Math.max(
          ...building.blocks.map((block) => block.y),
          ...(building.parts ?? []).flatMap((part) =>
            part.blocks.map((block) => block.y + part.origin[1]),
          ),
        ),
      };
      this.addBatches(model, building.blocks, group, 0);
      for (const spec of building.parts ?? []) {
        const part = new THREE.Group();
        part.position.set(...spec.origin);
        group.add(part);
        model.parts.push({ group: part, spec });
        this.addBatches(model, spec.blocks, part, spec.origin[1]);
      }
      this.models.push(model);
    }
    const floatingBlocks: [BlockKind, number, number, number, number][] = [
      ['grass', -11, 2, 1, 1.4],
      ['planks', -8, 8, 2, 0.8],
      ['stone', 11, 0, 1, 1],
      ['leaves', 9, 6, 2, 0.8],
      ['grass', 5, -6, 7, 0.7],
      ['dirt', -7, -5, 6, 0.6],
    ];
    for (const [kind, x, y, z, scale] of floatingBlocks) {
      const mesh = new THREE.Mesh(this.geometry, this.material(kind));
      mesh.position.set(x, y, z);
      mesh.userData.origin = mesh.position.clone();
      mesh.scale.setScalar(scale);
      mesh.rotation.set(0.2, 0.35, 0.12);
      this.world.add(mesh);
      this.floaters.push(mesh);
    }
    const smokeMaterial = new THREE.MeshBasicMaterial({
      color: 0xc0bfa7,
      transparent: true,
      opacity: 0.2,
      depthWrite: false,
    });
    for (let i = 0; i < 5; i++) {
      const mesh = new THREE.Mesh(this.geometry, smokeMaterial);
      this.world.add(mesh);
      this.smoke.push(mesh);
    }
    const grid = new THREE.GridHelper(34, 34, 0x61724a, 0x465638);
    grid.position.y = -6.5;
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.16;
    this.world.add(grid);

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.intersectionObserver = new IntersectionObserver(([entry]) => {
      this.inView = entry.isIntersecting;
      this.schedule();
    });
    this.intersectionObserver.observe(container);
    document.addEventListener('visibilitychange', this.schedule);
    this.motionQuery.addEventListener('change', this.motionChange);
    container.addEventListener('pointerdown', this.pointerDown);
    container.addEventListener('pointermove', this.pointerMove);
    container.addEventListener('pointerup', this.pointerUp);
    container.addEventListener('pointercancel', this.pointerUp);
    container.addEventListener('keydown', this.keyDown);
    this.cycleTime = this.motionQuery.matches ? BUILD_SECONDS : 0;
    this.resize();
    this.schedule();
  }

  private material(kind: BlockKind): THREE.Material | THREE.Material[] {
    const cached = this.materials.get(kind);
    if (cached) return cached;
    const texture = (name: BlockKind | 'grass-side' | 'log-top') => {
      if (!this.textures.has(name)) this.textures.set(name, pixelTexture(name));
      return this.textures.get(name)!;
    };
    const create = (name: BlockKind | 'grass-side' | 'log-top') =>
      new THREE.MeshLambertMaterial({ map: texture(name) });
    let result: THREE.Material | THREE.Material[];
    if (kind === 'grass') {
      const side = create('grass-side');
      result = [side, side, create('grass'), create('dirt'), side, side];
    } else if (kind === 'log' || kind === 'beam') {
      const side = create(kind),
        top = create('log-top');
      result =
        kind === 'beam' ? [top, top, side, side, side, side] : [side, side, top, top, side, side];
    } else if (kind === 'window' || kind === 'lantern' || kind === 'crystal') {
      result = new THREE.MeshLambertMaterial({
        map: texture(kind),
        emissive: kind === 'crystal' ? 0x745393 : 0xe9a244,
        emissiveIntensity: kind === 'crystal' ? 0.25 : 0.35,
      });
    } else if (kind === 'water') {
      result = new THREE.MeshLambertMaterial({
        map: texture(kind),
        transparent: true,
        opacity: 0.8,
      });
    } else result = create(kind);
    this.materials.set(kind, result);
    return result;
  }

  private addBatches(model: BuildingModel, source: Block[], group: THREE.Group, originY: number) {
    const groups = new Map<BlockKind, Block[]>();
    for (const block of source) {
      if (!groups.has(block.kind)) groups.set(block.kind, []);
      groups.get(block.kind)!.push(block);
    }
    for (const [kind, blocks] of groups) {
      const mesh = new THREE.InstancedMesh(this.geometry, this.material(kind), blocks.length);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.frustumCulled = false;
      if (kind === 'water') mesh.renderOrder = 1;
      group.add(mesh);
      model.batches.push({ mesh, blocks, originY });
      const color = new THREE.Color();
      blocks.forEach((block, i) => {
        const shade = 0.87 + Math.abs(Math.sin(block.x * 7 + block.z * 11 + block.y)) * 0.13;
        mesh.setColorAt(i, color.setScalar(shade));
      });
    }
  }

  private resize() {
    const { width, height } = this.container.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height);
    const aspect = width / height;
    const halfWidth = Math.max(14.2, 13.3 * aspect);
    this.camera.left = -halfWidth;
    this.camera.right = halfWidth;
    this.camera.top = halfWidth / aspect;
    this.camera.bottom = -halfWidth / aspect;
    this.camera.updateProjectionMatrix();
    this.draw();
  }

  private draw() {
    const model = this.models[this.buildingIndex];
    const phase: HomeSceneState['phase'] =
      this.cycleTime < BUILD_SECONDS
        ? 'build'
        : this.cycleTime < BUILD_SECONDS + HOLD_SECONDS
          ? 'hold'
          : this.cycleTime < CYCLE_SECONDS - 1
            ? 'dismantle'
            : 'switch';
    model.group.visible = phase !== 'switch';
    const stateKey = `${this.buildingIndex}:${phase}`;
    if (stateKey !== this.stateKey) {
      this.stateKey = stateKey;
      this.container.dataset.building = model.building.id;
      this.container.dataset.phase = phase;
      this.container.setAttribute(
        'aria-label',
        `Minecraft 浮空小岛：${model.building.name}。拖动可旋转，方向键可调整视角。`,
      );
      this.onChange({
        name: model.building.name,
        index: this.buildingIndex,
        total: this.models.length,
        phase,
      });
    }
    const dummy = this.dummy;
    if (!this.settled || phase === 'dismantle')
      for (const { mesh, blocks, originY } of model.batches) {
        blocks.forEach((block, i) => {
          const layer = (block.y + originY + 5) / (model.top + 5);
          const stagger = (Math.sin(block.x * 2 + block.z * 3) + 1) * 0.25;
          const p = THREE.MathUtils.clamp((this.cycleTime - layer * 4.2 - stagger) / 3.2, 0, 1);
          const exitTime = this.cycleTime - BUILD_SECONDS - HOLD_SECONDS;
          const exit = THREE.MathUtils.clamp(
            (exitTime - (1 - layer) * 1.8 - stagger * 0.5) / 2.8,
            0,
            1,
          );
          const eased =
            phase === 'dismantle' || phase === 'switch'
              ? 1 - THREE.MathUtils.smoothstep(exit, 0, 1)
              : 1 - (1 - p) ** 3;
          const fly = 1 - eased;
          dummy.position.set(
            block.x * (1 + fly * 0.6),
            block.y + fly * (7 + Math.sin(i) * 2),
            block.z * (1 + fly * 0.6),
          );
          dummy.rotation.set(fly * 0.25, fly * 0.4, fly * 0.12);
          const scale = Math.max(0.001, eased);
          dummy.scale.setScalar(scale);
          if (block.kind === 'water') dummy.scale.y *= 0.85;
          if (block.kind === 'flower') {
            dummy.position.y -= 0.45 * eased;
            dummy.scale.set(0.36 * scale, 0.32 * scale, 0.36 * scale);
          }
          if (block.kind === 'stem') dummy.scale.set(0.12 * scale, scale, 0.12 * scale);
          if (block.kind === 'lantern') {
            dummy.position.y -= 0.15 * eased;
            dummy.scale.set(0.5 * scale, 0.7 * scale, 0.5 * scale);
          }
          if (block.kind === 'rope') dummy.scale.set(0.18 * scale, scale, 0.18 * scale);
          if (block.kind === 'wheat') {
            dummy.position.y -= 0.15 * eased;
            dummy.scale.set(0.55 * scale, 0.7 * scale, 0.55 * scale);
          }
          dummy.updateMatrix();
          mesh.setMatrixAt(i, dummy.matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;
      }
    this.settled = phase === 'hold';
    this.world.rotation.y = this.angle + Math.sin(this.time * 0.06) * 0.1;
    this.world.position.y = Math.sin(this.time * 0.4) * 0.1;
    for (const { group, spec } of model.parts) {
      if (spec.motion === 'spin') group.rotation.z = -this.time * 0.16;
      else group.position.y = spec.origin[1] + Math.sin(this.time * 0.5) * 0.22;
    }
    this.floaters.forEach((mesh, i) => {
      const origin = mesh.userData.origin as THREE.Vector3;
      mesh.position.y = origin.y + Math.sin(this.time * 0.45 + i * 1.5) * 0.35;
      mesh.rotation.y = 0.35 + this.time * 0.06 + i;
      mesh.rotation.z = Math.sin(this.time * 0.2 + i) * 0.1;
    });
    this.smoke.forEach((mesh, i) => {
      const life = (this.time * 0.2 + i / 5) % 1;
      const chimney = model.building.chimney;
      if (chimney)
        mesh.position.set(
          chimney[0] + life * 1.1,
          chimney[1] + life * 4,
          chimney[2] + Math.sin(life * 5) * 0.3,
        );
      mesh.scale.setScalar(0.35 + life * 0.5);
      mesh.visible = !!chimney && phase === 'hold' && life < 0.85;
    });
    this.renderer.render(this.scene, this.camera);
  }

  private tick = (now: number) => {
    this.frame = 0;
    if (this.disposed || this.paused || !this.inView || document.hidden || this.motionQuery.matches)
      return;
    const delta = this.lastFrame ? Math.min((now - this.lastFrame) / 1000, 0.05) : 0;
    this.lastFrame = now;
    this.time += delta;
    this.cycleTime += delta;
    if (this.cycleTime >= CYCLE_SECONDS) {
      this.cycleTime -= CYCLE_SECONDS;
      this.advanceBuilding();
    }
    this.draw();
    this.frame = requestAnimationFrame(this.tick);
  };

  private schedule = () => {
    if (this.disposed) return;
    if (!this.paused && this.inView && !document.hidden && !this.motionQuery.matches) {
      if (!this.frame) {
        this.lastFrame = 0;
        this.frame = requestAnimationFrame(this.tick);
      }
    } else if (this.frame) {
      cancelAnimationFrame(this.frame);
      this.frame = 0;
    }
  };

  private motionChange = () => {
    this.cycleTime = BUILD_SECONDS;
    this.settled = false;
    this.draw();
    this.schedule();
  };

  private pointerDown = (event: PointerEvent) => {
    if (event.button !== 0) return;
    this.drag = { x: event.clientX, angle: this.angle };
    this.container.setPointerCapture(event.pointerId);
  };
  private pointerMove = (event: PointerEvent) => {
    if (!this.drag) return;
    this.angle = this.drag.angle + (event.clientX - this.drag.x) * 0.008;
    this.draw();
  };
  private pointerUp = () => {
    this.drag = null;
  };
  private keyDown = (event: KeyboardEvent) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    this.angle += event.key === 'ArrowLeft' ? -0.15 : 0.15;
    this.draw();
  };

  setPaused(paused: boolean) {
    this.paused = paused;
    this.schedule();
  }

  replay() {
    this.cycleTime = this.motionQuery.matches ? BUILD_SECONDS : 0;
    this.settled = false;
    this.paused = false;
    this.draw();
    this.schedule();
  }

  private advanceBuilding() {
    this.models[this.buildingIndex].group.visible = false;
    if (this.buildingIndex === this.models.length - 1) this.buildingDirection = -1;
    else if (this.buildingIndex === 0) this.buildingDirection = 1;
    this.buildingIndex += this.buildingDirection;
    this.settled = false;
  }

  nextBuilding() {
    this.advanceBuilding();
    this.cycleTime = this.paused || this.motionQuery.matches ? BUILD_SECONDS : 0;
    this.draw();
    this.schedule();
  }

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.intersectionObserver.disconnect();
    document.removeEventListener('visibilitychange', this.schedule);
    this.motionQuery.removeEventListener('change', this.motionChange);
    this.container.removeEventListener('pointerdown', this.pointerDown);
    this.container.removeEventListener('pointermove', this.pointerMove);
    this.container.removeEventListener('pointerup', this.pointerUp);
    this.container.removeEventListener('pointercancel', this.pointerUp);
    this.container.removeEventListener('keydown', this.keyDown);
    this.scene.traverse((object) => {
      if (object instanceof THREE.InstancedMesh) object.dispose();
      if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
        object.geometry.dispose();
        for (const material of Array.isArray(object.material) ? object.material : [object.material])
          material.dispose();
      }
    });
    for (const texture of this.textures.values()) {
      texture.userData.disposed = true;
      texture.dispose();
    }
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
