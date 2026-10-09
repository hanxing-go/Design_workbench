import * as THREE from 'three';
import type { Atlas, Painting } from './types';

export function clearPaintings(group: THREE.Group) {
  for (const object of [...group.children]) {
    group.remove(object);
    if (object instanceof THREE.Mesh) object.geometry.dispose();
  }
}

export function updatePaintings(
  group: THREE.Group,
  paintings: Painting[],
  atlas: Atlas,
  material: THREE.Material,
) {
  clearPaintings(group);
  for (const painting of paintings) {
    const rect = atlas.uv[painting.texture];
    if (!rect) continue;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(painting.vertices, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(Array(12).fill(1), 3));
    geometry.setAttribute(
      'uv',
      new THREE.Float32BufferAttribute(
        [0, 1, 1, 1, 1, 0, 0, 0].map((v, i) =>
          i % 2
            ? 1 - (rect[1] + (1 - v) * rect[3]) / atlas.height
            : (rect[0] + v * rect[2]) / atlas.width,
        ),
        2,
      ),
    );
    geometry.setIndex([0, 1, 2, 0, 2, 3]);
    geometry.computeVertexNormals();
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData.painting = painting;
    group.add(mesh);
  }
}

export function paintingAt(object: THREE.Object3D): Painting | undefined {
  return object.userData.painting as Painting | undefined;
}

export function slicePaintings(group: THREE.Group, layer: number) {
  for (const mesh of group.children) {
    const painting = paintingAt(mesh);
    if (painting)
      mesh.visible = Math.max(...painting.vertices.filter((_, i) => i % 3 === 1)) <= layer + 1;
  }
}
