import type { Material, State } from './types';

const names: Record<string, string> = {
  facing: '方向',
  half: '上下位置',
  shape: '形态',
  type: '类型',
  waterlogged: '含水',
  axis: '轴向',
  open: '打开',
  hinge: '门轴',
  powered: '激活',
  rotation: '旋转',
  north: '北侧连接',
  east: '东侧连接',
  south: '南侧连接',
  west: '西侧连接',
  face: '附着面',
  hanging: '悬挂',
  part: '部件',
  persistent: '保持叶片',
};
const values: Record<string, string> = {
  north: '北 ↑',
  east: '东 →',
  south: '南 ↓',
  west: '西 ←',
  up: '向上',
  down: '向下',
  top: '上半部',
  bottom: '下半部',
  upper: '上半部',
  lower: '下半部',
  double: '双层',
  straight: '直线',
  inner_left: '内左拐角',
  inner_right: '内右拐角',
  outer_left: '外左拐角',
  outer_right: '外右拐角',
  true: '是',
  false: '否',
  left: '左侧',
  right: '右侧',
  single: '单个',
  floor: '地面',
  wall: '墙面',
  ceiling: '天花板',
  head: '床头',
  foot: '床尾',
  none: '不连接',
  low: '低墙',
  tall: '高墙',
  x: '东西',
  y: '上下',
  z: '南北',
};

export class MaterialControls {
  automatic = true;
  private material: Material | null = null;
  private state: State = { name: '', properties: {} };
  private generation = 0;
  private advancedOpen = false;

  constructor(
    private container: HTMLElement,
    private change: (state: State, automatic: boolean) => void,
    private thumbnail: (state: State) => Promise<string>,
  ) {}

  show(material: Material, state: State) {
    this.material = material;
    this.state = state;
    this.automatic = true;
    this.advancedOpen = false;
    this.draw();
  }

  private choose(property: string, value: string) {
    this.state.properties[property] = value;
    this.automatic = false;
    this.change(this.state, this.automatic);
    this.draw();
  }

  private draw() {
    if (!this.material) return;
    const material = this.material;
    const generation = ++this.generation;
    const mode = document.createElement('label');
    mode.className = 'placement-mode';
    const automatic = document.createElement('input');
    automatic.type = 'checkbox';
    automatic.id = 'automatic-placement';
    automatic.checked = this.automatic;
    automatic.onchange = () => {
      this.automatic = automatic.checked;
      this.change(this.state, this.automatic);
      this.draw();
    };
    mode.append(automatic, '自动朝向与贴合');
    const hint = document.createElement('p');
    hint.className = 'placement-hint';
    hint.textContent = this.automatic
      ? '按点击位置和视角放置；连接与拐角随邻居更新。'
      : '按所选形态放置，本次保留手动属性。重新勾选可恢复自动放置。';
    this.container.replaceChildren(mode, hint);

    const preview = document.createElement('img');
    preview.className = 'material-state-preview';
    preview.alt = '当前材料形态预览';
    this.container.append(preview);
    const showImage = (image: HTMLImageElement, state: State) => {
      void this.thumbnail(state)
        .then((url) => {
          if (generation === this.generation) image.src = url;
        })
        .catch(() => {
          if (generation === this.generation) image.hidden = true;
        });
    };
    if (material.support.status === 'static') showImage(preview, this.state);
    else preview.hidden = true;

    const visualProperties = material.name.endsWith('_stairs')
      ? ['shape', 'half', 'facing']
      : material.name.endsWith('_slab')
        ? ['type']
        : material.properties.facing
          ? ['facing']
          : [];
    for (const property of visualProperties) {
      const options = material.properties[property];
      if (!options) continue;
      const group = document.createElement('fieldset');
      group.className = 'material-variants';
      const legend = document.createElement('legend');
      legend.textContent = names[property] ?? property;
      group.append(legend);
      for (const value of options) {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.variantProperty = property;
        button.dataset.variantValue = value;
        button.setAttribute('aria-pressed', String(this.state.properties[property] === value));
        button.title = `${names[property] ?? property}：${values[value] ?? value}`;
        if (property !== 'facing' && material.support.status === 'static') {
          const image = document.createElement('img');
          image.alt = '';
          button.append(image);
          showImage(image, {
            name: this.state.name,
            properties: { ...this.state.properties, [property]: value },
          });
        }
        button.append(values[value] ?? value);
        button.onclick = () => this.choose(property, value);
        group.append(button);
      }
      this.container.append(group);
    }

    const advanced = document.createElement('details');
    advanced.className = 'material-advanced';
    advanced.open = this.advancedOpen;
    advanced.ontoggle = () => {
      this.advancedOpen = advanced.open;
    };
    const summary = document.createElement('summary');
    summary.textContent = '高级属性';
    advanced.append(summary);
    for (const [name, options] of Object.entries(material.properties)) {
      const label = document.createElement('label');
      label.textContent = names[name] ?? name;
      label.title = name;
      const select = document.createElement('select');
      select.dataset.property = name;
      select.setAttribute('aria-label', names[name] ?? name);
      select.replaceChildren(...options.map((value) => new Option(values[value] ?? value, value)));
      select.value = this.state.properties[name];
      select.onchange = () => this.choose(name, select.value);
      label.append(select);
      advanced.append(label);
    }
    this.container.append(advanced);
  }
}
