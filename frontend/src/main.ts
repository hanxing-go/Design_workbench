import './style.css';
import shell from './shell.html?raw';
import type { Material, Model, Packet, Point, Selection, State, Summary } from './types';
import { Viewer } from './viewer';

const root = document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML = shell;

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const input = (id: string) => el<HTMLInputElement>(id).value;
const setInput = (id: string, value: string) => {
  el<HTMLInputElement>(id).value = value;
};
function message(text: string, error = false) {
  el('status').textContent = text;
  el('status').classList.toggle('error', error);
}
async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
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
const params = new URLSearchParams(location.search);
const setBusy = (value: boolean) => {
  busy = value;
  el<HTMLButtonElement>('commit').disabled = value;
  el<HTMLButtonElement>('preview').disabled = value;
};
const endpoint = (suffix = '') => `/api/projects/${project}${suffix}`;

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
    el('selection-hint').textContent = `选区 ${bounds.low.join(',')} → ${bounds.high.join(',')}`;
  }
  setInput('group-filter', '');
}
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
  const start = performance.now();
  const packet = await api<Packet>(endpoint('/render'), full ? {} : viewer.versions);
  if (full) {
    viewer.chunks.clear();
    for (const group of viewer.meshes.values()) viewer.scene.remove(group);
    viewer.meshes.clear();
    viewer.versions = {};
  }
  viewer.update(packet);
  latest = packet;
  summary = await api<Summary & { events: { revision: number; kind: string; changed: number }[] }>(
    endpoint(),
  );
  renderSummary(summary);
  const events = (
    summary as Summary & { events: { revision: number; kind: string; changed: number }[] }
  ).events;
  el('history').replaceChildren(
    ...events.slice(0, 8).map((event) => {
      const div = document.createElement('div');
      div.textContent = `r${event.revision} · ${event.kind} · ${event.changed} 格`;
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
        el('selection-hint').textContent = `分组：${name}`;
      };
      return button;
    }),
  );
  if (value.occupied_bounds) {
    const slider = el<HTMLInputElement>('layer');
    slider.min = String(value.occupied_bounds.low[1]);
    slider.max = String(value.occupied_bounds.high[1]);
    if (viewer.layer === Infinity) slider.value = slider.max;
  }
}

async function loadProjects(preferred?: string) {
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
  viewer.fitted = false;
  viewer.layer = Infinity;
  previous = null;
  setInput('compare', 'current');
  select(null);
  el('layer-label').textContent = '全部';
  clearPreview();
  await refresh(true);
  history.replaceState({}, '', `?project=${project}`);
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
    button.dataset.name = item.name;
    button.setAttribute('aria-label', item.chinese_name);
    const image = document.createElement('img');
    image.alt = '';
    image.width = 56;
    image.height = 56;
    const name = document.createElement('span');
    name.textContent = item.chinese_name;
    const badge = document.createElement('small');
    badge.textContent = { static: '', special: '特殊', invisible: '不可见', missing: '缺资源' }[
      item.support.status
    ];
    button.append(image, name, badge);
    button.onclick = () => void safely(async () => chooseMaterial(item));
    el('materials').append(button);
    if (item.support.status === 'static') {
      const model = await api<Model & { atlas: Packet['atlas'] }>(
        `/api/material/${item.name.split(':')[1]}`,
      );
      viewer.atlas = model.atlas;
      image.src = viewer.thumbnail(model, 72);
    } else image.remove();
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
  el('properties').replaceChildren(
    ...Object.entries(item.properties).map(([name, values]) => {
      const label = document.createElement('label');
      label.textContent = name;
      const select = document.createElement('select');
      select.dataset.property = name;
      select.replaceChildren(...values.map((value) => new Option(value, value)));
      select.value = currentState.properties[name];
      select.onchange = () => {
        currentState.properties[name] = select.value;
      };
      label.append(select);
      return label;
    }),
  );
  el('materials')
    .querySelectorAll<HTMLElement>('.material-card')
    .forEach((card) => card.classList.toggle('chosen', card.dataset.name === item.name));
  message(`已选择 ${item.chinese_name}`);
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
function request(operations: unknown[]) {
  if (!project || !summary) throw new Error('请先选择项目');
  return { expected_revision: summary.revision, request_id: crypto.randomUUID(), operations };
}
async function preview(operations?: unknown[]) {
  const body = request(operations ?? [operation()]);
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
    if (tool === 'select') {
      const position = hit.ground ? ([hit.position[0], 0, hit.position[2]] as Point) : hit.position;
      if (event.shiftKey && selection) {
        select({
          low: selection.low.map((v, i) => Math.min(v, position[i])) as Point,
          high: selection.high.map((v, i) => Math.max(v, position[i])) as Point,
        });
      } else select({ low: position, high: position });
      message(
        hit.protected ? '此格包含保留的实体内容；当前只能查看' : `选中 ${position.join(',')}`,
      );
    } else if (tool === 'place') {
      const target = hit.position.map((v, i) => v + hit.normal[i]) as Point;
      await commit([
        {
          op: 'set',
          blocks: [{ position: target, state: currentState, group: input('result-group') }],
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
bind('new-project', async () => {
  const name = prompt('建筑名称', '新建筑');
  if (!name) return;
  const created = await api<{ project_id: string }>('/api/projects', { name });
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
el<HTMLInputElement>('layer').oninput = () => {
  const layer = Number(input('layer'));
  viewer.setLayer(layer);
  el('layer-label').textContent = String(layer);
};
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
document
  .querySelectorAll<HTMLButtonElement>('[data-view]')
  .forEach(
    (button) =>
      (button.onclick = () => viewer.view(button.dataset.view as 'iso' | 'front' | 'side' | 'top')),
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
  const result = await api<{ issues: unknown[]; proposals: unknown[]; limitations: string[] }>(
    endpoint('/consistency'),
  );
  ruleProposals = result.proposals;
  el('check-result').textContent =
    `${result.issues.length} 个部件问题，${result.proposals.length} 个连接建议。${result.limitations.join('；')}`;
  el('apply-rules').hidden = !result.proposals.length;
});
bind('apply-rules', () => preview([{ op: 'set', blocks: ruleProposals }]));
bind('cabin', async () => {
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
});
document.addEventListener('keydown', (event) => {
  if (
    (event.ctrlKey || event.metaKey) &&
    event.key.toLowerCase() === 'z' &&
    !['INPUT', 'TEXTAREA', 'SELECT'].includes((event.target as HTMLElement).tagName)
  ) {
    event.preventDefault();
    el(event.shiftKey ? 'redo' : 'undo').click();
  }
  if (event.key === 'Escape') clearPreview();
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
  const info = await api<{ minecraft_version: string; resources_ready: boolean }>('/api/info');
  el('version').textContent = `Java ${info.minecraft_version}`;
  if (!info.resources_ready)
    throw new Error('尚未配置素材。先运行 design-workbench resources setup，再重启服务。');
  await viewer.initializeTexture();
  await loadProjects(params.get('project') ?? undefined);
  await loadCatalog();
  const data = await api<{ items: Material[] }>('/api/catalog?query=oak_planks&limit=1');
  if (data.items[0]) await chooseMaterial(data.items[0]);
  message('工作台就绪 · 所有修改自动保存');
});
