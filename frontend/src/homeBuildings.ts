export type BlockKind =
  | 'grass'
  | 'dirt'
  | 'stone'
  | 'brick'
  | 'planks'
  | 'log'
  | 'beam'
  | 'roof'
  | 'tile'
  | 'leaves'
  | 'cherry'
  | 'water'
  | 'window'
  | 'door'
  | 'door-top'
  | 'path'
  | 'flower'
  | 'stem'
  | 'lantern'
  | 'canvas'
  | 'red-wool'
  | 'copper'
  | 'crystal'
  | 'dark-stone'
  | 'rope'
  | 'wheat';

export type Block = { x: number; y: number; z: number; kind: BlockKind };
type Point = [number, number, number];
export type HomeBuildingPart = {
  origin: Point;
  motion: 'spin' | 'float';
  blocks: Block[];
};
export type HomeBuilding = {
  id: string;
  name: string;
  blocks: Block[];
  chimney?: Point;
  parts?: HomeBuildingPart[];
  framing?: { scale: number; y: number };
};

function island() {
  const blocks = new Map<string, Block>();
  const put = (x: number, y: number, z: number, kind: BlockKind) => {
    blocks.set(`${x},${y},${z}`, { x, y, z, kind });
  };
  const vacant = (x: number, y: number, z: number) => !blocks.has(`${x},${y},${z}`);
  const ground = (x: number, z: number, kind: BlockKind) => {
    if (!blocks.has(`${x},0,${z}`)) return false;
    put(x, 0, z, kind);
    return true;
  };
  const fill = (low: Point, high: Point, kind: BlockKind) => {
    for (let x = low[0]; x <= high[0]; x++)
      for (let y = low[1]; y <= high[1]; y++)
        for (let z = low[2]; z <= high[2]; z++) put(x, y, z, kind);
  };
  for (let x = -8; x <= 8; x++) {
    for (let z = -6; z <= 6; z++) {
      const distance = (x / 8.4) ** 2 + (z / 6.5) ** 2;
      const edge = 0.94 + Math.sin(x * 4.7 + z * 2.1) * 0.09;
      if (distance > edge) continue;
      put(x, 0, z, 'grass');
      for (let y = -1; y >= -5; y--) {
        if (distance < edge - (-y - 1) * 0.19) put(x, y, z, y > -3 ? 'dirt' : 'stone');
      }
    }
  }
  for (let x = -6; x <= -4; x++) {
    for (let z = 2; z <= 4; z++) {
      if ((x + 4) ** 2 / 6 + (z - 3) ** 2 / 2 < 1.3) put(x, 0, z, 'water');
    }
  }
  for (let z = 3; z <= 6; z++) {
    put(0, 0, z, 'path');
    put(1, 0, z, 'path');
  }
  put(-2, 0, 3, 'stone');
  put(-3, 0, 3, 'stone');

  const oak = (x: number, z: number, height: number, foliage: 'leaves' | 'cherry' = 'leaves') => {
    fill([x, 1, z], [x, height, z], 'log');
    for (let dx = -2; dx <= 2; dx++) {
      for (let dz = -2; dz <= 2; dz++) {
        for (let y = height - 1; y <= height + 2; y++) {
          if (vacant(x + dx, y, z + dz) && dx ** 2 + dz ** 2 + (y - height) ** 2 * 1.4 < 7.7)
            put(x + dx, y, z + dz, foliage);
        }
      }
    }
  };
  const spruce = (x: number, z: number) => {
    fill([x, 1, z], [x, 7, z], 'log');
    for (let y = 3; y <= 9; y++) {
      const radius = y >= 8 ? 0 : y % 2 ? 2 : 1;
      for (let dx = -radius; dx <= radius; dx++) {
        for (let dz = -radius; dz <= radius; dz++) {
          if (vacant(x + dx, y, z + dz) && Math.abs(dx) + Math.abs(dz) <= radius + 1)
            put(x + dx, y, z + dz, 'leaves');
        }
      }
    }
  };
  const flowers = () => {
    for (const [x, z] of [
      [-6, 1],
      [-2, 5],
      [4, 4],
      [6, 1],
      [3, 5],
      [-7, -1],
    ]) {
      if (vacant(x, 1, z) && vacant(x, 2, z) && blocks.get(`${x},0,${z}`)?.kind === 'grass') {
        put(x, 1, z, 'stem');
        put(x, 2, z, 'flower');
      }
    }
  };
  return { put, fill, ground, oak, spruce, flowers, finish: () => [...blocks.values()] };
}

