const pixel = (body: string, viewBox = '0 0 32 36') =>
  `<svg viewBox="${viewBox}" fill="none" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">${body}</svg>`;
const line = (body: string) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;

const vanillaSprites: Record<string, string> = {
  diamond: 'diamond',
  emerald: 'emerald',
  pickaxe: 'iron_pickaxe',
  book: 'book',
  torch: 'torch',
};

export const homeIcons: Record<string, string> = {
  emerald: pixel(
    '<path d="M10 2h12v3h4v4h3v14h-3v4h-4v3H10v-3H6v-4H3V9h3V5h4Z" fill="#153e28"/><path d="M11 4h10v3h4v4h2v10h-4v5h-3v2h-9v-3H7v-4H5V10h3V7h3Z" fill="#4faa65"/><path d="M11 5h9v3h-9ZM8 8h4v12H8Zm4 4h8v12h-8Z" fill="#a6e09a"/><path d="M21 8h3v13h-4v5h-8v-3h8v-5h1Z" fill="#2a7d4a"/><path d="M11 6h7v2h-7Zm-2 4h2v6H9Z" fill="#e3f6bf"/>',
    '0 0 32 32',
  ),
  diamond: pixel(
    '<path d="M6 1h4v1h2v2h2v3h1v5h-2v2h-3v1H6v-1H3v-2H2V7h1V4h1V2h2Z" fill="#155f62"/><path d="M6 2h4v1h2v2h1v3h1v4h-2v1H5v-1H3V7h1V4h2Z" fill="#26bdb2"/><path d="M6 2h3v1h2v2H6ZM4 5h2v5H4Zm2 0h5v4H6Z" fill="#a9f3e6"/><path d="M6 4h3v1H6Zm-1 3h2v2H5Z" fill="#effff7"/><path d="M6 10h5v2H5v-1h1Zm4-4h2v4h-2Z" fill="#169f99"/><path d="M5 13h6v1H5Z" fill="#59daca"/>',
    '0 0 16 16',
  ),
  github: line(
    '<path d="M9 19c-4 1-4-2-6-2m12 5v-4a3.5 3.5 0 0 0-1-3c3-.3 6-1.5 6-6a4.7 4.7 0 0 0-1-3 4.5 4.5 0 0 0 0-3s-1 0-3 1a12 12 0 0 0-8 0C6 3 5 3 5 3a4.5 4.5 0 0 0 0 3 4.7 4.7 0 0 0-1 3c0 4.5 3 5.7 6 6a3.5 3.5 0 0 0-1 3v4"/>',
  ),
  star: line('<path d="m12 3 2.8 5.6 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.5l6.2-.9Z"/>'),
  code: line('<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/>'),
  chat: line('<path d="M21 4H3v13h5v4l6-4h7ZM7 8h10M7 12h7"/>'),
  qr: line(
    '<path d="M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h3v3h4m-7 0v4h7v-2M6 6h1m10 0h1M6 17h1"/>',
  ),
  grass: pixel(
    `<path d="M16 1 31 9v18l-15 8L1 27V9Z" fill="#10150d"/><path d="m16 3 13 7-13 7L3 10Z" fill="#8cb859"/><path d="m3 12 12 7v13L3 25Z" fill="#795135"/><path d="m17 19 12-7v13l-12 7Z" fill="#523a2b"/><path d="m3 12 12 7v5l-4-2v-3l-4-2v3l-4-2Z" fill="#669343"/><path d="m17 19 12-7v5l-4 2v3l-4 2v-3l-4 2Z" fill="#44682e"/><path d="m9 8 5-3 4 2-5 3Z" fill="#b1cd7f"/><path d="m19 10 4-2 4 2-4 2Z" fill="#659746"/><path d="m6 23 3 2v3l-3-2Zm5 3 2 1v3l-2-1Z" fill="#aa7950"/><path d="m20 26 3-2v3l-3 2Z" fill="#78543a"/>`,
  ),
  pickaxe: pixel(
    `<path d="M4 26h4v-4h4v-4h4v-4h4v-4h4v8h4V6H16v4h6l-6 4h-4v4H8v4H4Z" fill="#384b2a"/><path d="M3 24h4v-4h4v-4h4v-4h4v4h-4v4h-4v4H7v4H3Z" fill="#c6aa78"/><path d="M12 5h12v4h4v12h-4V10H12Z" fill="#b5e88c"/><path d="M12 5h12v2H12Z" fill="#e3f7c7"/>`,
    '0 0 32 32',
  ),
  crafting: pixel(
    `<path d="m16 1 15 8v18l-15 8L1 27V9Z" fill="#18150e"/><path d="m16 3 13 7-13 7L3 10Z" fill="#c59a62"/><path d="m3 12 12 7v13L3 25Z" fill="#966337"/><path d="m17 19 12-7v13l-12 7Z" fill="#694326"/><path d="m7 10 9-5 9 5-9 5Z" fill="#69482b"/><path d="m9 10 7-4 7 4-7 4Z" fill="#bb8e57"/><path d="m12 8 7 4m-3-6 7 4m-4-2-7 4m4-6-7 4" stroke="#69482b" stroke-width="1"/><path d="m5 16 8 4v3l-8-4Z" fill="#c7965a"/><path d="m6 19 2 1v6l-2-1m4-3 2 1v5l-2-1" fill="#553820"/><path d="m20 21 6-3v3l-6 3Zm2 4 3-2v4l-3 2Z" fill="#b17a43"/>`,
  ),
  chest: pixel(
    `<path d="m16 3 15 7v17l-15 7L1 27V10Z" fill="#211b11"/><path d="m16 5 13 6-13 6L3 11Z" fill="#c49a43"/><path d="m3 13 12 6v12L3 25Z" fill="#ad792c"/><path d="m17 19 12-6v12l-12 6Z" fill="#79501f"/><path d="m3 19 12 6m2 0 12-6" stroke="#47331e" stroke-width="2"/><path d="m6 12 10 5 10-5M5 15v9m22-9v9" stroke="#e0ac49" stroke-width="1.5"/><path d="m7 18 5 3v7l-5-3Z" fill="#ead9a2"/><path d="m9 22 2 1v3l-2-1Z" fill="#716541"/>`,
  ),
  cabin: pixel(
    `<path d="m16 2 15 14h-4v15l-11 4L4 31V16H0Z" fill="#171a14"/><path d="m16 5 12 11-12 4L3 16Z" fill="#6b8e4f"/><path d="m16 8 8 8-8 3-9-3Z" fill="#90ad65"/><path d="m5 18 10 4v10L5 29Z" fill="#c9b483"/><path d="m17 22 9-4v11l-9 3Z" fill="#89734e"/><path d="m8 22 4 2v5l-4-2Z" fill="#ecbd64"/><path d="m20 22 4-2v5l-4 2Z" fill="#daa555"/><path d="m2 16 14 5 14-5M5 18v11m11-8v13m10-16v11" stroke="#51452c" stroke-width="2"/>`,
  ),
  torch: pixel(
    `<path d="M12 13h8v6h-8z" fill="#d7a148"/><path d="M14 19h4v12h-4z" fill="#87643b"/><path d="M14 2h4v4h4v9H10V8h4Z" fill="#e8a83c"/><path d="M14 6h4v8h-4z" fill="#ffe4a0"/><path d="M14 21h2v8h-2z" fill="#c79556"/>`,
    '0 0 32 32',
  ),
  book: pixel(
    `<path d="m14 3 15 7v19l-13 5L2 27V8Z" fill="#231e18"/><path d="m14 5 12 6-10 4L5 9Z" fill="#dbd1ab"/><path d="m5 12 10 5v14L5 26Z" fill="#6c914a"/><path d="m17 17 9-4v14l-9 4Z" fill="#3d6231"/><path d="m8 15 4 2v10l-4-2Z" fill="#a5be6f"/><path d="m19 19 3-1v7l-3 1Z" fill="#d3a851"/>`,
  ),
  creeper: pixel(
    `<path fill="#6d8459" d="M2 2h12v12H2Z"/><path fill="#20251c" d="M4 5h3v3H4Zm5 0h3v3H9ZM7 8h2v4H7ZM5 9h2v4H5Zm4 0h2v4H9Z"/>`,
    '0 0 16 16',
  ),
  import: line('<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>'),
  cube: line('<path d="m12 3 9 5v9l-9 5-9-5V8Zm0 10 9-5m-9 5L3 8m9 5v9"/>'),
  layers: line('<path d="m12 3 9 5-9 5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>'),
  blueprint: line('<path d="M5 3h12l3 3v15H5Zm12 0v4h3M8 11h9M8 15h6M8 7h5"/>'),
  replay: line('<path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/>'),
  next: line('<path d="m9 5 7 7-7 7"/>'),
  pause: line('<path d="M8 5v14M16 5v14" stroke-width="3"/>'),
  play: line('<path d="m8 5 11 7-11 7Z" fill="currentColor" stroke="none"/>'),
  search: line('<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>'),
  list: line('<path d="M9 6h12M9 12h12M9 18h12M3 6h2M3 12h2M3 18h2"/>'),
  grid: line('<path d="M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h7v7h-7Z"/>'),
};

export function hydrateHomeIcons(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>('[data-icon]').forEach((element) => {
    element.innerHTML = homeIcons[element.dataset.icon!] ?? '';
    const sprite = vanillaSprites[element.dataset.icon!];
    if (!sprite) return;
    const image = document.createElement('img');
    image.alt = '';
    image.className = 'vanilla-sprite';
    image.decoding = 'async';
    image.hidden = true;
    image.onload = () => {
      element.querySelector('svg')?.remove();
      image.hidden = false;
    };
    image.onerror = () => image.remove();
    image.src = `/api/ui/sprites/${sprite}.png`;
    element.append(image);
  });
}
