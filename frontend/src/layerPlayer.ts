import type { Summary } from './types';
import type { Viewer } from './viewer';

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

/** Layer numbers are one-based; the renderer always receives the actual world Y. */
export class LayerPlayer {
  private low = 0;
  private high = 0;
  private available = false;
  private suspended = true;
  private timer = 0;
  private playing = false;
  private slider = el<HTMLInputElement>('layer');
  private number = el<HTMLInputElement>('layer-number');
  private play = el<HTMLButtonElement>('layer-play');
  private speed = el<HTMLSelectElement>('layer-speed');

  constructor(private viewer: Viewer) {
    this.play.onclick = () => this.toggle();
    this.slider.oninput = () => {
      const value = Number(this.slider.value);
      this.stop();
      this.seek(value);
    };
    this.number.onchange = () => {
      const value = this.number.valueAsNumber;
      this.stop();
      if (Number.isFinite(value)) this.seek(this.low + Math.round(value) - 1);
      else this.sync();
    };
    el<HTMLButtonElement>('layer-prev').onclick = () => this.step(-1);
    el<HTMLButtonElement>('layer-next').onclick = () => this.step(1);
    el<HTMLButtonElement>('layer-reset').onclick = () => {
      this.stop();
      this.viewer.setLayer(Infinity);
      this.sync();
    };
    this.speed.onchange = () => {
      if (this.playing) this.schedule();
    };
    this.sync();
  }

  update(summary: Summary) {
    const bounds = summary.occupied_bounds;
    this.available = bounds !== null;
    this.low = bounds?.low[1] ?? 0;
    this.high = bounds?.high[1] ?? 0;
    this.slider.min = String(this.low);
    this.slider.max = String(this.high);
    this.number.max = String(this.high - this.low + 1);
    if (!this.available) {
      this.stop();
      if (this.viewer.layer !== Infinity) this.viewer.setLayer(Infinity);
    } else if (
      this.viewer.layer !== Infinity &&
      (this.viewer.layer < this.low || this.viewer.layer > this.high)
    ) {
      const value = Math.max(this.low, Math.min(this.high, this.viewer.layer));
      this.viewer.setLayer(value);
    }
    this.sync();
  }

  setBusy(value: boolean) {
    this.suspended = value;
    if (value) this.stop();
    this.sync();
  }

  stop() {
    window.clearTimeout(this.timer);
    this.timer = 0;
    this.playing = false;
    this.sync();
  }

  toggle() {
    if (this.playing) {
      this.stop();
      return;
    }
    if (!this.available || this.suspended || this.low === this.high) return;
    if (this.viewer.layer >= this.high) this.seek(this.low);
    this.playing = true;
    this.sync();
    this.schedule();
  }

  step(delta: number) {
    this.stop();
    this.seek(this.current + delta);
  }

  private get current() {
    return this.viewer.layer === Infinity ? this.high : this.viewer.layer;
  }

  private seek(y: number) {
    if (!this.available || this.suspended) return;
    const value = Math.max(this.low, Math.min(this.high, Math.round(y)));
    if (this.viewer.layer !== value) this.viewer.setLayer(value);
    this.sync();
  }

  private schedule() {
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(
      () => {
        this.seek(this.current + 1);
        if (this.current >= this.high) this.stop();
        else this.schedule();
      },
      600 / Number(this.speed.value),
    );
  }

  private sync() {
    const disabled = !this.available || this.suspended;
    this.slider.value = String(this.current);
    this.slider.style.setProperty(
      '--progress',
      `${this.high === this.low ? 100 : ((this.current - this.low) / (this.high - this.low)) * 100}%`,
    );
    this.slider.setAttribute(
      'aria-valuetext',
      `第 ${this.current - this.low + 1} 层，Y ${this.current}`,
    );
    this.number.value = String(this.available ? this.current - this.low + 1 : 0);
    el<HTMLElement>('layer-total').textContent = String(
      this.available ? this.high - this.low + 1 : 0,
    );
    el<HTMLElement>('layer-label').textContent = this.available
      ? `Y ${this.current}${this.viewer.layer === Infinity ? ' · 全部显示' : ' · 逐层显示'}`
      : '暂无方块';
    this.play.textContent = this.playing ? 'Ⅱ' : '▶';
    this.play.setAttribute('aria-label', this.playing ? '暂停逐层建造' : '播放逐层建造');
    this.play.setAttribute('aria-pressed', String(this.playing));
    this.play.disabled = disabled || this.low === this.high;
    this.slider.disabled = disabled || this.low === this.high;
    this.number.disabled = disabled;
    this.speed.disabled = disabled;
    el<HTMLButtonElement>('layer-prev').disabled = disabled || this.current <= this.low;
    el<HTMLButtonElement>('layer-next').disabled = disabled || this.current >= this.high;
    el<HTMLButtonElement>('layer-reset').disabled = disabled;
  }
}
