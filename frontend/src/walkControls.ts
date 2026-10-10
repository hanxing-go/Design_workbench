import * as THREE from 'three';
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const movementKeys = new Set([
  'KeyW',
  'KeyA',
  'KeyS',
  'KeyD',
  'Space',
  'ShiftLeft',
  'ShiftRight',
  'ControlLeft',
  'ControlRight',
]);

export function typing(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    !!target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')
  );
}

/** Browser-only flying camera. Scene edits still belong to the application service. */
export class WalkControls {
  active = false;
  readonly eyeHeight = 1.62;
  onChange: () => void = () => {};
  onError: (message: string) => void = () => {};
  private saved: {
    position: THREE.Vector3;
    target: THREE.Vector3;
    rotation: THREE.Quaternion;
    fov: number;
    far: number;
    zoom: number;
    enabled: boolean;
  } | null = null;
  private keys = new Set<string>();
  private rotation = new THREE.Euler(0, 0, 0, 'YXZ');
  private frame = 0;
  private lastTime = 0;

  constructor(
    private camera: THREE.PerspectiveCamera,
    private orbit: OrbitControls,
    readonly canvas: HTMLCanvasElement,
    private draw: () => void,
  ) {
    document.addEventListener('pointerlockchange', () => {
      if (!this.active && this.locked) document.exitPointerLock();
      if (this.active && this.locked) {
        canvas.focus();
        if (!this.frame) {
          this.lastTime = performance.now();
          this.frame = requestAnimationFrame(this.tick);
        }
      } else {
        this.resetMotion();
      }
      this.onChange();
    });
    document.addEventListener('mousemove', (event) => {
      if (!this.active || !this.locked) return;
      this.rotation.y -= event.movementX * 0.002;
      this.rotation.x = THREE.MathUtils.clamp(
        this.rotation.x - event.movementY * 0.002,
        -Math.PI / 2,
        Math.PI / 2,
      );
      camera.quaternion.setFromEuler(this.rotation);
      this.draw();
    });
    document.addEventListener(
      'keydown',
      (event) => {
        if (
          !this.active ||
          event.isComposing ||
          typing(event.target) ||
          document.querySelector('dialog[open]')
        )
          return;
        if (event.code === 'Escape' && this.locked) {
          event.preventDefault();
          if (this.locked) document.exitPointerLock();
          this.resetMotion();
        } else if (this.locked && movementKeys.has(event.code)) {
          event.preventDefault();
          this.keys.add(event.code);
          if (!this.frame) {
            this.lastTime = performance.now();
            this.frame = requestAnimationFrame(this.tick);
          }
        }
      },
      true,
    );
    document.addEventListener('keyup', (event) => this.keys.delete(event.code));
    window.addEventListener('blur', () => this.resetMotion());
    window.addEventListener('focus', () => {
      if (this.active && this.locked && !this.frame) {
        this.lastTime = performance.now();
        this.frame = requestAnimationFrame(this.tick);
      }
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) this.resetMotion();
    });
    canvas.tabIndex = 0;
  }

  get locked(): boolean {
    return document.pointerLockElement === this.canvas;
  }

  enter(floorY = 0) {
    if (this.active) return;
    this.saved = {
      position: this.camera.position.clone(),
      target: this.orbit.target.clone(),
      rotation: this.camera.quaternion.clone(),
      fov: this.camera.fov,
      far: this.camera.far,
      zoom: this.camera.zoom,
      enabled: this.orbit.enabled,
    };
    this.active = true;
    this.orbit.enabled = false;
    this.rotation.setFromQuaternion(this.camera.quaternion, 'YXZ');
    this.rotation.x = 0;
    this.rotation.z = 0;
    this.camera.position.y = floorY + this.eyeHeight;
    this.camera.quaternion.setFromEuler(this.rotation);
    this.camera.fov = 70;
    this.camera.zoom = 1;
    this.camera.updateProjectionMatrix();
    this.draw();
    this.onChange();
    void this.lock();
  }

  async lock() {
    if (!this.active || this.locked) return;
    try {
      await this.canvas.requestPointerLock();
    } catch {
      if (this.active) {
        this.onError('无法锁定指针，请使用桌面 Chrome，或点击“继续编辑”重试。');
        this.onChange();
      }
    }
  }

  exit() {
    if (!this.active || !this.saved) return;
    this.active = false;
    if (this.locked) document.exitPointerLock();
    this.resetMotion();
    const saved = this.saved;
    this.camera.position.copy(saved.position);
    this.orbit.target.copy(saved.target);
    this.orbit.enabled = saved.enabled;
    this.camera.fov = saved.fov;
    this.camera.far = saved.far;
    this.camera.zoom = saved.zoom;
    this.camera.updateProjectionMatrix();
    this.orbit.update();
    this.camera.quaternion.copy(saved.rotation);
    this.saved = null;
    this.draw();
    this.onChange();
  }

  private resetMotion() {
    this.keys.clear();
    cancelAnimationFrame(this.frame);
    this.frame = 0;
    this.lastTime = 0;
  }

  private tick = (time: number) => {
    this.frame = 0;
    if (!this.active || !this.locked || document.hidden || !document.hasFocus()) return;
    const dt = Math.min(Math.max((time - this.lastTime) / 1000, 0), 0.05);
    this.lastTime = time;
    const right = Number(this.keys.has('KeyD')) - Number(this.keys.has('KeyA'));
    const forward = Number(this.keys.has('KeyW')) - Number(this.keys.has('KeyS'));
    const vertical =
      Number(this.keys.has('Space')) -
      Number(this.keys.has('ShiftLeft') || this.keys.has('ShiftRight'));
    // Yaw remains defined even when pitch is exactly vertical.
    const yaw = this.rotation.y;
    const direction = new THREE.Vector3(
      right * Math.cos(yaw) - forward * Math.sin(yaw),
      vertical,
      -right * Math.sin(yaw) - forward * Math.cos(yaw),
    );
    if (direction.lengthSq()) {
      const speed = this.keys.has('ControlLeft') || this.keys.has('ControlRight') ? 16 : 8;
      this.camera.position.addScaledVector(direction.normalize(), speed * dt);
      this.draw();
    }
    this.frame = requestAnimationFrame(this.tick);
  };
}