function cottage(): HomeBuilding {
  const { put, fill, oak, spruce, flowers, finish } = island();
  fill([-3, 1, -3], [3, 1, 3], 'stone');
  for (let y = 2; y <= 5; y++) {
    for (let a = -3; a <= 3; a++) {
      put(a, y, -3, 'planks');
      put(a, y, 3, 'planks');
      put(-3, y, a, 'planks');
      put(3, y, a, 'planks');
    }
  }
  for (const x of [-3, 3]) {
    for (const z of [-3, 3]) fill([x, 1, z], [x, 5, z], 'log');
  }
  for (let x = -2; x <= 2; x++) {
    put(x, 5, 3, 'beam');
    put(x, 5, -3, 'beam');
  }
  fill([-2, 3, 3], [-1, 4, 3], 'window');
  fill([2, 3, 3], [2, 4, 3], 'window');
  fill([3, 3, -1], [3, 4, 1], 'window');
  put(0, 2, 3, 'door');
  put(0, 3, 3, 'door-top');
  put(0, 1, 4, 'planks');
  for (let x = -4; x <= 4; x++) {
    const height = 9 - Math.abs(x);
    for (let z = -4; z <= 4; z++) put(x, height, z, 'roof');
    for (let y = 6; y < height; y++) {
      put(x, y, 3, 'planks');
      put(x, y, -3, 'planks');
    }
  }
  fill([2, 6, -2], [2, 9, -2], 'stone');
  put(0, 7, 3, 'window');
  oak(-5, -3, 5);
  spruce(5, -2);
  flowers();
  return { id: 'cottage', name: '林间木屋', blocks: finish(), chimney: [2, 10.2, -2] };
}

function watchtower(): HomeBuilding {
  const { put, fill, oak, spruce, flowers, finish } = island();
  fill([-3, 1, -3], [3, 1, 3], 'brick');
  for (let y = 2; y <= 9; y++) {
    for (let a = -2; a <= 2; a++) {
      put(a, y, -2, 'brick');
      put(a, y, 2, 'brick');
      put(-2, y, a, 'brick');
      put(2, y, a, 'brick');
    }
    for (const x of [-2, 2]) {
      for (const z of [-2, 2]) put(x, y, z, 'stone');
    }
  }
  for (const y of [4, 7]) {
    fill([-1, y, 2], [-1, y + 1, 2], 'window');
    fill([1, y, 2], [1, y + 1, 2], 'window');
    fill([2, y, 0], [2, y + 1, 0], 'window');
    fill([0, y, -2], [0, y + 1, -2], 'window');
  }
  put(0, 2, 2, 'door');
  put(0, 3, 2, 'door-top');
  put(0, 1, 4, 'brick');
  fill([-3, 9, -3], [3, 9, 3], 'stone');
  for (let a = -3; a <= 3; a++) {
    for (const side of [-3, 3]) {
      put(a, 10, side, 'brick');
      put(side, 10, a, 'brick');
      if (Math.abs(a) === 3 || a % 2 === 0) {
        put(a, 11, side, 'brick');
        put(side, 11, a, 'brick');
      }
    }
  }
  // A low courtyard wall makes the tower feel like a tiny Minecraft outpost.
  for (let x = -6; x <= -4; x++) {
    put(x, 1, -1, 'brick');
    if (x % 2 === 0) put(x, 2, -1, 'brick');
  }
  oak(-5, -4, 3);
  spruce(5, -3);
  flowers();
  return { id: 'watchtower', name: '石砖瞭望塔', blocks: finish() };
}

