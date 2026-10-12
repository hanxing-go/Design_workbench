import './style.css';
import shell from './shell.html?raw';
import { hydrateHomeIcons } from './homeIcons';
import { initMinecraftUI } from './minecraftUI';
import type { Material, Model, Packet, Point, Selection, State, Summary } from './types';
import { Viewer } from './viewer';
import { LayerPlayer } from './layerPlayer';
import { typing } from './walkControls';
import { DesignPanel } from './designPanel';
import { MaterialControls } from './materialControls';

const root = document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML = shell;
hydrateHomeIcons(root);
initMinecraftUI();
document.title = 'Design Workbench · 建筑设计';

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const input = (id: string) => el<HTMLInputElement>(id).value;
const setInput = (id: string, value: string) => {
  el<HTMLInputElement>(id).value = value;
};
let feedbackTimer = 0;
function message(text: string, error = false) {
  el('status').textContent = text;
  el('status').classList.toggle('error', error);
  const feedback = el('walk-feedback');
  feedback.textContent = text;
  feedback.classList.toggle('error', error);
  feedback.hidden = false;
  clearTimeout(feedbackTimer);
  feedbackTimer = window.setTimeout(() => (feedback.hidden = true), error ? 8000 : 3500);
}
async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
  if (project && /^\/api\/(catalog|material\/)/.test(path)) {
    path += (path.includes('?') ? '&' : '?') + 'project=' + encodeURIComponent(project);
  }
  const response = await fetch(path, {
    method: method ?? (body === undefined ? 'GET' : 'POST'),
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error?.message ?? data.detail ?? `请求失败 ${response.status}`);
  return data as T;
}
const viewer = new Viewer(el('stage'));
const layerPlayer = new LayerPlayer(viewer);
let project = '',
  summary: Summary | null = null,
  material: Material | null = null,
  currentState: State = { name: 'minecraft:oak_planks', properties: {} },
  selection: Selection | null = null,
  tool = 'select',
  page = 0,
  total = 0,
  busy = false;
let previewBody: Record<string, unknown> | null = null,
  previous: Packet | null = null,
  latest: Packet | null = null;
let ruleProposals: unknown[] = [];
let ruleRevision = -1;
const materialControls = new MaterialControls(
  el('properties'),
  (state) => {
    currentState = state;
    clearPreview();
    void updateMaterialHud().catch((error) => message(String(error), true));
  },
  async (state) => {
    const activeProject = project;
    const activeResources = latest?.resource_hash;
    const query = new URLSearchParams({ properties: JSON.stringify(state.properties) });
    const model = await api<Model & { atlas: Packet['atlas'] }>(
      `/api/material/${state.name.split(':')[1]}?${query}`,
    );
    if (activeProject !== project || activeResources !== latest?.resource_hash)
      throw new Error('材料预览请求已过期');
    viewer.atlas = model.atlas;
    return viewer.thumbnail(model, 96);
  },
);
const params = new URLSearchParams(location.search);
const setBusy = (value: boolean) => {
  busy = value;
  el('properties').inert = value;
  el<HTMLInputElement>('search').disabled = value;
  el<HTMLSelectElement>('category').disabled = value;
  el<HTMLSelectElement>('projects').disabled = value;
  el('materials')
    .querySelectorAll<HTMLButtonElement>('.material-card')
    .forEach((card) => {
      card.disabled = value;
    });
  el<HTMLButtonElement>('commit').disabled = value;
  el<HTMLButtonElement>('preview').disabled = value;
  el<HTMLButtonElement>('rename-submit').disabled = value;
  layerPlayer.setBusy(value);
};
const endpoint = (suffix = '') => `/api/projects/${project}${suffix}`;
const designPanel = new DesignPanel({
  project: () => project,
  summary: () => summary,
  refresh: async () => {
    clearPreview();
    await refresh();
  },
  preview: (changes) => {
    clearPreview();
    if (changes) viewer.showGhosts(changes);
  },
  openProject: async (id) => {
    await loadProjects(id);
  },
  notice: message,
});

function point(value: string): Point {
  const values = value.split(',').map((v) => Number(v.trim()));
  if (values.length !== 3 || values.some((v) => !Number.isInteger(v)))
    throw new Error('坐标需要三个整数，例如 0,0,0');
  return values as Point;
}
function box(): Selection {
  const a = point(input('low')),
    b = point(input('high'));
  return {
    low: a.map((v, i) => Math.min(v, b[i])) as Point,
    high: a.map((v, i) => Math.max(v, b[i])) as Point,
  };
}
function selector() {
  const group = input('group-filter');
  return group ? { group } : { bounds: selection ?? box() };
}
function select(bounds: Selection | null) {
  selection = bounds;
  viewer.showSelection(bounds);
  if (bounds) {
    setInput('low', bounds.low.join(','));
    setInput('high', bounds.high.join(','));
  }
  selectionHint();
  setInput('group-filter', '');
}
function selectionHint() {
  const gesture = viewer.walk.active
    ? 'Alt+点击选择或扩展选区；Shift 下降'
    : '点击选中；Shift+点击扩展选区';
  el('selection-hint').textContent = selection
    ? `选区 ${selection.low.join(',')} → ${selection.high.join(',')} · ${gesture}`
    : gesture;
}

