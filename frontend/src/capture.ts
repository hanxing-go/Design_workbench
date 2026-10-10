import { Viewer } from './viewer';
import type { Packet, Point } from './types';

interface CaptureView {
  name: 'front' | 'side' | 'back' | 'top' | 'iso' | 'custom';
  layer: number | null;
  bounds: { low: Point; high: Point } | null;
  camera: { position: Point; target: Point; fov: number } | null;
}

declare global {
  interface Window {
    captureReady: boolean;
    captureError: string | null;
    captureView: (view: CaptureView) => Promise<unknown>;
  }
}

window.captureReady = false;
window.captureError = null;
const viewer = new Viewer(document.getElementById('stage')!);
viewer.controls.enabled = false;
let packet: Packet;

window.captureView = async (view) => {
  viewer.setLayer(view.layer ?? Infinity);
  const bounds = view.bounds ??
    packet.summary.occupied_bounds ?? { low: [0, 0, 0], high: [0, 0, 0] };
  viewer.camera.fov = 40;
  viewer.camera.updateProjectionMatrix();
  viewer.fit(bounds);
  const diameter = Math.hypot(...bounds.high.map((value, index) => value + 1 - bounds.low[index]));
  const halfAngle = Math.min(Math.PI / 9, Math.atan(Math.tan(Math.PI / 9) * viewer.camera.aspect));
  const direction = viewer.camera.position.clone().sub(viewer.controls.target).normalize();
  viewer.camera.position
    .copy(viewer.controls.target)
    .add(direction.multiplyScalar((diameter / 2 / Math.sin(halfAngle)) * 1.1));
  if (view.camera) {
    viewer.camera.position.set(...view.camera.position);
    viewer.controls.target.set(...view.camera.target);
    viewer.camera.fov = view.camera.fov;
    viewer.camera.updateProjectionMatrix();
    viewer.camera.lookAt(viewer.controls.target);
  } else if (view.name === 'back') {
    viewer.view('front');
    const offset = viewer.camera.position.clone().sub(viewer.controls.target);
    offset.z *= -1;
    viewer.camera.position.copy(viewer.controls.target).add(offset);
    viewer.camera.lookAt(viewer.controls.target);
  } else {
    viewer.view(view.name === 'custom' ? 'iso' : view.name);
  }
  await viewer.whenReady();
  viewer.drawNow();
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  viewer.drawNow();
  return {
    name: view.name,
    layer: view.layer,
    camera: {
      position: viewer.camera.position.toArray(),
      target: viewer.controls.target.toArray(),
      fov: viewer.camera.fov,
      near: viewer.camera.near,
      far: viewer.camera.far,
    },
    width: viewer.renderer.domElement.width,
    height: viewer.renderer.domElement.height,
    snapshot_cells: viewer.occupied().size,
    visible_cells: [...viewer.occupied().values()].filter(
      (cell) => cell[1] <= (view.layer ?? Infinity),
    ).length,
    revision: packet.revision,
  };
};

async function initialize() {
  await viewer.initializeTexture();
  const response = await fetch('/api/snapshot');
  if (!response.ok) throw new Error(`Snapshot HTTP ${response.status}`);
  packet = (await response.json()) as Packet;
  viewer.update(packet);
  await viewer.whenReady();
  viewer.drawNow();
  window.captureReady = true;
}
void initialize().catch((error: unknown) => {
  window.captureError = error instanceof Error ? error.message : String(error);
});
