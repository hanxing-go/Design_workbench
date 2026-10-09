import * as THREE from 'three';
import type { Model, Point, RenderCell } from './types';

export function addSignText(group: THREE.Group, model: Model, cell: RenderCell) {
  const dye: Record<string, string> = {
    black: '#000000',
    white: '#f9fffe',
    orange: '#f9801d',
    magenta: '#c74ebd',
    light_blue: '#3ab3da',
    yellow: '#fed83d',
    lime: '#80c71f',
    pink: '#f38baa',
    gray: '#474f52',
    light_gray: '#9d9d97',
    cyan: '#169c9c',
    purple: '#8932b8',
    blue: '#3c44aa',
    brown: '#835432',
    green: '#5e7c16',
    red: '#b02e26',
  };
  for (const [side, text] of (model.texts ?? []).entries()) {
    const plane = model.text_planes?.[side];
    if (!plane || !text.lines.some(Boolean)) continue;
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = dye[text.color] ?? '#000000';
    if (text.glowing) {
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 3;
    }
    ctx.font = '32px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    text.lines.slice(0, 4).forEach((line, i) => ctx.fillText(line, 256, 44 + i * 55, 460));
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const geometry = new THREE.BufferGeometry();
    const points = [0, 1, 2, 3].map(
      (i) => new THREE.Vector3(...(plane.slice(i * 3, i * 3 + 3) as Point)),
    );
    const normal = points[1]
      .clone()
      .sub(points[0])
      .cross(points[2].clone().sub(points[0]))
      .normalize();
    geometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(
        points.flatMap((p) => p.addScaledVector(normal, 0.002).toArray()),
        3,
      ),
    );
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute([1, 1, 0, 1, 0, 0, 1, 0], 2));
    geometry.setIndex([0, 1, 2, 0, 2, 3]);
    const mesh = new THREE.Mesh(
      geometry,
      new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide,
      }),
    );
    mesh.position.set(cell[0], cell[1], cell[2]);
    mesh.userData.signText = true;
    mesh.raycast = () => {};
    group.add(mesh);
  }
}

export function disposeChunk(group: THREE.Group) {
  group.traverse((object) => {
    if (object instanceof THREE.InstancedMesh) object.dispose();
    if (object instanceof THREE.Mesh && object.userData.signText) {
      object.geometry.dispose();
      const material = object.material as THREE.MeshBasicMaterial;
      material.map?.dispose();
      material.dispose();
    }
  });
}