let walkPanel: 'library' | 'inspector' = 'library';
const immersiveSlots = new Map<HTMLElement, Comment>();
function mountImmersive(active: boolean) {
  if (active && !immersiveSlots.size) {
    // Reuse the editor controls and their handlers; restore their exact positions on exit.
    const destinations: Record<string, string[]> = {
      'walk-menu-exit': ['walk-toggle'],
      'walk-menu-actions': ['undo', 'redo', 'save'],
      'walk-menu-settings': ['walk-reach-control', 'compare'],
      'walk-panel-host': ['library', 'inspector'],
      'walk-menu-layers': ['slice-controls', 'workspace-details'],
      'walk-menu-notices': ['warnings'],
    };
    for (const [destination, ids] of Object.entries(destinations)) {
      for (const id of ids) {
        const element = el(id);
        const slot = document.createComment(id);
        element.before(slot);
        immersiveSlots.set(element, slot);
        el(destination).append(element);
      }
    }
  } else if (!active) {
    for (const [element, slot] of immersiveSlots) slot.replaceWith(element);
    immersiveSlots.clear();
  }
}
viewer.walk.onChange = () => {
  const active = viewer.walk.active,
    locked = viewer.walk.locked,
    wasLocked = root.classList.contains('pointer-locked'),
    wasActive = root.classList.contains('first-person-mode');
  mountImmersive(active);
  root.classList.toggle('first-person-mode', active);
  root.classList.toggle('pointer-locked', active && locked);
  root.classList.toggle('walk-menu-open', active && !locked);
  el('walk-toggle').textContent = active ? '退出第一人称' : '第一人称';
  el('walk-toggle').setAttribute('aria-pressed', String(active));
  el('walk-crosshair').hidden = !active || !locked;
  el('walk-hud').hidden = !active;
  el('walk-menu').hidden = !active || locked;
  el('walk-status').hidden = !locked;
  el('walk-reach-control').hidden = !active;
  el('camera-bar').hidden = active;
  document
    .querySelectorAll<HTMLButtonElement>('[data-tool]')
    .forEach((button) => (button.disabled = active));
  selectionHint();
  renderPanels();
  if (active && wasLocked && !locked) el('walk-resume').focus();
  else if (!active && wasActive) el('walk-toggle').focus();
};
viewer.walk.onError = (text) => message(text, true);
el('walk-toggle').onclick = () => {
  if (viewer.walk.active) viewer.walk.exit();
  else if (summary) {
    layerPlayer.stop();
    viewer.walk.enter(summary.occupied_bounds ? summary.occupied_bounds.low[1] + 1 : 0);
  }
};
el('walk-resume').onclick = () => void viewer.walk.lock();
try {
  const reach = Number(localStorage.getItem('workbench.walkReach'));
  if (Number.isFinite(reach) && reach > 0) viewer.walkReach = reach;
} catch {
  /* Browser settings are optional. */
}
setInput('walk-reach', String(viewer.walkReach));
el<HTMLInputElement>('walk-reach').onchange = () => {
  const reach = el<HTMLInputElement>('walk-reach').valueAsNumber;
  if (!Number.isFinite(reach) || reach <= 0) {
    setInput('walk-reach', String(viewer.walkReach));
    message('命中距离需要大于零。', true);
    return;
  }
  viewer.walkReach = reach;
  try {
    localStorage.setItem('workbench.walkReach', String(reach));
  } catch {
    /* Optional. */
  }
};
function clearPreview() {
  previewBody = null;
  viewer.clearGhosts();
  el('preview-description').textContent = '';
  el('cancel-preview').hidden = true;
}
function snapshot(): Packet | null {
  if (!latest) return null;
  return {
    ...latest,
    chunks: Object.fromEntries(
      [...viewer.chunks].map(([key, value]) => [
        key,
        value.map((cell) => [...cell] as typeof cell),
      ]),
    ),
    models: Object.fromEntries(viewer.models),
    removed_chunks: [],
  };
}

