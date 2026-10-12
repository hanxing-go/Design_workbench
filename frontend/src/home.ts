import './style.css';
import './home.css';
import home from './home.html?raw';
import buildersUrl from './assets/builders.png';
import { hydrateHomeIcons } from './homeIcons';
import { initMinecraftUI } from './minecraftUI';
import './homeWorkshop.css';
import { clearProjectPreviews, observeProjectPreview } from './projectPreviews';
import type { Summary } from './types';

type HomeProject = Summary & { project_id: string; events?: { created: string }[] };
type Info = { minecraft_version: string; resources_ready: boolean };
type Versions = { default: string; items: Info[] };
const root = document.querySelector<HTMLDivElement>('#app')!;
root.className = 'home-mode';
root.innerHTML = home.replace('__BUILDERS_URL__', buildersUrl);
hydrateHomeIcons();
initMinecraftUI();
const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const createDialog = el<HTMLDialogElement>('home-create-dialog');
const guideDialog = el<HTMLDialogElement>('home-guide-dialog');
const nameInput = el<HTMLInputElement>('home-project-name');
const fileInput = el<HTMLInputElement>('home-import-file');
let projects: HomeProject[] = [];
let loading = false;
let starter = false;
let noticeTimer = 0;
let info: Info | null = null;
let versions: Info[] = [];
const versionSelect = el<HTMLSelectElement>('home-minecraft-version');

function updateResourceStatus() {
  const ready = versions.find(
    (item) => item.minecraft_version === versionSelect.value,
  )?.resources_ready;
  el('home-resource-status').textContent = ready
    ? '此版本素材已就绪。'
    : '首次使用此版本，请下载官方素材；之后可离线建造。';
  el<HTMLButtonElement>('home-resources-setup').disabled = loading || !!ready;
}
versionSelect.onchange = updateResourceStatus;
el('home-resources-setup').onclick = async () => {
  if (loading) return;
  loading = true;
  versionSelect.disabled = true;
  el<HTMLButtonElement>('home-create-submit').disabled = true;
  updateResourceStatus();
  el('home-resource-status').textContent = '正在下载官方素材并生成图集，请稍候…';
  try {
    const result = await api<Info>('/api/resources/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ minecraft_version: versionSelect.value }),
    });
    const item = versions.find((item) => item.minecraft_version === result.minecraft_version);
    if (item) item.resources_ready = result.resources_ready;
    el('home-create-error').textContent = '';
  } catch (error) {
    el('home-create-error').textContent =
      error instanceof Error ? error.message : '素材下载失败，请重试。';
  } finally {
    loading = false;
    versionSelect.disabled = false;
    el<HTMLButtonElement>('home-create-submit').disabled = false;
    updateResourceStatus();
  }
};

function notice(text: string, error = false) {
  const output = el('home-notice');
  output.textContent = text;
  output.classList.toggle('is-error', error);
  output.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = window.setTimeout(() => (output.hidden = true), error ? 8000 : 4000);
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    signal: !options?.method || options.method === 'GET' ? AbortSignal.timeout(20000) : undefined,
    ...options,
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error?.message ?? data.detail ?? `请求失败 (${response.status})`);
  return data as T;
}

function openProject(identifier: string, cabin = false) {
  const params = new URLSearchParams({ project: identifier });
  if (cabin) params.set('starter', 'cabin');
  location.assign(`?${params}`);
}

function readRecents(): Record<string, number> {
  try {
    const data: unknown = JSON.parse(localStorage.getItem('workbench.recentProjects') ?? '{}');
    if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
    return Object.fromEntries(
      Object.entries(data).filter(
        ([, value]) => typeof value === 'number' && Number.isFinite(value),
      ),
    );
  } catch {
    return {};
  }
}

