const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/homeScene-DflaHt-9.js","assets/three.module-BKyUEcGm.js"])))=>i.map(i=>d[i]);
import{_ as T}from"./main-B_wfCu5-.js";/* empty css              */import"./modulepreload-polyfill-B5Qt9EMX.js";const A=`<div class="home-topline" aria-hidden="true"></div>
<header class="home-header">
  <a class="brand home-brand" href="/" aria-label="Design Workbench 首页">
    <span class="brand-mark" data-icon="grass" aria-hidden="true"></span>
    <span><strong>Design Workbench</strong><small>MINECRAFT 建筑设计工作台</small></span>
  </a>
  <nav class="home-nav" aria-label="主导航">
    <a href="#" class="is-current" aria-current="page">首页</a>
    <a href="#designs">我的设计 <span class="nav-count" id="home-project-count">0</span></a>
    <button type="button" data-home-guide>建造指南 <span aria-hidden="true">↗</span></button>
  </nav>
  <div class="home-header-actions">
    <span class="home-version"><i></i><span id="home-version">JAVA EDITION</span></span>
    <a href="?view=workbench" class="home-workbench-link"
      >进入工作台 <span aria-hidden="true">↗</span></a
    >
  </div>
</header>
<main class="home-main">
  <section class="home-hero" aria-labelledby="home-title">
    <div class="hero-grid" aria-hidden="true"></div>
    <div class="hero-cross cross-one" aria-hidden="true">+</div>
    <div class="hero-cross cross-two" aria-hidden="true">+</div>
    <div class="hero-content">
      <div class="hero-eyebrow">
        <span class="eyebrow-pixels" aria-hidden="true">✦</span> 为每一个热爱建造的你
        <span class="eyebrow-line"></span>
      </div>
      <h1 id="home-title">
        让想象，<br /><span>方块成真<span class="title-period">.</span></span>
      </h1>
      <p class="hero-description">
        从一块木板，到一座理想之城。<br />设计、预览、自由构筑，把你的灵感带进 Minecraft。
      </p>
      <div class="hero-actions">
        <button class="primary hero-create" data-home-create>
          <span data-icon="pickaxe" aria-hidden="true"></span> 开始建造
          <span class="button-arrow" aria-hidden="true">→</span>
        </button>
        <button class="hero-import" data-home-import>
          <span data-icon="import" aria-hidden="true"></span> 导入蓝图
        </button>
      </div>
      <p class="hero-note">
        <span class="tiny-square" aria-hidden="true"></span> 本地保存 <span>·</span> 自由编辑
        <span>·</span> 属于你的创造空间
      </p>
      <div class="hero-capabilities">
        <span><span data-icon="cube" aria-hidden="true"></span> 方块级编辑</span>
        <span><span data-icon="layers" aria-hidden="true"></span> 逐层建造预览</span>
        <span><span data-icon="blueprint" aria-hidden="true"></span> .litematic 蓝图</span>
      </div>
    </div>
    <div class="hero-visual" id="home-visual">
      <div class="scene-location">
        <span class="location-dot" aria-hidden="true"></span> 主世界 <span>/ OVERWORLD</span>
      </div>
      <div
        id="home-scene"
        role="img"
        aria-label="Minecraft 浮空小岛：木屋、树木、池塘和漂浮方块。拖动可旋转，方向键可调整视角。"
        tabindex="0"
      ></div>
      <div class="scene-fallback" id="scene-fallback" hidden>
        <span data-icon="grass" aria-hidden="true"></span>
        <p>你的世界，从一个方块开始</p>
      </div>
      <div class="scene-coordinate" aria-hidden="true">
        X <span>128</span> <b>/</b> Y <span>64</span> <b>/</b> Z <span>128</span>
      </div>
      <div class="scene-bottom">
        <span class="scene-caption"
          ><span class="scene-caption-dot"></span> <span id="scene-building-name">林间木屋</span>
          <small
            ><span id="scene-building-phase">正在搭建</span> ·
            <span id="scene-building-index">01 / 07</span> · 拖动旋转</small
          ></span
        >
        <div class="scene-controls" role="group" aria-label="首页动画控制">
          <button id="scene-next" aria-label="切换下一种建筑" title="下一种建筑">
            <span data-icon="next" aria-hidden="true"></span>
          </button>
          <button id="scene-replay" aria-label="重播方块建造动画" title="重播建造动画">
            <span data-icon="replay" aria-hidden="true"></span>
          </button>
          <button id="scene-pause" aria-label="暂停首页动画" aria-pressed="false" title="暂停动画">
            <span data-icon="pause" aria-hidden="true"></span>
          </button>
        </div>
      </div>
      <span class="scene-corner corner-tl" aria-hidden="true"></span
      ><span class="scene-corner corner-tr" aria-hidden="true"></span
      ><span class="scene-corner corner-bl" aria-hidden="true"></span
      ><span class="scene-corner corner-br" aria-hidden="true"></span>
    </div>
    <div class="hero-bottom-label" aria-hidden="true">
      <span>CREATIVE MODE: ON</span><span>BUILD SOMETHING THAT MATTERS.</span
      ><span>↓ 向下探索</span>
    </div>
  </section>
  <section class="home-start" aria-labelledby="start-title">
    <div class="home-section-heading">
      <div>
        <span class="section-marker" aria-hidden="true"></span>
        <h2 id="start-title">下一次冒险，从这里开始</h2>
      </div>
      <span class="section-meta">CHOOSE YOUR NEXT STEP</span>
    </div>
    <div class="start-cards">
      <button class="start-card start-create" data-home-create>
        <span class="start-art" data-icon="crafting" aria-hidden="true"></span>
        <span class="start-card-content"
          ><strong>创造一个新世界 <span class="card-tag">NEW</span></strong
          ><span>空白画布，无限可能。从第一个方块开始。</span></span
        ><span class="start-arrow" aria-hidden="true">↗</span>
      </button>
      <button class="start-card start-import" data-home-import>
        <span class="start-art" data-icon="chest" aria-hidden="true"></span>
        <span class="start-card-content"
          ><strong>带上你的蓝图</strong><span>导入 .litematic，让已有灵感继续生长。</span></span
        ><span class="start-arrow" aria-hidden="true">↗</span>
      </button>
      <button class="start-card start-cabin" id="home-cabin">
        <span class="start-art" data-icon="cabin" aria-hidden="true"></span>
        <span class="start-card-content"
          ><strong>先搭一间小屋 <span class="card-tag tag-warm">TRY IT</span></strong
          ><span>从一份木屋起稿，熟悉你的建造工具。</span></span
        ><span class="start-arrow" aria-hidden="true">↗</span>
      </button>
    </div>
  </section>
  <section class="home-designs" id="designs" aria-labelledby="designs-title">
    <div class="home-section-heading">
      <div>
        <span class="section-marker" aria-hidden="true"></span>
        <h2 id="designs-title">我的设计</h2>
        <span class="design-count" id="design-count">0 个项目</span>
      </div>
      <div class="design-tools">
        <label class="design-search"
          ><span data-icon="search" aria-hidden="true"></span
          ><input
            id="home-search"
            type="search"
            placeholder="寻找你的灵感…"
            aria-label="搜索我的设计" /></label
        ><button
          class="design-toggle"
          id="design-toggle"
          aria-label="以列表显示设计"
          aria-pressed="false"
          title="切换列表视图"
        >
          <span data-icon="list" aria-hidden="true"></span>
        </button>
      </div>
    </div>
    <div id="home-projects" class="home-projects" aria-live="polite">
      <p class="projects-loading">正在读取你的设计…</p>
    </div>
    <div id="home-empty" class="home-empty" hidden>
      <span data-icon="blueprint" aria-hidden="true"></span>
      <div>
        <strong>这里，留给你的下一个杰作。</strong>
        <p>创建你的第一份设计，或导入一份建筑蓝图。</p>
      </div>
      <button data-home-create>新建设计 <span aria-hidden="true">＋</span></button>
    </div>
    <p id="home-no-results" class="home-no-results" hidden>没有找到匹配的设计，试试其他名称。</p>
    <div class="home-tip">
      <span data-icon="torch" aria-hidden="true"></span>
      <p>
        <strong>建造小贴士</strong
        ><span id="home-tip-text"
          >不用一次搭完一座城。先放下第一个方块，剩下的灵感会慢慢到来。</span
        >
      </p>
      <button id="home-next-tip" aria-label="下一条建造小贴士" title="下一条小贴士">↻</button>
    </div>
  </section>
  <section class="home-guide-banner">
    <div class="guide-banner-icon" data-icon="book" aria-hidden="true"></div>
    <div>
      <span class="section-meta">YOUR ADVENTURE GUIDE</span>
      <h2>好建筑，从熟悉工具开始。</h2>
      <p>花一点时间认识你的工作台，让每一次建造都更得心应手。</p>
    </div>
    <button data-home-guide>查看建造指南 <span aria-hidden="true">↗</span></button>
  </section>
</main>
<footer class="home-footer">
  <a class="footer-brand" href="/" aria-label="回到首页"
    ><span data-icon="grass" aria-hidden="true"></span> Design Workbench
    <span class="footer-version">v0.1.0</span></a
  ><span class="footer-made"
    >用方块，记录想象。<span
      class="footer-creeper"
      data-icon="creeper"
      aria-hidden="true"
    ></span></span
  ><span class="footer-local" id="home-connection"><i></i> 正在连接本地工作台</span>
</footer>
<input id="home-import-file" type="file" accept=".litematic" hidden />
<output id="home-notice" class="home-notice" role="status" hidden></output>
<dialog id="home-create-dialog" class="home-dialog" aria-labelledby="home-create-title">
  <form id="home-create-form">
    <div class="dialog-heading">
      <div>
        <small class="section-meta">A NEW ADVENTURE</small>
        <h2 id="home-create-title">给你的灵感起个名字</h2>
      </div>
      <button type="button" data-home-close aria-label="关闭新建设计">×</button>
    </div>
    <p class="muted">每一个伟大的建筑，都从一个小小的想法开始。</p>
    <label for="home-project-name">设计名称</label
    ><input
      id="home-project-name"
      name="name"
      placeholder="例如：山间小屋"
      required
      maxlength="128"
      autocomplete="off"
    />
    <p id="home-create-error" class="home-form-error" role="alert"></p>
    <div class="dialog-actions">
      <button type="button" data-home-close>再想想</button
      ><button class="primary" type="submit" id="home-create-submit">创建并开始建造 →</button>
    </div>
  </form>
</dialog>
<dialog
  id="home-guide-dialog"
  class="home-dialog home-guide-dialog"
  aria-labelledby="home-guide-title"
>
  <div class="dialog-heading">
    <div>
      <small class="section-meta">THE BUILDER'S HANDBOOK</small>
      <h2 id="home-guide-title">你的第一本建造指南</h2>
    </div>
    <button data-home-close aria-label="关闭建造指南">×</button>
  </div>
  <div class="home-guide-steps">
    <div>
      <span>01</span>
      <h3>准备好你的世界</h3>
      <p>
        新建一份设计，或导入 .litematic
        蓝图。想先试试？首页的「先搭一间小屋」会为你生成一份可自由编辑的木屋。
      </p>
    </div>
    <div>
      <span>02</span>
      <h3>放下第一个方块</h3>
      <p>
        在左侧挑选方块材料，用选择、放置和删除工具编辑。选中区域后，可以填充、替换、阵列、构筑屋顶，先预览再应用。
      </p>
    </div>
    <div>
      <span>03</span>
      <h3>换个角度看灵感</h3>
      <p>
        拖动旋转、右键平移、滚轮缩放。用底部播放条逐层查看建造过程，或按 G
        进入第一人称，走进自己的建筑。
      </p>
    </div>
    <div>
      <span>04</span>
      <h3>把建筑带进游戏</h3>
      <p>
        编辑会自动保存到本地。完成后，在工作台顶部导出 .litematic 蓝图，再通过 Litematica 在
        Minecraft 中使用。
      </p>
    </div>
  </div>
  <div class="home-guide-keys">
    <span><kbd>1</kbd><kbd>2</kbd><kbd>3</kbd> 切换工具</span
    ><span><kbd>Ctrl</kbd> + <kbd>Z</kbd> 撤销</span><span><kbd>Space</kbd> 逐层播放</span
    ><span><kbd>G</kbd> 第一人称</span>
  </div>
  <div class="dialog-actions">
    <button data-home-close class="primary">准备好了，开始探索 →</button>
  </div>
</dialog>
`,o=(e,n="0 0 32 36")=>`<svg viewBox="${n}" fill="none" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">${e}</svg>`,i=e=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" xmlns="http://www.w3.org/2000/svg">${e}</svg>`,V={diamond:"diamond",emerald:"emerald",pickaxe:"iron_pickaxe",book:"book",torch:"torch"},N={emerald:o('<path d="M10 2h12v3h4v4h3v14h-3v4h-4v3H10v-3H6v-4H3V9h3V5h4Z" fill="#153e28"/><path d="M11 4h10v3h4v4h2v10h-4v5h-3v2h-9v-3H7v-4H5V10h3V7h3Z" fill="#4faa65"/><path d="M11 5h9v3h-9ZM8 8h4v12H8Zm4 4h8v12h-8Z" fill="#a6e09a"/><path d="M21 8h3v13h-4v5h-8v-3h8v-5h1Z" fill="#2a7d4a"/><path d="M11 6h7v2h-7Zm-2 4h2v6H9Z" fill="#e3f6bf"/>',"0 0 32 32"),diamond:o('<path d="M6 1h4v1h2v2h2v3h1v5h-2v2h-3v1H6v-1H3v-2H2V7h1V4h1V2h2Z" fill="#155f62"/><path d="M6 2h4v1h2v2h1v3h1v4h-2v1H5v-1H3V7h1V4h2Z" fill="#26bdb2"/><path d="M6 2h3v1h2v2H6ZM4 5h2v5H4Zm2 0h5v4H6Z" fill="#a9f3e6"/><path d="M6 4h3v1H6Zm-1 3h2v2H5Z" fill="#effff7"/><path d="M6 10h5v2H5v-1h1Zm4-4h2v4h-2Z" fill="#169f99"/><path d="M5 13h6v1H5Z" fill="#59daca"/>',"0 0 16 16"),github:i('<path d="M9 19c-4 1-4-2-6-2m12 5v-4a3.5 3.5 0 0 0-1-3c3-.3 6-1.5 6-6a4.7 4.7 0 0 0-1-3 4.5 4.5 0 0 0 0-3s-1 0-3 1a12 12 0 0 0-8 0C6 3 5 3 5 3a4.5 4.5 0 0 0 0 3 4.7 4.7 0 0 0-1 3c0 4.5 3 5.7 6 6a3.5 3.5 0 0 0-1 3v4"/>'),star:i('<path d="m12 3 2.8 5.6 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.5l6.2-.9Z"/>'),code:i('<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/>'),chat:i('<path d="M21 4H3v13h5v4l6-4h7ZM7 8h10M7 12h7"/>'),qr:i('<path d="M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h3v3h4m-7 0v4h7v-2M6 6h1m10 0h1M6 17h1"/>'),grass:o('<path d="M16 1 31 9v18l-15 8L1 27V9Z" fill="#10150d"/><path d="m16 3 13 7-13 7L3 10Z" fill="#8cb859"/><path d="m3 12 12 7v13L3 25Z" fill="#795135"/><path d="m17 19 12-7v13l-12 7Z" fill="#523a2b"/><path d="m3 12 12 7v5l-4-2v-3l-4-2v3l-4-2Z" fill="#669343"/><path d="m17 19 12-7v5l-4 2v3l-4 2v-3l-4 2Z" fill="#44682e"/><path d="m9 8 5-3 4 2-5 3Z" fill="#b1cd7f"/><path d="m19 10 4-2 4 2-4 2Z" fill="#659746"/><path d="m6 23 3 2v3l-3-2Zm5 3 2 1v3l-2-1Z" fill="#aa7950"/><path d="m20 26 3-2v3l-3 2Z" fill="#78543a"/>'),pickaxe:o('<path d="M4 26h4v-4h4v-4h4v-4h4v-4h4v8h4V6H16v4h6l-6 4h-4v4H8v4H4Z" fill="#384b2a"/><path d="M3 24h4v-4h4v-4h4v-4h4v4h-4v4h-4v4H7v4H3Z" fill="#c6aa78"/><path d="M12 5h12v4h4v12h-4V10H12Z" fill="#b5e88c"/><path d="M12 5h12v2H12Z" fill="#e3f7c7"/>',"0 0 32 32"),crafting:o('<path d="m16 1 15 8v18l-15 8L1 27V9Z" fill="#18150e"/><path d="m16 3 13 7-13 7L3 10Z" fill="#c59a62"/><path d="m3 12 12 7v13L3 25Z" fill="#966337"/><path d="m17 19 12-7v13l-12 7Z" fill="#694326"/><path d="m7 10 9-5 9 5-9 5Z" fill="#69482b"/><path d="m9 10 7-4 7 4-7 4Z" fill="#bb8e57"/><path d="m12 8 7 4m-3-6 7 4m-4-2-7 4m4-6-7 4" stroke="#69482b" stroke-width="1"/><path d="m5 16 8 4v3l-8-4Z" fill="#c7965a"/><path d="m6 19 2 1v6l-2-1m4-3 2 1v5l-2-1" fill="#553820"/><path d="m20 21 6-3v3l-6 3Zm2 4 3-2v4l-3 2Z" fill="#b17a43"/>'),chest:o('<path d="m16 3 15 7v17l-15 7L1 27V10Z" fill="#211b11"/><path d="m16 5 13 6-13 6L3 11Z" fill="#c49a43"/><path d="m3 13 12 6v12L3 25Z" fill="#ad792c"/><path d="m17 19 12-6v12l-12 6Z" fill="#79501f"/><path d="m3 19 12 6m2 0 12-6" stroke="#47331e" stroke-width="2"/><path d="m6 12 10 5 10-5M5 15v9m22-9v9" stroke="#e0ac49" stroke-width="1.5"/><path d="m7 18 5 3v7l-5-3Z" fill="#ead9a2"/><path d="m9 22 2 1v3l-2-1Z" fill="#716541"/>'),cabin:o('<path d="m16 2 15 14h-4v15l-11 4L4 31V16H0Z" fill="#171a14"/><path d="m16 5 12 11-12 4L3 16Z" fill="#6b8e4f"/><path d="m16 8 8 8-8 3-9-3Z" fill="#90ad65"/><path d="m5 18 10 4v10L5 29Z" fill="#c9b483"/><path d="m17 22 9-4v11l-9 3Z" fill="#89734e"/><path d="m8 22 4 2v5l-4-2Z" fill="#ecbd64"/><path d="m20 22 4-2v5l-4 2Z" fill="#daa555"/><path d="m2 16 14 5 14-5M5 18v11m11-8v13m10-16v11" stroke="#51452c" stroke-width="2"/>'),torch:o('<path d="M12 13h8v6h-8z" fill="#d7a148"/><path d="M14 19h4v12h-4z" fill="#87643b"/><path d="M14 2h4v4h4v9H10V8h4Z" fill="#e8a83c"/><path d="M14 6h4v8h-4z" fill="#ffe4a0"/><path d="M14 21h2v8h-2z" fill="#c79556"/>',"0 0 32 32"),book:o('<path d="m14 3 15 7v19l-13 5L2 27V8Z" fill="#231e18"/><path d="m14 5 12 6-10 4L5 9Z" fill="#dbd1ab"/><path d="m5 12 10 5v14L5 26Z" fill="#6c914a"/><path d="m17 17 9-4v14l-9 4Z" fill="#3d6231"/><path d="m8 15 4 2v10l-4-2Z" fill="#a5be6f"/><path d="m19 19 3-1v7l-3 1Z" fill="#d3a851"/>'),creeper:o('<path fill="#6d8459" d="M2 2h12v12H2Z"/><path fill="#20251c" d="M4 5h3v3H4Zm5 0h3v3H9ZM7 8h2v4H7ZM5 9h2v4H5Zm4 0h2v4H9Z"/>',"0 0 16 16"),import:i('<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>'),cube:i('<path d="m12 3 9 5v9l-9 5-9-5V8Zm0 10 9-5m-9 5L3 8m9 5v9"/>'),layers:i('<path d="m12 3 9 5-9 5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>'),blueprint:i('<path d="M5 3h12l3 3v15H5Zm12 0v4h3M8 11h9M8 15h6M8 7h5"/>'),replay:i('<path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/>'),next:i('<path d="m9 5 7 7-7 7"/>'),pause:i('<path d="M8 5v14M16 5v14" stroke-width="3"/>'),play:i('<path d="m8 5 11 7-11 7Z" fill="currentColor" stroke="none"/>'),search:i('<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>'),list:i('<path d="M9 6h12M9 12h12M9 18h12M3 6h2M3 12h2M3 18h2"/>'),grid:i('<path d="M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h7v7h-7Z"/>')};function b(e=document){e.querySelectorAll("[data-icon]").forEach(n=>{n.innerHTML=N[n.dataset.icon]??"";const a=V[n.dataset.icon];if(!a)return;const s=document.createElement("img");s.alt="",s.className="vanilla-sprite",s.decoding="async",s.hidden=!0,s.onload=()=>{n.querySelector("svg")?.remove(),s.hidden=!1},s.onerror=()=>s.remove(),s.src=`/api/ui/sprites/${a}.png`,n.append(s)})}const H=document.querySelector("#app");H.className="home-mode";H.innerHTML=A;b();const t=e=>document.getElementById(e),E=t("home-create-dialog"),x=t("home-guide-dialog"),f=t("home-project-name"),p=t("home-import-file");let h=[],c=!1,L=!1,k=0,d=null;function m(e,n=!1){const a=t("home-notice");a.textContent=e,a.classList.toggle("is-error",n),a.hidden=!1,clearTimeout(k),k=window.setTimeout(()=>a.hidden=!0,n?8e3:4e3)}async function u(e,n){const a=await fetch(e,n),s=await a.json();if(!a.ok)throw new Error(s.error?.message??s.detail??`请求失败 (${a.status})`);return s}function C(e,n=!1){const a=new URLSearchParams({project:e});n&&a.set("starter","cabin"),location.assign(`?${a}`)}function _(){try{const e=JSON.parse(localStorage.getItem("workbench.recentProjects")??"{}");return!e||typeof e!="object"||Array.isArray(e)?{}:Object.fromEntries(Object.entries(e).filter(([,n])=>typeof n=="number"&&Number.isFinite(n)))}catch{return{}}}function Z(){const e=t("home-search").value.trim().toLocaleLowerCase(),n=h.filter(a=>a.name.toLocaleLowerCase().includes(e));t("home-project-count").textContent=String(h.length),t("design-count").textContent=`${h.length} 个项目`,t("home-empty").hidden=h.length>0,t("home-no-results").hidden=!h.length||!!n.length,t("home-projects").replaceChildren(...n.map(a=>{const s=document.createElement("a");s.className="project-card",s.href=`?project=${encodeURIComponent(a.project_id)}`;const r=document.createElement("span");r.className="project-art",r.dataset.icon=a.blocks?"cabin":"blueprint",r.setAttribute("aria-hidden","true");const l=document.createElement("div"),y=document.createElement("strong");y.textContent=a.name;const M=document.createElement("small");M.textContent=`${a.blocks.toLocaleString()} 个方块 · 修订 ${a.revision}`,l.append(y,M);const v=document.createElement("span");return v.className="project-arrow",v.textContent="↗",v.setAttribute("aria-hidden","true"),s.append(r,l,v),s})),b(t("home-projects"))}function j(e=!1){c||(L=e,f.value=e?"我的林间小屋":"",t("home-create-title").textContent=e?"从一间小屋开始":"给你的灵感起个名字",t("home-create-error").textContent="",E.showModal(),f.focus())}document.querySelectorAll("[data-home-create]").forEach(e=>{e.onclick=()=>j()});t("home-cabin").onclick=()=>j(!0);document.querySelectorAll("[data-home-guide]").forEach(e=>{e.onclick=()=>x.showModal()});document.querySelectorAll("[data-home-close]").forEach(e=>{e.onclick=()=>e.closest("dialog")?.close()});for(const e of[E,x])e.addEventListener("click",n=>{if(n.target!==e)return;const a=e.getBoundingClientRect();(n.clientX<a.left||n.clientX>a.right||n.clientY<a.top||n.clientY>a.bottom)&&e.close()});t("home-create-form").onsubmit=async e=>{if(e.preventDefault(),c)return;const n=f.value.trim();if(!n){t("home-create-error").textContent="给你的设计起一个名字吧。",f.focus();return}c=!0;const a=t("home-create-submit");a.disabled=!0,a.textContent="正在准备你的世界…";try{if(d&&!d.resources_ready)throw new Error("方块素材尚未配置，请先完成本地资源设置再开始建造。");const s=await u("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:n})});C(s.project_id,L)}catch(s){t("home-create-error").textContent=s instanceof Error?s.message:"创建失败，请检查本地服务后重试。",a.disabled=!1,a.textContent="创建并开始建造 →",c=!1}};document.querySelectorAll("[data-home-import]").forEach(e=>{e.onclick=()=>{c||p.click()}});p.onchange=async()=>{const e=p.files?.[0];if(!(!e||c)){if(!e.name.toLowerCase().endsWith(".litematic")){m("请选择 .litematic 格式的建筑蓝图。",!0),p.value="";return}if(e.size>32e6){m("蓝图文件不能超过 32 MB，请选择较小的文件。",!0),p.value="";return}c=!0,document.querySelectorAll("[data-home-import]").forEach(n=>{n.disabled=!0}),m(`正在导入「${e.name}」…`);try{if(d&&!d.resources_ready)throw new Error("方块素材尚未配置，请先完成本地资源设置。");const n=await u("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:e.name.replace(/\.litematic$/i,"").slice(0,128)||"导入的建筑"})});h.unshift(n),Z();const a=new FormData;a.set("file",e),a.set("expected_revision",String(n.revision)),a.set("request_id",crypto.randomUUID()),await u(`/api/projects/${encodeURIComponent(n.project_id)}/import`,{method:"POST",body:a}),C(n.project_id)}catch(n){m(n instanceof Error?n.message:"导入失败，请检查蓝图后重试。",!0),c=!1,document.querySelectorAll("[data-home-import]").forEach(a=>{a.disabled=!1})}finally{p.value=""}}};t("home-search").oninput=Z;t("design-toggle").onclick=()=>{const e=t("design-toggle"),n=t("home-projects").classList.toggle("is-list");e.setAttribute("aria-pressed",String(n)),e.setAttribute("aria-label",n?"以网格显示设计":"以列表显示设计"),e.innerHTML=`<span data-icon="${n?"grid":"list"}" aria-hidden="true"></span>`,b(e)};const w=["不用一次搭完一座城。先放下第一个方块，剩下的灵感会慢慢到来。","先做建筑轮廓，再补细节。用「盒体填充」和「双坡屋顶」快速确定你的建筑比例。","试试逐层播放：一层一层看清结构，也让复杂的建造变得井井有条。","按 G 进入第一人称。走进自己的建筑，才能发现窗外那一束刚刚好的风景。","多用分组整理墙体、屋顶和窗户。想换一种材料时，就可以一次替换整组。"];let g=0;t("home-next-tip").onclick=()=>{g=(g+1)%w.length,t("home-tip-text").textContent=w[g]};async function S(){const e=await Promise.allSettled([u("/api/info"),u("/api/projects")]),n=t("home-connection");if(e[0].status==="fulfilled"?(d=e[0].value,t("home-version").textContent=`JAVA ${d.minecraft_version}`,n.replaceChildren(),n.append(document.createElement("i"),document.createTextNode(d.resources_ready?"本地工作台已连接":"已连接 · 待配置方块素材")),n.classList.toggle("is-offline",!d.resources_ready)):(n.replaceChildren(),n.append(document.createElement("i"),document.createTextNode("本地服务未连接")),n.classList.add("is-offline")),e[1].status==="fulfilled"){const a=_();h=e[1].value.items.sort((s,r)=>(a[r.project_id]??0)-(a[s.project_id]??0)),Z(),e[1].value.errors?.length&&m("部分设计暂时无法读取，其余设计已显示。",!0)}else{t("home-projects").replaceChildren();const a=document.createElement("p");a.className="projects-loading",a.textContent="暂时无法读取设计。请检查本地工作台服务，刷新后重试。",t("home-projects").append(a)}}S();window.addEventListener("pageshow",e=>{e.persisted&&S()});T(async()=>{const{HomeScene:e}=await import("./homeScene-DflaHt-9.js");return{HomeScene:e}},__vite__mapDeps([0,1])).then(({HomeScene:e})=>{let n;try{n=new e(t("home-scene"),l=>{t("scene-building-name").textContent=l.name,t("scene-building-index").textContent=`${String(l.index+1).padStart(2,"0")} / ${String(l.total).padStart(2,"0")}`,t("scene-building-phase").textContent={build:"正在搭建",hold:"一方天地，无限可能",dismantle:"方块轻轻散开",switch:"下一份灵感…"}[l.phase]})}catch{t("scene-fallback").hidden=!1,t("scene-pause").hidden=t("scene-replay").hidden=t("scene-next").hidden=!0;return}let a=!1;const s=t("scene-pause"),r=()=>{s.setAttribute("aria-pressed",String(a)),s.setAttribute("aria-label",a?"继续首页动画":"暂停首页动画"),s.title=a?"继续动画":"暂停动画",s.innerHTML=`<span data-icon="${a?"play":"pause"}" aria-hidden="true"></span>`,b(s)};s.onclick=()=>{a=!a,n.setPaused(a),r()},t("scene-replay").onclick=()=>{a=!1,n.replay(),r()},t("scene-next").onclick=()=>n.nextBuilding(),window.addEventListener("pagehide",l=>{l.persisted||n.dispose()})}).catch(()=>{t("scene-fallback").hidden=!1,t("scene-pause").hidden=t("scene-replay").hidden=t("scene-next").hidden=!0});
