export type Point = [number, number, number];
export interface State {
  name: string;
  properties: Record<string, string>;
}
export interface Support {
  status: 'static' | 'special' | 'invisible' | 'missing';
  reason: string;
}
export interface Material extends Support {
  display_name: string;
  chinese_name: string;
  name: string;
  default_state: State;
  properties: Record<string, string[]>;
  support: Support;
  category: string;
}
export interface Face {
  vertices: number[];
  uv: number[];
  texture: string;
  tint: boolean;
  color?: string;
  cull: Point | null;
}
export interface Model extends State, Support {
  faces: Face[];
  text_planes?: number[][];
  texts?: { lines: string[]; color: string; glowing: boolean }[];
  opaque_cube: boolean;
  render_layer?: 'opaque' | 'cutout' | 'translucent' | 'emissive';
}
export interface Atlas {
  width: number;
  height: number;
  uv: Record<string, number[]>;
}
export type RenderCell = [number, number, number, string, string, boolean];
export interface Summary {
  id: string;
  name: string;
  revision: number;
  blocks: number;
  groups: Record<string, number>;
  occupied_bounds: { low: Point; high: Point } | null;
  undo_available: number;
  redo_available: number;
}
export interface Painting {
  id: string;
  anchor: Point;
  facing: string;
  variant: string;
  protected: boolean;
  texture: string;
  vertices: number[];
}
export interface Packet {
  paintings?: Painting[];
  revision: number;
  summary: Summary;
  chunks: Record<string, RenderCell[]>;
  models: Record<string, Model>;
  chunk_versions: Record<string, string>;
  removed_chunks: string[];
  atlas: Atlas;
  warnings: (Support & { name: string; count: number })[];
  resource_hash: string;
}
export interface Selection {
  low: Point;
  high: Point;
}