function renderProjects() {
  clearProjectPreviews();
  const query = el<HTMLInputElement>('home-search').value.trim().toLocaleLowerCase();
  const matching = projects.filter((project) => project.name.toLocaleLowerCase().includes(query));
  el('home-project-count').textContent = String(projects.length);
  el('design-count').textContent = `${projects.length} 个项目`;
  el('home-empty').hidden = projects.length > 0;
  el('home-no-results').hidden = !projects.length || !!matching.length;
  el('home-projects').replaceChildren(
    ...matching.map((project) => {
      const card = document.createElement('a');
      card.className = 'project-card';
      card.href = `?project=${encodeURIComponent(project.project_id)}`;
      const art = document.createElement('span');
      art.className = 'project-art';
      art.textContent = project.blocks ? '正在生成建筑预览…' : '空白画布 · 从第一个方块开始';
      if (!project.blocks) art.classList.add('preview-unavailable');
      art.setAttribute('aria-hidden', 'true');
      const content = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = project.name;
      const details = document.createElement('small');
      details.textContent = `${project.blocks.toLocaleString()} 个方块 · Java ${project.minecraft_version}`;
      const edited = document.createElement('small');
      const date = project.events?.[0]?.created;
      const timestamp = date ? Date.parse(date) : NaN;
      edited.textContent = Number.isFinite(timestamp)
        ? `最近编辑 ${new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(timestamp)}`
        : '尚未编辑 · 等待你的灵感';
      if (date) edited.title = new Date(date).toLocaleString('zh-CN');
      content.append(title, details, edited);
      const arrow = document.createElement('span');
      arrow.className = 'project-arrow';
      arrow.textContent = '继续建造 →';
      arrow.setAttribute('aria-hidden', 'true');
      card.append(art, content, arrow);
      if (project.blocks) observeProjectPreview(art, project.project_id, project.revision);
      return card;
    }),
  );
  if (projects.length && !query) {
    const create = document.createElement('button');
    create.className = 'project-create-tile';
    create.type = 'button';
    create.innerHTML =
      '<span class="project-create-plus" aria-hidden="true">＋</span><strong>下一个世界，等你创造</strong><span>新建设计，从第一个方块开始</span><span class="project-create-label">开始建造 →</span>';
    create.onclick = () => showCreate();
    el('home-projects').append(create);
  }
}

function showCreate(cabin = false) {
  if (loading) return;
  starter = cabin;
  nameInput.value = cabin ? '我的林间小屋' : '';
  el('home-create-title').textContent = cabin ? '从一间小屋开始' : '给你的灵感起个名字';
  el('home-create-error').textContent = '';
  updateResourceStatus();
  createDialog.showModal();
  nameInput.focus();
}

document.querySelectorAll<HTMLButtonElement>('[data-home-create]').forEach((button) => {
  button.onclick = () => showCreate();
});
el('home-cabin').onclick = () => showCreate(true);
document.querySelectorAll<HTMLButtonElement>('[data-home-guide]').forEach((button) => {
  button.onclick = () => guideDialog.showModal();
});
document.querySelectorAll<HTMLButtonElement>('[data-home-close]').forEach((button) => {
  button.onclick = () => button.closest('dialog')?.close();
});
for (const dialog of [createDialog, guideDialog]) {
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom
    )
      dialog.close();
  });
}

el<HTMLFormElement>('home-create-form').onsubmit = async (event) => {
  event.preventDefault();
  if (loading) return;
  const name = nameInput.value.trim();
  if (!name) {
    el('home-create-error').textContent = '给你的设计起一个名字吧。';
    nameInput.focus();
    return;
  }
  loading = true;
  const submit = el<HTMLButtonElement>('home-create-submit');
  submit.disabled = true;
  submit.textContent = '正在准备你的世界…';
  try {
    info = await api<Info>(
      `/api/info?minecraft_version=${encodeURIComponent(versionSelect.value)}`,
    );
    if (info && !info.resources_ready)
      throw new Error('此版本素材尚未配置，请点击「下载所选版本的官方素材」。');
    const project = await api<HomeProject>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, minecraft_version: versionSelect.value }),
    });
    openProject(project.project_id, starter);
  } catch (error) {
    el('home-create-error').textContent =
      error instanceof Error ? error.message : '创建失败，请检查本地服务后重试。';
    submit.disabled = false;
    submit.textContent = '创建并开始建造 →';
    loading = false;
  }
};

document.querySelectorAll<HTMLButtonElement>('[data-home-import]').forEach((button) => {
  button.onclick = () => {
    if (!loading) fileInput.click();
  };
});

