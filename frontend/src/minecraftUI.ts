import './minecraftUI.css';

export function initMinecraftUI() {
  const root = document.getElementById('app')!;
  const pickaxe = new Image();
  pickaxe.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 32;
    const ctx = canvas.getContext('2d')!;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(pickaxe, 0, 0, 32, 32);
    root.style.setProperty('--mc-cursor', `url("${canvas.toDataURL()}") 26 5, auto`);
  };
  pickaxe.src = '/api/ui/sprites/diamond_pickaxe.png';
}