function cherryGarden(): HomeBuilding {
  const { put, fill, oak, flowers, finish } = island();
  fill([-3, 1, -3], [3, 1, 3], 'planks');
  for (let y = 2; y <= 4; y++) {
    for (let a = -2; a <= 2; a++) {
      put(a, y, -2, 'planks');
      put(a, y, 2, 'planks');
      put(-2, y, a, 'planks');
      put(2, y, a, 'planks');
    }
  }
  for (const x of [-2, 2]) {
    for (const z of [-2, 2]) fill([x, 1, z], [x, 4, z], 'log');
  }
  fill([-1, 2, 2], [1, 3, 2], 'window');
  fill([2, 2, -1], [2, 3, 1], 'window');
  put(0, 2, 2, 'door');
  put(0, 3, 2, 'door-top');
  for (let x = -3; x <= 3; x++) {
    for (let z = -3; z <= 3; z++) {
      put(x, 8 - Math.max(Math.abs(x), Math.abs(z)), z, 'tile');
      if (Math.abs(x) === 3 && Math.abs(z) === 3) put(x, 6, z, 'tile');
    }
  }
  // Raised corner eaves, a ridge, and two lanterns frame the garden pavilion.
  fill([-1, 8, 0], [1, 8, 0], 'tile');
  put(0, 1, 4, 'planks');
  for (const x of [-2, 2]) {
    put(x, 1, 4, 'stone');
    put(x, 2, 4, 'lantern');
  }
  oak(-5, -3, 4, 'cherry');
  oak(5, -2, 5, 'cherry');
  flowers();
  return { id: 'cherry-garden', name: '樱花庭院', blocks: finish() };
}

function windmill(): HomeBuilding {
  const { put, fill, ground, oak, flowers, finish } = island();
  fill([-2, 1, -2], [2, 1, 2], 'brick');
  for (let y = 2; y <= 6; y++) {
    for (let a = -2; a <= 2; a++) {
      put(a, y, -2, 'canvas');
      put(a, y, 2, 'canvas');
      put(-2, y, a, 'canvas');
      put(2, y, a, 'canvas');
    }
  }
  for (const x of [-2, 2]) {
    for (const z of [-2, 2]) fill([x, 1, z], [x, 6, z], 'log');
  }
  fill([2, 3, -1], [2, 4, 0], 'window');
  put(0, 2, 2, 'door');
  put(0, 3, 2, 'door-top');
  put(0, 1, 3, 'planks');
  for (let x = -3; x <= 3; x++) {
    const height = 9 - Math.abs(x);
    for (let z = -3; z <= 3; z++) put(x, height, z, 'roof');
    for (let y = 7; y < height; y++) {
      put(x, y, -2, 'planks');
      put(x, y, 2, 'planks');
    }
  }
  for (let x = 3; x <= 6; x++) {
    for (let z = 2; z <= 4; z++) {
      if (ground(x, z, 'dirt')) put(x, 1, z, 'wheat');
    }
  }
  put(0, 6, 3, 'log');
  oak(-5, -3, 4);
  flowers();

  const sails = new Map<string, Block>();
  const sail = (x: number, y: number, kind: BlockKind) => {
    sails.set(`${x},${y}`, { x, y, z: 0, kind });
  };
  sail(0, 0, 'copper');
  for (let arm = 0; arm < 4; arm++) {
    const turn = (x: number, y: number): [number, number] =>
      arm === 0 ? [x, y] : arm === 1 ? [-y, x] : arm === 2 ? [-x, -y] : [y, -x];
    for (let length = 1; length <= 4; length++) {
      const [x, y] = turn(0, length);
      sail(x, y, 'log');
      if (length >= 2) {
        const [clothX, clothY] = turn(1, length);
        sail(clothX, clothY, 'canvas');
      }
    }
  }
  return {
    id: 'windmill',
    name: '麦田风车',
    blocks: finish(),
    parts: [{ origin: [0, 6.5, 4], motion: 'spin', blocks: [...sails.values()] }],
  };
}

function riverBridge(): HomeBuilding {
  const { put, fill, ground, oak, flowers, finish } = island();
  for (let x = -2; x <= 2; x++) {
    for (let z = -6; z <= 6; z++) ground(x, z, 'water');
  }
  for (let x = -7; x <= 7; x++) {
    const deck = 2 + Math.round(3 * Math.cos((x / 7) * (Math.PI / 2)));
    for (let z = -1; z <= 1; z++) {
      put(x, deck, z, 'planks');
      put(x, deck - 1, z, 'brick');
      if (Math.abs(x) >= 5) fill([x, 1, z], [x, deck - 2, z], 'stone');
    }
    for (const z of [-2, 2]) {
      put(x, deck, z, 'brick');
      if (x % 2 === 0) put(x, deck + 1, z, 'brick');
      if (Math.abs(x) === 4) put(x, deck + 2, z, 'lantern');
    }
  }
  put(-8, 1, 0, 'stone');
  put(8, 1, 0, 'stone');
  oak(-5, -4, 4);
  oak(5, -4, 4, 'cherry');
  flowers();
  return { id: 'river-bridge', name: '溪谷拱桥', blocks: finish() };
}