fileInput.onchange = async () => {
  const file = fileInput.files?.[0];
  if (!file || loading) return;
  if (!file.name.toLowerCase().endsWith('.litematic')) {
    notice('请选择 .litematic 格式的建筑蓝图。', true);
    fileInput.value = '';
    return;
  }
  if (file.size > 32_000_000) {
    notice('蓝图文件不能超过 32 MB，请选择较小的文件。', true);
    fileInput.value = '';
    return;
  }
  loading = true;
  document.querySelectorAll<HTMLButtonElement>('[data-home-import]').forEach((button) => {
    button.disabled = true;
  });
  notice(`正在导入「${file.name}」…`);
  try {
    const probe = new FormData();
    probe.set('file', file);
    const blueprint = await api<Info>('/api/blueprints/info', { method: 'POST', body: probe });
    if (!blueprint.resources_ready) {
      versionSelect.value = blueprint.minecraft_version;
      throw new Error(
        `蓝图使用 Java ${blueprint.minecraft_version}。请在「开始建造」中下载此版本素材，再导入。`,
      );
    }
    const project = await api<HomeProject>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: file.name.replace(/\.litematic$/i, '').slice(0, 128) || '导入的建筑',
        minecraft_version: blueprint.minecraft_version,
      }),
    });
    // Keep the newly created project visible if an invalid blueprint cannot be imported.
    projects.unshift(project);
    renderProjects();
    const body = new FormData();
    body.set('file', file);
    body.set('expected_revision', String(project.revision));
    body.set('request_id', crypto.randomUUID());
    await api(`/api/projects/${encodeURIComponent(project.project_id)}/import`, {
      method: 'POST',
      body,
    });
    openProject(project.project_id);
  } catch (error) {
    notice(error instanceof Error ? error.message : '导入失败，请检查蓝图后重试。', true);
    loading = false;
    document.querySelectorAll<HTMLButtonElement>('[data-home-import]').forEach((button) => {
      button.disabled = false;
    });
  } finally {
    fileInput.value = '';
  }
};

el<HTMLInputElement>('home-search').oninput = renderProjects;
el('home-clear-search').onclick = () => {
  el<HTMLInputElement>('home-search').value = '';
  renderProjects();
  el('home-search').focus();
};
el('design-toggle').onclick = () => {
  const button = el('design-toggle');
  const list = el('home-projects').classList.toggle('is-list');
  button.setAttribute('aria-pressed', String(list));
  button.setAttribute('aria-label', list ? '以网格显示设计' : '以列表显示设计');
  button.innerHTML = `<span data-icon="${list ? 'grid' : 'list'}" aria-hidden="true"></span>`;
  hydrateHomeIcons(button);
};

const tips = [
  '不用一次搭完一座城。先放下第一个方块，剩下的灵感会慢慢到来。',
  '先做建筑轮廓，再补细节。用「盒体填充」和「双坡屋顶」快速确定你的建筑比例。',
  '试试逐层播放：一层一层看清结构，也让复杂的建造变得井井有条。',
  '按 G 进入第一人称。走进自己的建筑，才能发现窗外那一束刚刚好的风景。',
  '多用分组整理墙体、屋顶和窗户。想换一种材料时，就可以一次替换整组。',
];
let tip = 0;
el('home-next-tip').onclick = () => {
  tip = (tip + 1) % tips.length;
  el('home-tip-text').textContent = tips[tip];
};