async function refresh(full = false) {
  if (!project) return;
  const activeProject = project;
  const start = performance.now();
  type ObservedSummary = Summary & {
    events: { revision: number; kind: string; changed: number }[];
  };
  let packet: Packet;
  let observed: ObservedSummary;
  let attempts = 0;
  do {
    packet = await api<Packet>(
      `/api/projects/${activeProject}/render`,
      full ? {} : viewer.versions,
    );
    observed = await api<ObservedSummary>(`/api/projects/${activeProject}`);
    if (++attempts >= 3 && packet.revision !== observed.revision)
      throw new Error('场景正在连续更新，请稍后重新读取');
  } while (packet.revision !== observed.revision);
  if (project !== activeProject) return;
  if (full) {
    viewer.clearScene();
  }
  viewer.update(packet);
  await viewer.whenReady();
  latest = packet;
  summary = observed;
  renderSummary(summary);
  const events = (
    summary as Summary & { events: { revision: number; kind: string; changed: number }[] }
  ).events;
  el('history').replaceChildren(
    ...events.slice(0, 8).map((event) => {
      const div = document.createElement('div');
      const kind = { edit: '编辑', import: '导入', rename: '重命名', undo: '撤销', redo: '重做' };
      div.textContent = `r${event.revision} · ${kind[event.kind as keyof typeof kind] ?? event.kind} · ${event.changed} 格`;
      return div;
    }),
  );
  el('stats').textContent =
    `${packet.summary.blocks.toLocaleString()} 方块 · ${Object.keys(packet.chunks).length} 分块更新 · ${Math.round(performance.now() - start)} ms`;
  el('warnings').hidden = packet.warnings.length === 0;
  el('warnings').textContent = packet.warnings
    .map((w) => `${w.name.split(':')[1]}：${w.count} 格（${w.reason}）`)
    .join('；');
}
function renderSummary(value: Summary) {
  el('scene-name').textContent = value.name;
  const option = el<HTMLSelectElement>('projects').selectedOptions[0];
  if (option) option.textContent = value.name;
  el('revision').textContent = `修订 ${value.revision}`;
  el('scene-meta').textContent =
    `${value.blocks.toLocaleString()} 个方块 · 修订 ${value.revision} · 已保存`;
  el('empty-message').hidden = value.blocks > 0;
  el<HTMLButtonElement>('undo').disabled = !value.undo_available;
  el<HTMLButtonElement>('redo').disabled = !value.redo_available;
  const old = input('group-filter');
  el('group-filter').replaceChildren(
    new Option('当前选区', ''),
    ...Object.keys(value.groups).map((name) => new Option(`${name} · ${value.groups[name]}`, name)),
  );
  if (value.groups[old]) setInput('group-filter', old);
  el('group-tree').replaceChildren(
    ...Object.entries(value.groups).map(([name, count]) => {
      const button = document.createElement('button');
      button.textContent = `${name}  ${count}`;
      button.onclick = () => {
        setInput('group-filter', name);
        viewer.showSelection(null);
        el('selection-hint').textContent =
          `分组：${name}${viewer.walk.active ? ' · Alt+点击扩展选区；Shift 下降' : ''}`;
      };
      return button;
    }),
  );
  layerPlayer.update(value);
}

async function loadProjects(preferred?: string) {
  viewer.walk.exit();
  const data = await api<{ items: (Summary & { project_id: string })[] }>('/api/projects');
  const projectsSelect = el<HTMLSelectElement>('projects');
  projectsSelect.replaceChildren(
    ...data.items.map((item) => new Option(item.name, item.project_id)),
  );
  if (!data.items.length) {
    const created = await api<Summary & { project_id: string }>('/api/projects', {
      name: '我的建筑',
    });
    await loadProjects(created.project_id);
    return;
  }
  project = preferred ?? project ?? '';
  if (!data.items.some((item) => item.project_id === project)) project = data.items[0].project_id;
  projectsSelect.value = project;
  const info = await api<{ minecraft_version: string; resources_ready: boolean }>(
    `/api/info?project=${encodeURIComponent(project)}`,
  );
  el('version').textContent = `Java ${info.minecraft_version}`;
  if (!info.resources_ready)
    throw new Error(`Java ${info.minecraft_version} 素材尚未安装，请回到首页下载此版本素材。`);
  viewer.atlasUrl = `/api/atlas.png?project=${encodeURIComponent(project)}`;
  if (!viewer.texture) await viewer.initializeTexture();
  viewer.fitted = false;
  viewer.layer = Infinity;
  previous = null;
  setInput('compare', 'current');
  select(null);
  clearPreview();
  await refresh(true);
  page = 0;
  material = null;
  currentState = { name: 'minecraft:oak_planks', properties: {} };
  await loadCatalog();
  const defaultMaterial = await api<{ items: Material[] }>('/api/catalog?query=oak_planks&limit=1');
  if (defaultMaterial.items[0]) await chooseMaterial(defaultMaterial.items[0]);
  history.replaceState({}, '', `?project=${project}`);
  await designPanel.load();
  try {
    const stored: unknown = JSON.parse(localStorage.getItem('workbench.recentProjects') ?? '{}');
    const recents = stored && typeof stored === 'object' && !Array.isArray(stored) ? stored : {};
    localStorage.setItem(
      'workbench.recentProjects',
      JSON.stringify({ ...recents, [project]: Date.now() }),
    );
  } catch {
    /* Recent projects are optional when browser storage is unavailable. */
  }
}

