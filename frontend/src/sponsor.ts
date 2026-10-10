import './style.css';
import './home.css';
import './sponsor.css';
import sponsor from './sponsor.html?raw';
import { hydrateHomeIcons } from './homeIcons';
import { sponsorConfig } from './sponsor.config';

const root = document.querySelector<HTMLDivElement>('#app')!;
root.className = 'home-mode sponsor-mode';
root.innerHTML = sponsor;
document.title = '赞助支持 · Design Workbench';
document
  .querySelector('meta[name="description"]')
  ?.setAttribute(
    'content',
    '支持 Design Workbench 开源 Minecraft 建筑设计工作台，让创造继续生长。',
  );

const repository = sponsorConfig.repository.replace(/\/$/, '');
document.querySelectorAll<HTMLAnchorElement>('[data-repository-link]').forEach((link) => {
  link.href = repository;
});
document.querySelectorAll<HTMLAnchorElement>('[data-issues-link]').forEach((link) => {
  link.href = `${repository}/issues`;
});
document.querySelectorAll<HTMLAnchorElement>('[data-contribute-link]').forEach((link) => {
  link.href = `${repository}/blob/main/CONTRIBUTING.md`;
});
document.querySelectorAll<HTMLAnchorElement>('[data-contact-link]').forEach((link) => {
  link.href = `${repository}/issues/new?title=${encodeURIComponent('赞助合作')}`;
});

const qrDialog = document.getElementById('sponsor-qr-dialog') as HTMLDialogElement;
const channels = document.getElementById('sponsor-channels')!;
for (const channel of sponsorConfig.channels) {
  let url: URL | null = null;
  if (channel.url) {
    try {
      const parsed = new URL(channel.url);
      if (parsed.protocol === 'https:') url = parsed;
    } catch {
      /* An incomplete channel stays hidden until it has a usable destination. */
    }
  }
  if (!url && !channel.qrImage) continue;
  const card = document.createElement('article');
  card.className = 'sponsor-channel';
  const icon = document.createElement('span');
  icon.className = 'sponsor-channel-icon';
  icon.dataset.icon = channel.icon;
  icon.setAttribute('aria-hidden', 'true');
  const title = document.createElement('h3');
  title.textContent = channel.name;
  const description = document.createElement('p');
  description.textContent = channel.description;
  card.append(icon, title, description);
  if (url) {
    const link = document.createElement('a');
    link.className = 'sponsor-primary';
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = `前往${channel.name}赞助 ↗`;
    card.append(link);
  } else if (channel.qrImage) {
    const button = document.createElement('button');
    button.className = 'primary';
    button.textContent = `使用${channel.name}赞助 →`;
    button.onclick = () => {
      document.getElementById('sponsor-qr-title')!.textContent = `${channel.name}扫码赞助`;
      const image = document.getElementById('sponsor-qr-image') as HTMLImageElement;
      image.src = channel.qrImage!;
      image.alt = `${channel.name}赞助收款码`;
      document.getElementById('sponsor-qr-recipient')!.textContent = channel.recipient
        ? `收款方：${channel.recipient}`
        : '';
      qrDialog.showModal();
    };
    card.append(button);
  }
  channels.append(card);
}
document.getElementById('sponsor-unconfigured')!.hidden = channels.childElementCount > 0;
document.getElementById('sponsor-qr-close')!.onclick = () => qrDialog.close();
qrDialog.addEventListener('click', (event) => {
  if (event.target !== qrDialog) return;
  const bounds = qrDialog.getBoundingClientRect();
  if (
    event.clientX < bounds.left ||
    event.clientX > bounds.right ||
    event.clientY < bounds.top ||
    event.clientY > bounds.bottom
  )
    qrDialog.close();
});
hydrateHomeIcons();
