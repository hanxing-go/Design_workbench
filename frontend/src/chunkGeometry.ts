import * as THREE from 'three';
import type { RenderCell } from './types';

export interface GeometryPart {
  geometry: THREE.BufferGeometry;
  cell: RenderCell;
}

// Every segment retains its owner. Geometry batching must not erase block identity.
export function mergedChunk(
  parts: GeometryPart[],
  material: THREE.Material | THREE.Material[],
): THREE.Mesh {
  const vertices = parts.reduce((sum, part) => sum + part.geometry.attributes.position.count, 0);
  const positions = new Float32Array(vertices * 3);
  const normals = new Float32Array(vertices * 3);
  const colors = new Float32Array(vertices * 3);
  const uvs = new Float32Array(vertices * 2);
  const triangleEnds = new Uint32Array(parts.length);
  let offset = 0;
  for (const [index, { geometry, cell }] of parts.entries()) {
    const p = geometry.attributes.position.array;
    const n = geometry.attributes.normal.array;
    const c = geometry.attributes.color.array;
    const uv = geometry.attributes.uv.array;
    for (let i = 0; i < p.length; i += 3) {
      positions[offset * 3 + i] = p[i] + cell[0];
      positions[offset * 3 + i + 1] = p[i + 1] + cell[1];
      positions[offset * 3 + i + 2] = p[i + 2] + cell[2];
    }
    normals.set(n, offset * 3);
    colors.set(c, offset * 3);
    uvs.set(uv, offset * 2);
    offset += geometry.attributes.position.count;
    triangleEnds[index] = offset / 3;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData.chunkGeometry = true;
  mesh.userData.cells = parts.map((part) => part.cell);
  mesh.userData.triangleEnds = triangleEnds;
  return mesh;
}

export function triangleOwner(mesh: THREE.Object3D, triangle: number): RenderCell | undefined {
  const ends = mesh.userData.triangleEnds as Uint32Array | undefined;
  if (!ends) return undefined;
  if (mesh instanceof THREE.Mesh && mesh.geometry.index) {
    triangle = mesh.geometry.index.array[triangle * 3] / 3;
  }
  let low = 0;
  let high = ends.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (triangle < ends[middle]) high = middle;
    else low = middle + 1;
  }
  return mesh.userData.cells[low];
}