async function loadCatalog() {
  const query = new URLSearchParams({
    query: input('search'),
    category: input('category'),
    offset: String(page * 24),
    limit: '24',
  });
  const data = await api<{ items: Material[]; total: number }>(`/api/catalog?${query}`);
  total = data.total;
  el('catalog-total').textContent = String(total);
  el('page').textContent = `${page + 1} / ${Math.max(1, Math.ceil(total / 24))}`;
  el<HTMLButtonElement>('prev-page').disabled = page === 0;
  el<HTMLButtonElement>('next-page').disabled = (page + 1) * 24 >= total;
  el('materials').replaceChildren();
  for (const item of data.items) {
    const button = document.createElement('button');
    button.className = 'material-card';
    button.disabled = true;
    button.dataset.name = item.name;
    button.setAttribute('aria-label', item.chinese_name);
    const image = document.createElement('img');
    image.alt = '';
    image.width = 56;
    image.height = 56;
    const name = document.createElement('span');
    name.textContent = item.chinese_name;
    const badge = document.createElement('small');
    badge.textContent = { static: '', special: '暂无预览', invisible: '不可见', missing: '缺资源' }[
      item.support.status
    ];
    button.title = `${item.chinese_name} · ${item.support.reason}`;
    button.append(image, name, badge);
    button.onclick = () => void safely(async () => chooseMaterial(item));
    el('materials').append(button);
    if (item.support.status === 'static') {
      const model = await api<Model & { atlas: Packet['atlas'] }>(
        `/api/material/${item.name.split(':')[1]}`,
      );
      viewer.atlas = model.atlas;
      image.src = viewer.thumbnail(model, 72);
    } else {
      const placeholder = document.createElement('span');
      placeholder.className = 'material-placeholder';
      placeholder.setAttribute('aria-hidden', 'true');
      placeholder.textContent = item.support.status === 'invisible' ? '◇' : '▧';
      image.replaceWith(placeholder);
    }
  }
  el('materials')
    .querySelectorAll<HTMLElement>('.material-card')
    .forEach((card) => card.classList.toggle('chosen', card.dataset.name === currentState.name));
}
async function chooseMaterial(item: Material) {
  material = item;
  currentState = { ...item.default_state, properties: { ...item.default_state.properties } };
  el('material-name').textContent = item.chinese_name;
  el('material-id').textContent = item.name;
  el('material-support').textContent = item.support.reason;
  materialControls.show(item, currentState);
  el('materials')
    .querySelectorAll<HTMLElement>('.material-card')
    .forEach((card) => card.classList.toggle('chosen', card.dataset.name === item.name));
  await updateMaterialHud();
  message(`已选择 ${item.chinese_name}`);
}
let materialHudRequest = 0;
async function updateMaterialHud() {
  const request = ++materialHudRequest;
  const activeProject = project;
  const activeResources = latest?.resource_hash;
  el('walk-material-name').textContent = material?.chinese_name ?? currentState.name;
  const propertyLabels: Record<string, Record<string, string>> = {
    facing: { north: '朝北', south: '朝南', west: '朝西', east: '朝东', up: '朝上', down: '朝下' },
    axis: { x: '沿 X 轴', y: '沿 Y 轴', z: '沿 Z 轴' },
    half: { top: '上半部', bottom: '下半部', upper: '上半部', lower: '下半部' },
    waterlogged: { true: '含水', false: '不含水' },
  };
  el('walk-material-properties').textContent = Object.entries(currentState.properties)
    .filter(([name, value]) => value !== material?.default_state.properties[name])
    .map(([name, value]) => propertyLabels[name]?.[value] ?? `${name}：${value}`)
    .join(' · ');
  const image = el<HTMLImageElement>('walk-material-image');
  image.hidden = true;
  if (material?.support.status !== 'static') return;
  const query = new URLSearchParams({ properties: JSON.stringify(currentState.properties) });
  const model = await api<Model & { atlas: Packet['atlas'] }>(
    `/api/material/${currentState.name.split(':')[1]}?${query}`,
  );
  if (
    request !== materialHudRequest ||
    activeProject !== project ||
    activeResources !== latest?.resource_hash
  )
    return;
  viewer.atlas = model.atlas;
  image.src = viewer.thumbnail(model, 72);
  image.hidden = false;
}