function crystalAltar(): HomeBuilding {
  const { put, fill, oak, flowers, finish } = island();
  for (let x = -4; x <= 4; x++) {
    for (let z = -4; z <= 4; z++) {
      if (x * x + z * z <= 20) put(x, 1, z, 'dark-stone');
      if (x * x + z * z <= 11) put(x, 2, z, 'brick');
    }
  }
  const crystal = (x: number, z: number, height: number) => {
    for (let y = 3; y <= height; y++) {
      const radius = y >= height - 1 ? 0 : 1;
      for (let dx = -radius; dx <= radius; dx++) {
        for (let dz = -radius; dz <= radius; dz++) {
          if (Math.abs(dx) + Math.abs(dz) <= radius) put(x + dx, y, z + dz, 'crystal');
        }
      }
    }
  };
  crystal(0, 0, 11);
  crystal(-3, 1, 7);
  crystal(3, -1, 8);
  for (const [x, z, height] of [
    [-3, -3, 4],
    [3, 3, 3],
    [-3, 3, 2],
    [3, -3, 5],
  ]) {
    fill([x, 2, z], [x, height, z], 'dark-stone');
    put(x, height + 1, z, 'lantern');
  }
  oak(-6, -3, 3);
  flowers();
  return { id: 'crystal-altar', name: '紫晶祭坛', blocks: finish() };
}

function airship(): HomeBuilding {
  const { put, fill, oak, flowers, finish } = island();
  fill([-4, 1, -2], [4, 1, 2], 'planks');
  for (const x of [-5, 5]) {
    for (const z of [-2, 2]) {
      fill([x, 1, z], [x, 2, z], 'log');
      put(x, 3, z, 'lantern');
    }
  }
  oak(-6, -4, 3);
  flowers();
  const ship = new Map<string, Block>();
  const place = (x: number, y: number, z: number, kind: BlockKind) => {
    ship.set(`${x},${y},${z}`, { x, y, z, kind });
  };
  for (let x = -7; x <= 7; x++) {
    for (let y = 8; y <= 14; y++) {
      for (let z = -3; z <= 3; z++) {
        if ((x / 7.5) ** 2 + ((y - 11) / 3.3) ** 2 + (z / 3.3) ** 2 < 1) {
          const stripe = x === -4 || x === -1 || x === 2 || x === 5;
          place(x, y, z, stripe ? 'red-wool' : 'canvas');
        }
      }
    }
  }
  for (let x = -4; x <= 4; x++) {
    const bottom = Math.abs(x) === 4 ? 5 : Math.abs(x) === 3 ? 4 : 3;
    for (let y = bottom; y <= 5; y++) {
      for (let z = -1; z <= 1; z++) place(x, y, z, y === bottom ? 'copper' : 'planks');
    }
  }
  for (let x = -2; x <= 2; x++) {
    for (const z of [-1, 1]) {
      place(x, 6, z, Math.abs(x) < 2 ? 'window' : 'log');
      place(x, 7, z, 'roof');
    }
    place(x, 7, 0, 'roof');
  }
  for (const x of [-4, 4]) {
    for (const z of [-1, 1]) {
      for (let y = 6; y <= 9; y++) {
        if (!ship.has(`${x},${y},${z}`)) place(x, y, z, 'rope');
      }
    }
  }
  for (let y = 10; y <= 13; y++) place(-7, y, 0, 'tile');
  for (let x = -8; x <= -6; x++) {
    for (let z = -2; z <= 2; z++) place(x, 10, z, 'tile');
  }
  for (const z of [-2, 2]) {
    place(3, 4, z, 'copper');
    place(4, 4, z, 'log');
    place(4, 3, z, 'canvas');
    place(4, 5, z, 'canvas');
  }
  return {
    id: 'airship',
    name: '蒸汽飞艇',
    blocks: finish(),
    parts: [{ origin: [0, 0, 0], motion: 'float', blocks: [...ship.values()] }],
    framing: { scale: 0.83, y: -0.65 },
  };
}

export const HOME_BUILDINGS: HomeBuilding[] = [
  cottage(),
  watchtower(),
  cherryGarden(),
  windmill(),
  riverBridge(),
  crystalAltar(),
  airship(),
];