async function loadHomeData() {
  clearProjectPreviews();
  el('home-projects').setAttribute('aria-busy', 'true');
  el('home-projects').innerHTML =
    '<span class="projects-loading sr-only">正在读取你的设计…</span>' +
    '<div class="project-skeleton" aria-hidden="true"></div>'.repeat(3);
  // Library, connection, and version discovery settle independently.
  void api<Versions>('/api/versions')
    .then((result) => {
      const selected = versionSelect.value;
      versions = result.items;
      versionSelect.replaceChildren(
        ...versions.map(
          (item) =>
            new Option(
              `Java ${item.minecraft_version}${item.resources_ready ? ' · 素材已安装' : ''}`,
              item.minecraft_version,
            ),
        ),
      );
      versionSelect.value = versions.some((item) => item.minecraft_version === selected)
        ? selected
        : result.default;
      updateResourceStatus();
    })
    .catch(() => {
      if (!versions.length)
        el('home-resource-status').textContent = '版本列表暂不可用，请重新连接本地工作台。';
    });
  const connection = el('home-connection');
  void api<Info>('/api/info')
    .then((result) => {
      info = result;
      if (!versions.length) {
        versions = [result];
        versionSelect.replaceChildren(
          new Option(`Java ${result.minecraft_version}`, result.minecraft_version),
        );
        updateResourceStatus();
      }
      el('home-version').textContent = `JAVA ${result.minecraft_version}`;
      connection.replaceChildren(
        document.createElement('i'),
        document.createTextNode(
          result.resources_ready ? '本地工作台已连接' : '已连接 · 待配置方块素材',
        ),
      );
      connection.classList.toggle('is-offline', !result.resources_ready);
    })
    .catch(() => {
      connection.replaceChildren(
        document.createElement('i'),
        document.createTextNode('本地服务未连接'),
      );
      connection.classList.add('is-offline');
    });
  try {
    const result = await api<{ items: HomeProject[]; errors?: unknown[] }>('/api/projects');
    const recents = readRecents();
    projects = result.items.sort(
      (a, b) =>
        (recents[b.project_id] ?? (Date.parse(b.events?.[0]?.created ?? '') || 0)) -
        (recents[a.project_id] ?? (Date.parse(a.events?.[0]?.created ?? '') || 0)),
    );
    renderProjects();
    if (result.errors?.length) notice('部分设计暂时无法读取，其余设计已显示。', true);
  } catch {
    el('home-projects').replaceChildren();
    const error = document.createElement('p');
    error.className = 'projects-error';
    error.textContent = '暂时无法读取设计，请确认本地工作台已启动。';
    const retry = document.createElement('button');
    retry.textContent = '重新连接';
    retry.onclick = () => void loadHomeData();
    error.append(retry);
    el('home-projects').append(error);
  }
  el('home-projects').setAttribute('aria-busy', 'false');
}
void loadHomeData();
window.addEventListener('pageshow', (event) => {
  if (event.persisted) void loadHomeData();
});

void import('./homeScene')
  .then(({ HomeScene }) => {
    let scene: InstanceType<typeof HomeScene>;
    try {
      scene = new HomeScene(el('home-scene'), (state) => {
        el('scene-building-name').textContent = state.name;
        el('scene-building-index').textContent =
          `${String(state.index + 1).padStart(2, '0')} / ${String(state.total).padStart(2, '0')}`;
        el('scene-building-phase').textContent = {
          build: '正在搭建',
          hold: '一方天地，无限可能',
          dismantle: '方块轻轻散开',
          switch: '下一份灵感…',
        }[state.phase];
      });
    } catch {
      el('scene-fallback').hidden = false;
      el('scene-pause').hidden = el('scene-replay').hidden = el('scene-next').hidden = true;
      return;
    }
    let paused = false;
    const pauseButton = el('scene-pause');
    const updatePause = () => {
      pauseButton.setAttribute('aria-pressed', String(paused));
      pauseButton.setAttribute('aria-label', paused ? '继续首页动画' : '暂停首页动画');
      pauseButton.title = paused ? '继续动画' : '暂停动画';
      pauseButton.innerHTML = `<span data-icon="${paused ? 'play' : 'pause'}" aria-hidden="true"></span>`;
      hydrateHomeIcons(pauseButton);
    };
    pauseButton.onclick = () => {
      paused = !paused;
      scene.setPaused(paused);
      updatePause();
    };
    el('scene-replay').onclick = () => {
      paused = false;
      scene.replay();
      updatePause();
    };
    el('scene-next').onclick = () => scene.nextBuilding();
    window.addEventListener('pagehide', (event) => {
      if (!event.persisted) scene.dispose();
    });
  })
  .catch(() => {
    el('scene-fallback').hidden = false;
    el('scene-pause').hidden = el('scene-replay').hidden = el('scene-next').hidden = true;
  });