function fields() {
  const kind = input('operation');
  const descriptions: Record<string, string> = {
    fill: '<label><input id="hollow" type="checkbox"> 仅填充外壳</label>',
    replace: '<p class="muted">将选区或分组替换为当前材料。</p>',
    delete: '<p class="muted">删除选区或分组中的方块。</p>',
    group: '<p class="muted">将选区归入“结果分组”。</p>',
    transform:
      '<label>位移 <input id="offset" value="0,0,0"></label><label>变换中心 <input id="origin" value="0,0,0"></label><label>旋转 <select id="rotation"><option>0</option><option>90</option><option>180</option><option>270</option></select></label><label>镜像 <select id="mirror"><option value="">无</option><option value="x">沿 X</option><option value="z">沿 Z</option></select></label><label><input id="copy" type="checkbox"> 保留原件，复制</label><label><input id="overwrite" type="checkbox"> 允许覆盖目标</label>',
    array:
      '<label>重复数 X,Y,Z <input id="count" value="3,1,1"></label><label>间距 X,Y,Z <input id="step" value="8,0,0"></label>',
    extrude:
      '<label>轮廓 X,Z（每行一个点）<textarea id="polygon">0,0\n6,0\n6,8\n0,8</textarea></label><label>起始 Y <input id="base-y" type="number" value="0"></label><label>高度 <input id="height" type="number" value="4" min="1"></label>',
    arc: '<label>中心 <input id="center" value="0,0,0"></label><label>半径 <input id="radius" type="number" value="8" min="1"></label><label>厚度 <input id="thickness" type="number" value="1" min="1"></label><label>高度 <input id="height" type="number" value="1" min="1"></label><div class="coordinates"><label>起始角 <input id="start-angle" type="number" value="0"></label><label>结束角 <input id="end-angle" type="number" value="360"></label></div>',
    roof: '<label>屋脊方向 <select id="ridge"><option value="z">沿 Z</option><option value="x">沿 X</option></select></label><label>最高起伏 <input id="height" type="number" value="4" min="1"></label><p class="muted">选区起点 Y 为檐口高度，使用当前材料。</p>',
    window:
      '<label>墙面法向 <select id="window-axis"><option value="z">Z（窗宽沿 X）</option><option value="x">X（窗宽沿 Z）</option></select></label><label>边框材料 <input id="frame" value="oak_log"></label><p class="muted">玻璃使用当前材料；选区必须为单格厚。</p>',
  };
  el('operation-fields').innerHTML = descriptions[kind] ?? '';
  clearPreview();
}
function operation(): Record<string, unknown> {
  const kind = input('operation'),
    bounds = selection ?? box(),
    group = input('result-group') || 'main';
  const state = { name: currentState.name, properties: { ...currentState.properties } };
  switch (kind) {
    case 'fill':
      return { op: kind, bounds, state, group, hollow: el<HTMLInputElement>('hollow').checked };
    case 'replace':
      return { op: kind, selector: selector(), state };
    case 'delete':
      return { op: kind, selector: selector() };
    case 'group':
      return { op: kind, selector: selector(), name: group };
    case 'transform':
      return {
        op: kind,
        selector: selector(),
        origin: point(input('origin')),
        offset: point(input('offset')),
        rotation: Number(input('rotation')),
        mirror: input('mirror') || null,
        copy: el<HTMLInputElement>('copy').checked,
        overwrite: el<HTMLInputElement>('overwrite').checked,
        group,
      };
    case 'array':
      return {
        op: kind,
        selector: selector(),
        count: point(input('count')),
        step: point(input('step')),
        group,
      };
    case 'extrude':
      return {
        op: kind,
        polygon: input('polygon')
          .split('\n')
          .filter(Boolean)
          .map((line) => {
            const p = line.split(',').map(Number);
            if (p.length !== 2 || p.some((v) => !Number.isInteger(v)))
              throw new Error('轮廓每行需要 X,Z 两个整数');
            return p;
          }),
        base_y: Number(input('base-y')),
        height: Number(input('height')),
        state,
        group,
      };
    case 'arc':
      return {
        op: kind,
        center: point(input('center')),
        radius: Number(input('radius')),
        thickness: Number(input('thickness')),
        height: Number(input('height')),
        start: Number(input('start-angle')),
        end: Number(input('end-angle')),
        state,
        group,
      };
    case 'roof':
      return {
        op: kind,
        bounds,
        ridge_axis: input('ridge'),
        height: Number(input('height')),
        state,
        group,
      };
    case 'window':
      return {
        op: kind,
        bounds,
        axis: input('window-axis'),
        frame: { name: input('frame') },
        glass: state,
        group,
      };
    default:
      throw new Error('请选择设计工具');
  }
}
function request(operations: unknown[], options: { auto_connect?: boolean } = {}) {
  if (!project || !summary) throw new Error('请先选择项目');
  const usesMaterial = operations.some((operation) =>
    ['place', 'set', 'fill', 'replace', 'extrude', 'arc', 'roof', 'window'].includes(
      (operation as { op: string }).op,
    ),
  );
  return {
    expected_revision: summary.revision,
    request_id: crypto.randomUUID(),
    auto_connect: usesMaterial ? materialControls.automatic : true,
    operations,
    ...options,
  };
}
async function preview(operations?: unknown[], options: { auto_connect?: boolean } = {}) {
  const body = request(operations ?? [operation()], options);
  const result = await api<{
    changed: number;
    changes: { position: Point; after: unknown }[];
    truncated: boolean;
  }>(endpoint('/preview'), body);
  previewBody = body;
  viewer.showGhosts(result.changes);
  el('preview-description').textContent =
    `将修改 ${result.changed.toLocaleString()} 格。绿色新增或替换，红色删除。${result.truncated ? '预览显示前一万格。' : ''}`;
  el('cancel-preview').hidden = false;
  message(`修改预览：${result.changed} 格，尚未提交`);
}
async function commit(operations?: unknown[]) {
  if (input('compare') === 'before') throw new Error('先切回当前设计再编辑');
  const body = operations ? request(operations) : (previewBody ?? request([operation()]));
  previous = snapshot();
  const result = await api<{ revision: number; changed: number }>(endpoint('/edit'), body);
  clearPreview();
  await refresh();
  message(`已保存修订 ${result.revision}，修改 ${result.changed} 格`);
}
async function safely(action: () => Promise<void>) {
  if (busy) return;
  setBusy(true);
  try {
    await action();
  } catch (error) {
    message(error instanceof Error ? error.message : String(error), true);
  } finally {
    setBusy(false);
  }
}

viewer.onHit = (hit, event) =>
  void safely(async () => {
    if (!hit || !summary) return;
    if (input('compare') === 'before') throw new Error('先切回当前设计');
    const action = viewer.walk.active
      ? event.button === 2
        ? 'place'
        : event.altKey
          ? 'select'
          : 'erase'
      : tool;
    if (action === 'select') {
      const position = hit.ground ? ([hit.position[0], 0, hit.position[2]] as Point) : hit.position;
      if ((viewer.walk.active ? event.altKey : event.shiftKey) && selection) {
        select({
          low: selection.low.map((v, i) => Math.min(v, position[i])) as Point,
          high: selection.high.map((v, i) => Math.max(v, position[i])) as Point,
        });
      } else select({ low: position, high: position });
      message(
        hit.protected ? '此格包含保留的实体内容；当前只能查看' : `选中 ${position.join(',')}`,
      );
    } else if (action === 'place') {
      await commit([
        {
          op: 'place',
          hit: hit.position,
          normal: hit.normal,
          location: hit.location,
          facing: viewer.placementFacing(),
          automatic: materialControls.automatic,
          state: currentState,
          group: input('result-group'),
        },
      ]);
    } else if (!hit.ground) {
      await commit([
        { op: 'delete', selector: { bounds: { low: hit.position, high: hit.position } } },
      ]);
    }
  });

