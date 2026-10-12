const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/homeScene-DflaHt-9.js","assets/three.module-BKyUEcGm.js"])))=>i.map(i=>d[i]);
import{_ as N}from"./main-DOtyJZE6.js";/* empty css              */import{h as g}from"./homeIcons-TEDqZ-z5.js";import"./modulepreload-polyfill-B5Qt9EMX.js";const D=`<div class="home-topline" aria-hidden="true"></div>
<header class="home-header">
  <a class="brand home-brand" href="/" aria-label="Design Workbench 首页">
    <span class="brand-mark" data-icon="grass" aria-hidden="true"></span>
    <span><strong>Design Workbench</strong><small>MINECRAFT 建筑设计工作台</small></span>
  </a>
  <nav class="home-nav" aria-label="主导航">
    <a href="#" class="is-current" aria-current="page">首页</a>
    <a href="#designs">我的设计 <span class="nav-count" id="home-project-count">0</span></a>
    <button type="button" data-home-guide>建造指南 <span aria-hidden="true">↗</span></button>
    <a href="?view=sponsor" class="home-sponsor-link"
      ><span data-icon="diamond" aria-hidden="true"></span>赞助支持</a
    >
  </nav>
  <div class="home-header-actions">
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
  <a class="footer-sponsor" href="?view=sponsor"
    ><span data-icon="diamond" aria-hidden="true"></span>支持开源</a
  >
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
    <label for="home-minecraft-version">Minecraft Java 版本</label>
    <select id="home-minecraft-version" name="minecraft_version"></select>
    <button type="button" id="home-resources-setup">下载所选版本的官方素材</button>
    <p id="home-resource-status" class="muted" role="status"></p>
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
`,j=document.querySelector("#app");j.className="home-mode";j.innerHTML=D;g();const a=e=>document.getElementById(e),S=a("home-create-dialog"),_=a("home-guide-dialog"),f=a("home-project-name"),p=a("home-import-file");let l=[],o=!1,T=!1,x=0,u=null,v=[];const r=a("home-minecraft-version");function m(){const e=v.find(t=>t.minecraft_version===r.value)?.resources_ready;a("home-resource-status").textContent=e?"此版本素材已就绪。":"首次使用此版本，请下载官方素材；之后可离线建造。",a("home-resources-setup").disabled=o||!!e}r.onchange=m;a("home-resources-setup").onclick=async()=>{if(!o){o=!0,r.disabled=!0,a("home-create-submit").disabled=!0,m(),a("home-resource-status").textContent="正在下载官方素材并生成图集，请稍候…";try{const e=await d("/api/resources/setup",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({minecraft_version:r.value})}),t=v.find(n=>n.minecraft_version===e.minecraft_version);t&&(t.resources_ready=e.resources_ready),a("home-create-error").textContent=""}catch(e){a("home-create-error").textContent=e instanceof Error?e.message:"素材下载失败，请重试。"}finally{o=!1,r.disabled=!1,a("home-create-submit").disabled=!1,m()}}};function h(e,t=!1){const n=a("home-notice");n.textContent=e,n.classList.toggle("is-error",t),n.hidden=!1,clearTimeout(x),x=window.setTimeout(()=>n.hidden=!0,t?8e3:4e3)}async function d(e,t){const n=await fetch(e,t),s=await n.json();if(!n.ok)throw new Error(s.error?.message??s.detail??`请求失败 (${n.status})`);return s}function O(e,t=!1){const n=new URLSearchParams({project:e});t&&n.set("starter","cabin"),location.assign(`?${n}`)}function R(){try{const e=JSON.parse(localStorage.getItem("workbench.recentProjects")??"{}");return!e||typeof e!="object"||Array.isArray(e)?{}:Object.fromEntries(Object.entries(e).filter(([,t])=>typeof t=="number"&&Number.isFinite(t)))}catch{return{}}}function w(){const e=a("home-search").value.trim().toLocaleLowerCase(),t=l.filter(n=>n.name.toLocaleLowerCase().includes(e));a("home-project-count").textContent=String(l.length),a("design-count").textContent=`${l.length} 个项目`,a("home-empty").hidden=l.length>0,a("home-no-results").hidden=!l.length||!!t.length,a("home-projects").replaceChildren(...t.map(n=>{const s=document.createElement("a");s.className="project-card",s.href=`?project=${encodeURIComponent(n.project_id)}`;const i=document.createElement("span");i.className="project-art",i.dataset.icon=n.blocks?"cabin":"blueprint",i.setAttribute("aria-hidden","true");const c=document.createElement("div"),k=document.createElement("strong");k.textContent=n.name;const E=document.createElement("small");E.textContent=`Java ${n.minecraft_version} · ${n.blocks.toLocaleString()} 个方块 · 修订 ${n.revision}`,c.append(k,E);const b=document.createElement("span");return b.className="project-arrow",b.textContent="↗",b.setAttribute("aria-hidden","true"),s.append(i,c,b),s})),g(a("home-projects"))}function A(e=!1){o||(T=e,f.value=e?"我的林间小屋":"",a("home-create-title").textContent=e?"从一间小屋开始":"给你的灵感起个名字",a("home-create-error").textContent="",m(),S.showModal(),f.focus())}document.querySelectorAll("[data-home-create]").forEach(e=>{e.onclick=()=>A()});a("home-cabin").onclick=()=>A(!0);document.querySelectorAll("[data-home-guide]").forEach(e=>{e.onclick=()=>_.showModal()});document.querySelectorAll("[data-home-close]").forEach(e=>{e.onclick=()=>e.closest("dialog")?.close()});for(const e of[S,_])e.addEventListener("click",t=>{if(t.target!==e)return;const n=e.getBoundingClientRect();(t.clientX<n.left||t.clientX>n.right||t.clientY<n.top||t.clientY>n.bottom)&&e.close()});a("home-create-form").onsubmit=async e=>{if(e.preventDefault(),o)return;const t=f.value.trim();if(!t){a("home-create-error").textContent="给你的设计起一个名字吧。",f.focus();return}o=!0;const n=a("home-create-submit");n.disabled=!0,n.textContent="正在准备你的世界…";try{if(u=await d(`/api/info?minecraft_version=${encodeURIComponent(r.value)}`),u&&!u.resources_ready)throw new Error("此版本素材尚未配置，请点击「下载所选版本的官方素材」。");const s=await d("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:t,minecraft_version:r.value})});O(s.project_id,T)}catch(s){a("home-create-error").textContent=s instanceof Error?s.message:"创建失败，请检查本地服务后重试。",n.disabled=!1,n.textContent="创建并开始建造 →",o=!1}};document.querySelectorAll("[data-home-import]").forEach(e=>{e.onclick=()=>{o||p.click()}});p.onchange=async()=>{const e=p.files?.[0];if(!(!e||o)){if(!e.name.toLowerCase().endsWith(".litematic")){h("请选择 .litematic 格式的建筑蓝图。",!0),p.value="";return}if(e.size>32e6){h("蓝图文件不能超过 32 MB，请选择较小的文件。",!0),p.value="";return}o=!0,document.querySelectorAll("[data-home-import]").forEach(t=>{t.disabled=!0}),h(`正在导入「${e.name}」…`);try{const t=new FormData;t.set("file",e);const n=await d("/api/blueprints/info",{method:"POST",body:t});if(!n.resources_ready)throw r.value=n.minecraft_version,new Error(`蓝图使用 Java ${n.minecraft_version}。请在「开始建造」中下载此版本素材，再导入。`);const s=await d("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:e.name.replace(/\.litematic$/i,"").slice(0,128)||"导入的建筑",minecraft_version:n.minecraft_version})});l.unshift(s),w();const i=new FormData;i.set("file",e),i.set("expected_revision",String(s.revision)),i.set("request_id",crypto.randomUUID()),await d(`/api/projects/${encodeURIComponent(s.project_id)}/import`,{method:"POST",body:i}),O(s.project_id)}catch(t){h(t instanceof Error?t.message:"导入失败，请检查蓝图后重试。",!0),o=!1,document.querySelectorAll("[data-home-import]").forEach(n=>{n.disabled=!1})}finally{p.value=""}}};a("home-search").oninput=w;a("design-toggle").onclick=()=>{const e=a("design-toggle"),t=a("home-projects").classList.toggle("is-list");e.setAttribute("aria-pressed",String(t)),e.setAttribute("aria-label",t?"以网格显示设计":"以列表显示设计"),e.innerHTML=`<span data-icon="${t?"grid":"list"}" aria-hidden="true"></span>`,g(e)};const C=["不用一次搭完一座城。先放下第一个方块，剩下的灵感会慢慢到来。","先做建筑轮廓，再补细节。用「盒体填充」和「双坡屋顶」快速确定你的建筑比例。","试试逐层播放：一层一层看清结构，也让复杂的建造变得井井有条。","按 G 进入第一人称。走进自己的建筑，才能发现窗外那一束刚刚好的风景。","多用分组整理墙体、屋顶和窗户。想换一种材料时，就可以一次替换整组。"];let y=0;a("home-next-tip").onclick=()=>{y=(y+1)%C.length,a("home-tip-text").textContent=C[y]};async function L(){const e=await Promise.allSettled([d("/api/info"),d("/api/projects"),d("/api/versions")]),t=a("home-connection");if(e[2].status==="fulfilled"&&(v=e[2].value.items,r.replaceChildren(...v.map(n=>new Option(`Java ${n.minecraft_version}`,n.minecraft_version))),r.value=e[2].value.default,m()),e[0].status==="fulfilled"?(u=e[0].value,t.replaceChildren(),t.append(document.createElement("i"),document.createTextNode(u.resources_ready?"本地工作台已连接":"已连接 · 待配置方块素材")),t.classList.toggle("is-offline",!u.resources_ready)):(t.replaceChildren(),t.append(document.createElement("i"),document.createTextNode("本地服务未连接")),t.classList.add("is-offline")),e[1].status==="fulfilled"){const n=R();l=e[1].value.items.sort((s,i)=>(n[i.project_id]??0)-(n[s.project_id]??0)),w(),e[1].value.errors?.length&&h("部分设计暂时无法读取，其余设计已显示。",!0)}else{a("home-projects").replaceChildren();const n=document.createElement("p");n.className="projects-loading",n.textContent="暂时无法读取设计。请检查本地工作台服务，刷新后重试。",a("home-projects").append(n)}}L();window.addEventListener("pageshow",e=>{e.persisted&&L()});N(async()=>{const{HomeScene:e}=await import("./homeScene-DflaHt-9.js");return{HomeScene:e}},__vite__mapDeps([0,1])).then(({HomeScene:e})=>{let t;try{t=new e(a("home-scene"),c=>{a("scene-building-name").textContent=c.name,a("scene-building-index").textContent=`${String(c.index+1).padStart(2,"0")} / ${String(c.total).padStart(2,"0")}`,a("scene-building-phase").textContent={build:"正在搭建",hold:"一方天地，无限可能",dismantle:"方块轻轻散开",switch:"下一份灵感…"}[c.phase]})}catch{a("scene-fallback").hidden=!1,a("scene-pause").hidden=a("scene-replay").hidden=a("scene-next").hidden=!0;return}let n=!1;const s=a("scene-pause"),i=()=>{s.setAttribute("aria-pressed",String(n)),s.setAttribute("aria-label",n?"继续首页动画":"暂停首页动画"),s.title=n?"继续动画":"暂停动画",s.innerHTML=`<span data-icon="${n?"play":"pause"}" aria-hidden="true"></span>`,g(s)};s.onclick=()=>{n=!n,t.setPaused(n),i()},a("scene-replay").onclick=()=>{n=!1,t.replay(),i()},a("scene-next").onclick=()=>t.nextBuilding(),window.addEventListener("pagehide",c=>{c.persisted||t.dispose()})}).catch(()=>{a("scene-fallback").hidden=!1,a("scene-pause").hidden=a("scene-replay").hidden=a("scene-next").hidden=!0});
