import * as THREE from 'three';
import { mergedChunk, type GeometryPart } from './chunkGeometry';

interface Segment {
  start: number;
  end: number;
  center: THREE.Vector3;
  radius: number;
  depth: number;
  order: number;
  material: number;
  pickable: boolean;
}

export interface TextPart extends GeometryPart {
  material: THREE.Material;
}

/** A globally sorted index buffer preserves block order without thousands of draw calls. */
export class Transparency {
  mesh: THREE.Mesh;
  private segments: Segment[] = [];
  private sorted: Segment[] = [];
  private lastCamera = new Float64Array(16).fill(NaN);
  private projection = new THREE.Matrix4();
  private frustum = new THREE.Frustum();
  private sphere = new THREE.Sphere();
  private projected = new THREE.Vector3();
  private cameraPosition = new THREE.Vector3();
  private textMaterials: THREE.Material[] = [];
  private probe = new THREE.Mesh(
    new THREE.BufferGeometry(),
    new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }),
  );

  constructor(parts: GeometryPart[], material: THREE.Material, texts: TextPart[] = []) {
    const all = [...parts, ...texts];
    this.textMaterials = texts.map((part) => part.material);
    this.mesh = mergedChunk(all, [material, ...this.textMaterials]);
    let start = 0;
    for (const [order, { cell, geometry }] of all.entries()) {
      if (!geometry.boundingSphere) geometry.computeBoundingSphere();
      const bound = geometry.boundingSphere!;
      const end = start + geometry.attributes.position.count;
      this.segments.push({
        start,
        end,
        center: bound.center.clone().add(new THREE.Vector3(cell[0], cell[1], cell[2])),
        radius: bound.radius,
        depth: 0,
        order,
        material: order < parts.length ? 0 : order - parts.length + 1,
        pickable: order < parts.length,
      });
      start = end;
    }
    this.mesh.geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(start), 1));
    this.mesh.geometry.index!.setUsage(THREE.DynamicDrawUsage);
    this.mesh.geometry.setDrawRange(0, 0);
    this.probe.geometry.attributes = this.mesh.geometry.attributes;
    this.mesh.raycast = (raycaster, hits) => {
      const origin = raycaster.ray.origin;
      for (const segment of this.segments) {
        if (!segment.pickable) continue;
        this.sphere.center.copy(segment.center);
        this.sphere.radius = segment.radius;
        if (!raycaster.ray.intersectsSphere(this.sphere)) continue;
        if (origin.distanceTo(segment.center) - segment.radius > raycaster.far) continue;
        this.probe.geometry.boundingSphere = this.sphere;
        this.probe.geometry.setDrawRange(segment.start, segment.end - segment.start);
        const found: THREE.Intersection[] = [];
        this.probe.raycast(raycaster, found);
        for (const hit of found) {
          hit.object = this.mesh;
          hit.instanceId = segment.order;
          hits.push(hit);
        }
      }
    };
  }

  sort(camera: THREE.Camera) {
    this.projection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    const elements = this.projection.elements;
    if (elements.every((value, index) => value === this.lastCamera[index])) return;
    this.lastCamera.set(elements);
    this.frustum.setFromProjectionMatrix(this.projection);
    this.cameraPosition.setFromMatrixPosition(camera.matrixWorld);
    this.sorted.length = 0;
    for (const segment of this.segments) {
      this.sphere.center.copy(segment.center);
      this.sphere.radius = segment.radius;
      if (!this.frustum.intersectsSphere(this.sphere)) continue;
      segment.depth = this.projected.copy(segment.center).applyMatrix4(this.projection).z;
      this.sorted.push(segment);
    }
    this.sorted.sort((a, b) => b.depth - a.depth || a.order - b.order);
    const geometry = this.mesh.geometry;
    const positions = geometry.attributes.position.array;
    const normals = geometry.attributes.normal.array;
    const indices = geometry.index!.array;
    geometry.clearGroups();
    let offset = 0;
    let groupStart = 0;
    let material = -1;
    const eye = this.cameraPosition;
    for (const segment of this.sorted) {
      if (segment.material !== material) {
        if (material !== -1) geometry.addGroup(groupStart, offset - groupStart, material);
        groupStart = offset;
        material = segment.material;
      }
      // Match the old per-block BackSide then FrontSide draws in one DoubleSide draw.
      for (const front of [false, true]) {
        for (let i = segment.start; i < segment.end; i += 3) {
          const j = i * 3;
          const facing =
            normals[j] * (eye.x - positions[j]) +
              normals[j + 1] * (eye.y - positions[j + 1]) +
              normals[j + 2] * (eye.z - positions[j + 2]) >=
            0;
          if (facing !== front) continue;
          indices[offset++] = i;
          indices[offset++] = i + 1;
          indices[offset++] = i + 2;
        }
      }
    }
    if (material !== -1) geometry.addGroup(groupStart, offset - groupStart, material);
    geometry.setDrawRange(0, offset);
    geometry.index!.needsUpdate = true;
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.probe.geometry.dispose();
    (this.probe.material as THREE.Material).dispose();
    for (const material of this.textMaterials) material.dispose();
  }
}