function bind(id: string, action: () => Promise<void>) {
  el(id).onclick = () => void safely(action);
}
const renameDialog = el<HTMLDialogElement>('rename-dialog');
el('rename-project').onclick = () => {
  if (busy || !summary) return;
  if (viewer.walk.locked) document.exitPointerLock();
  layerPlayer.stop();
  setInput('project-name', summary.name);
  el<HTMLInputElement>('project-name').setCustomValidity('');
  el('rename-error').textContent = '';
  renameDialog.showModal();
  el<HTMLInputElement>('project-name').select();
};
el<HTMLInputElement>('project-name').oninput = () => {
  el<HTMLInputElement>('project-name').setCustomValidity('');
  el('rename-error').textContent = '';
};
el<HTMLFormElement>('rename-form').onsubmit = (event) => {
  event.preventDefault();
  const name = input('project-name').trim();
  if (!name) {
    el<HTMLInputElement>('project-name').setCustomValidity('请输入设计名称');
    el<HTMLInputElement>('project-name').reportValidity();
    return;
  }
  if (name === summary?.name) {
    renameDialog.close();
    return;
  }
  void safely(async () => {
    try {
      previous = snapshot();
      await api(
        endpoint(),
        {
          name,
          expected_revision: summary!.revision,
          request_id: crypto.randomUUID(),
        },
        'PATCH',
      );
      clearPreview();
      await refresh();
      renameDialog.close();
      message(`已重命名为「${name}」并保存`);
    } catch (error) {
      el('rename-error').textContent = error instanceof Error ? error.message : String(error);
      throw error;
    }
  });
};
el('help').onclick = () => {
  if (viewer.walk.locked) document.exitPointerLock();
  layerPlayer.stop();
  el<HTMLDialogElement>('help-dialog').showModal();
};
document.querySelectorAll<HTMLButtonElement>('[data-close-dialog]').forEach((button) => {
  button.onclick = () => el<HTMLDialogElement>(button.dataset.closeDialog!).close();
});

type Panels = { library: boolean; inspector: boolean };
function savedPanels(): Panels {
  const fallback = { library: innerWidth > 780, inspector: innerWidth > 780 };
  try {
    const value = JSON.parse(localStorage.getItem('workbench.panels') ?? 'null');
    return value && typeof value.library === 'boolean' && typeof value.inspector === 'boolean'
      ? value
      : fallback;
  } catch {
    return fallback;
  }
}
let panels = savedPanels();
let panelsBeforeFocus: Panels | null = null;
function renderPanels() {
  for (const side of ['library', 'inspector'] as const) {
    const visible = viewer.walk.active ? !viewer.walk.locked && walkPanel === side : panels[side];
    el(side).hidden = !visible;
    el('workbench-layout').classList.toggle(`${side}-hidden`, !panels[side]);
    el(`toggle-${side}`).setAttribute('aria-expanded', String(panels[side]));
  }
  const focused = !panels.library && !panels.inspector;
  el('focus-mode').setAttribute('aria-pressed', String(focused));
  el('focus-mode').textContent = focused ? '退出专注' : '专注';
  document.querySelectorAll<HTMLButtonElement>('[data-walk-panel]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.walkPanel === walkPanel));
  });
  el('walk-menu-layers').hidden = walkPanel !== 'inspector';
  if (viewer.walk.active) return;
  try {
    localStorage.setItem('workbench.panels', JSON.stringify(panels));
  } catch {
    // The controls also work when browser storage is unavailable.
  }
}
for (const side of ['library', 'inspector'] as const) {
  el(`toggle-${side}`).onclick = () => {
    if (viewer.walk.active) {
      walkPanel = side;
      if (viewer.walk.locked) document.exitPointerLock();
      renderPanels();
      return;
    }
    panelsBeforeFocus = null;
    panels[side] = !panels[side];
    renderPanels();
  };
}
document.querySelectorAll<HTMLButtonElement>('[data-walk-panel]').forEach((button) => {
  button.onclick = () => {
    walkPanel = button.dataset.walkPanel as typeof walkPanel;
    renderPanels();
  };
});
el('focus-mode').onclick = () => {
  if (viewer.walk.active) return;
  if (!panels.library && !panels.inspector) {
    panels = panelsBeforeFocus ?? { library: true, inspector: true };
    panelsBeforeFocus = null;
  } else {
    panelsBeforeFocus = { ...panels };
    panels = { library: false, inspector: false };
  }
  renderPanels();
};
renderPanels();
document.addEventListener('visibilitychange', () => {
  if (document.hidden) layerPlayer.stop();
});

bind('new-project', async () => {
  const name = prompt('建筑名称', '新建筑');
  if (!name) return;
  const created = await api<{ project_id: string }>('/api/projects', {
    name,
    minecraft_version: summary?.minecraft_version,
  });
  await loadProjects(created.project_id);
  message('新项目已创建');
});
el<HTMLSelectElement>('projects').onchange = () =>
  void safely(async () => {
    await loadProjects(input('projects'));
    message('项目已打开');
  });
bind('save', async () => {
  await refresh();
  message(`已保存并重新读取，修订 ${summary?.revision}`);
});
for (const direction of ['undo', 'redo'])
  bind(direction, async () => {
    previous = snapshot();
    await api(endpoint(`/history/${direction}`), {
      expected_revision: summary!.revision,
      request_id: crypto.randomUUID(),
    });
    clearPreview();
    await refresh();
    message(direction === 'undo' ? '已撤销并保存' : '已重做并保存');
  });
bind('preview', () => preview());
bind('commit', () => commit());
bind('cancel-preview', async () => clearPreview());
bind('select-bounds', async () => {
  select(box());
  message('选区已更新');
});
el<HTMLSelectElement>('operation').onchange = fields;
el<HTMLSelectElement>('compare').onchange = () =>
  void safely(async () => {
    clearPreview();
    if (input('compare') === 'before') {
      if (!previous) {
        setInput('compare', 'current');
        throw new Error('还没有可对比的上次修改');
      }
      viewer.update({
        ...previous,
        removed_chunks: Object.keys(viewer.versions).filter((id) => !previous!.chunks[id]),
      });
      await viewer.whenReady();
      layerPlayer.update(previous.summary);
      message(`查看修改前 r${previous.revision}`);
    } else {
      await refresh(true);
      message('查看当前设计');
    }
  });
document.querySelectorAll<HTMLButtonElement>('[data-tool]').forEach(
  (button) =>
    (button.onclick = () => {
      tool = button.dataset.tool!;
      document
        .querySelectorAll('[data-tool]')
        .forEach((item) => item.classList.toggle('active', item === button));
    }),
);
document.querySelectorAll<HTMLButtonElement>('[data-view]').forEach(
  (button) =>
    (button.onclick = () => {
      viewer.view(button.dataset.view as 'iso' | 'front' | 'side' | 'top');
      document
        .querySelectorAll<HTMLButtonElement>('[data-view]')
        .forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    }),
);
el('fit').onclick = () => {
  if (summary?.occupied_bounds) viewer.fit(summary.occupied_bounds);
};
let searchTimer = 0;
el<HTMLInputElement>('search').oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    page = 0;
    void safely(loadCatalog);
  }, 300);
};
el<HTMLSelectElement>('category').onchange = () => {
  page = 0;
  void safely(loadCatalog);
};
bind('prev-page', async () => {
  page = Math.max(0, page - 1);
  await loadCatalog();
});
bind('next-page', async () => {
  page++;
  await loadCatalog();
});
el('import').onclick = () => el<HTMLInputElement>('import-file').click();
el<HTMLInputElement>('import-file').onchange = () =>
  void safely(async () => {
    const file = el<HTMLInputElement>('import-file').files?.[0];
    if (!file || !summary) return;
    const form = new FormData();
    form.set('file', file);
    form.set('expected_revision', String(summary.revision));
    form.set('request_id', crypto.randomUUID());
    previous = snapshot();
    const response = await fetch(endpoint('/import'), { method: 'POST', body: form });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.message ?? '导入失败');
    viewer.fitted = false;
    viewer.layer = Infinity;
    await refresh(true);
    message(`导入完成：${result.import_report.blocks.toLocaleString()} 方块，特殊内容已保留`);
    el<HTMLInputElement>('import-file').value = '';
  });
bind('export', async () => {
  const response = await fetch(endpoint('/export'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_revision: summary!.revision }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message ?? '导出失败');
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${summary!.name}-r${summary!.revision}.litematic`;
  link.click();
  URL.revokeObjectURL(url);
  message('蓝图已导出，方块状态与保留内容已写入');
});
bind('check', async () => {
  const result = await api<{
    revision: number;
    issues: { position: Point; message: string }[];
    proposals: unknown[];
    limitations: string[];
  }>(endpoint('/consistency'));
  ruleProposals = result.proposals;
  ruleRevision = result.revision;
  el('check-result').textContent =
    `${result.issues.length} 个部件问题，${result.proposals.length} 个连接或补全建议。${result.limitations.join('；')}`;
  el('apply-rules').hidden = !result.proposals.length;
  const issues = el('check-issues');
  issues.hidden = !result.issues.length;
  issues.replaceChildren(
    ...result.issues.slice(0, 100).map((issue) => {
      const item = document.createElement('li');
      item.textContent = `${issue.position.join(', ')}：${issue.message}`;
      return item;
    }),
  );
  if (result.issues.length > 100) {
    const item = document.createElement('li');
    item.textContent = `其余 ${result.issues.length - 100} 个问题可通过接口查看。`;
    issues.append(item);
  }
});
bind('apply-rules', async () => {
  if (ruleRevision !== summary?.revision) throw new Error('设计已修改，请重新检查连接后再预览修复');
  await preview([{ op: 'set', blocks: ruleProposals }], { auto_connect: true });
});
async function createCabin() {
  await commit([
    {
      op: 'fill',
      bounds: { low: [0, 0, 0], high: [8, 0, 10] },
      state: { name: 'oak_planks' },
      group: 'floor',
    },
    {
      op: 'fill',
      bounds: { low: [0, 1, 0], high: [8, 4, 10] },
      state: { name: 'oak_planks' },
      group: 'walls',
      hollow: true,
    },
    { op: 'fill', bounds: { low: [1, 4, 1], high: [7, 4, 9] }, state: { name: 'air' } },
    { op: 'fill', bounds: { low: [4, 1, 0], high: [4, 2, 0] }, state: { name: 'air' } },
    {
      op: 'roof',
      bounds: { low: [-1, 5, -1], high: [9, 5, 11] },
      state: { name: 'spruce_stairs' },
      ridge_axis: 'z',
      height: 6,
      group: 'roof',
    },
    {
      op: 'window',
      bounds: { low: [1, 1, 0], high: [3, 3, 0] },
      axis: 'z',
      frame: { name: 'oak_log' },
      glass: { name: 'glass' },
      group: 'windows',
    },
    {
      op: 'window',
      bounds: { low: [5, 1, 0], high: [7, 3, 0] },
      axis: 'z',
      frame: { name: 'oak_log' },
      glass: { name: 'glass' },
      group: 'windows',
    },
    {
      op: 'set',
      blocks: [
        {
          position: [4, 1, 0],
          state: { name: 'oak_door', properties: { half: 'lower', facing: 'north' } },
          group: 'door',
        },
        {
          position: [4, 2, 0],
          state: { name: 'oak_door', properties: { half: 'upper', facing: 'north' } },
          group: 'door',
        },
      ],
    },
  ]);
  viewer.fitted = false;
  await refresh(true);
  message('木屋起稿完成，可继续自由编辑');
}
bind('cabin', createCabin);
document.addEventListener('keydown', (event) => {
  const target = event.target instanceof HTMLElement ? event.target : null;
  if (
    event.defaultPrevented ||
    event.isComposing ||
    event.repeat ||
    event.altKey ||
    document.querySelector('dialog[open]') ||
    typing(target)
  )
    return;
  const key = event.key.toLowerCase();
  if (viewer.walk.active && [' ', 'shift', 'control'].includes(key)) return;
  if (target?.closest('button') && [' ', 'arrowleft', 'arrowright'].includes(key)) return;
  if (event.ctrlKey || event.metaKey) {
    const action =
      key === 'z'
        ? event.shiftKey
          ? 'redo'
          : 'undo'
        : key === 'y'
          ? 'redo'
          : key === 's'
            ? 'save'
            : '';
    if (action) {
      event.preventDefault();
      el(action).click();
    }
    return;
  }
  const actions: Record<string, () => void> = {
    ' ': () => layerPlayer.toggle(),
    arrowleft: () => layerPlayer.step(-1),
    arrowright: () => layerPlayer.step(1),
    '[': () => el('toggle-library').click(),
    ']': () => el('toggle-inspector').click(),
    f: () => el('fit').click(),
    g: () => el('walk-toggle').click(),
    f2: () => el('rename-project').click(),
    '?': () => el('help').click(),
    escape: () => {
      layerPlayer.stop();
      clearPreview();
    },
  };
  if (['1', '2', '3'].includes(key)) {
    event.preventDefault();
    document
      .querySelector<HTMLButtonElement>(
        `[data-tool="${{ '1': 'select', '2': 'place', '3': 'erase' }[key as '1' | '2' | '3']}"]`,
      )
      ?.click();
  } else if (
    key === 'tab' &&
    (target === document.body ||
      target?.tagName === 'CANVAS' ||
      target?.id === 'stage' ||
      target?.id === 'app')
  ) {
    event.preventDefault();
    el('focus-mode').click();
  } else if (actions[key]) {
    event.preventDefault();
    actions[key]();
  }
});

Object.defineProperty(window, 'workbench', {
  value: {
    viewer,
    get project() {
      return project;
    },
    get summary() {
      return summary;
    },
    get selection() {
      return selection;
    },
    get busy() {
      return busy;
    },
  },
  writable: false,
});
fields();
void safely(async () => {
  await loadProjects(params.get('project') ?? undefined);
  message('工作台就绪 · 所有修改自动保存');
  if (params.get('starter') === 'cabin' && summary?.blocks === 0 && summary.revision === 0)
    await createCabin();
});

let polling = false;
window.setInterval(() => {
  if (polling || busy || document.hidden || !project || !summary || input('compare') === 'before')
    return;
  polling = true;
  const activeProject = project;
  void api<Summary>(`/api/projects/${activeProject}`)
    .then(async (current) => {
      if (busy || project !== activeProject || current.revision === summary?.revision) return;
      await safely(async () => {
        await refresh();
        message(
          previewBody
            ? `已读取外部编辑 r${summary?.revision}；当前预演基于旧修订，请重新预演`
            : `已读取外部编辑 r${summary?.revision}`,
        );
      });
    })
    .catch((error: unknown) => {
      console.warn('读取外部修订失败', error);
    })
    .finally(() => {
      polling = false;
    });
}, 1500);
