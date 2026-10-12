const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/homeScene-BskHhR8t.js","assets/three.module-BKyUEcGm.js"])))=>i.map(i=>d[i]);
import{_ as ae}from"./main-B5l7SAB3.js";import{h as B,i as se}from"./minecraftUI-Cl_zRL2Y.js";/* empty css             */import{s as oe,N as re,f as G,n as ie,W as ce,A as de,l as le,r as pe,D as he,I as ue,h as me,t as fe,V as k,O as be,b as ve,m as ge,B as ye,F as U}from"./three.module-BKyUEcGm.js";import"./modulepreload-polyfill-B5Qt9EMX.js";const we=`<div class="home-topline" aria-hidden="true"></div>
<header class="home-header">
  <a class="brand home-brand" href="/" aria-label="Design Workbench 首页">
    <span class="brand-mark" data-icon="grass" aria-hidden="true"></span>
    <span><strong>Design Workbench</strong><small>MINECRAFT 建筑设计工作台</small></span>
  </a>
  <nav class="home-nav" aria-label="主导航">
    <a href="#" class="is-current" aria-current="page">首页</a>
    <a href="#designs">我的设计 <span class="nav-count" id="home-project-count">0</span></a>
    <button type="button" data-home-guide>建造指南 <span aria-hidden="true">→</span></button>
    <a href="?view=sponsor" class="home-sponsor-link"
      ><span data-icon="diamond" aria-hidden="true"></span>赞助支持</a
    >
  </nav>
  <div class="home-header-actions">
    <a href="?view=workbench" class="home-workbench-link"
      >进入工作台 <span aria-hidden="true">→</span></a
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
      <img
        class="hero-builders"
        src="__BUILDERS_URL__"
        width="502"
        height="577"
        alt="Alex 与史蒂夫在脚手架旁一起搭建方块"
        draggable="false"
        decoding="async"
      />
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
        <span class="start-kicker">01 / 创造</span>
        <span class="start-art" data-icon="crafting" aria-hidden="true"></span>
        <span class="start-card-content"
          ><strong>新建设计</strong><span>空白画布，无限可能。从第一个方块开始。</span></span
        ><span class="start-action"
          >打开空白工作台 <span class="start-arrow" aria-hidden="true">→</span></span
        >
      </button>
      <button class="start-card start-import" data-home-import>
        <span class="start-kicker">02 / 延续</span>
        <span class="start-art" data-icon="chest" aria-hidden="true"></span>
        <span class="start-card-content"
          ><strong>导入蓝图</strong><span>导入 .litematic，让已有灵感继续生长。</span></span
        ><span class="start-action"
          >选择蓝图文件 <span class="start-arrow" aria-hidden="true">↑</span></span
        >
      </button>
      <button class="start-card start-cabin" id="home-cabin">
        <span class="start-kicker">03 / 探索</span>
        <span class="start-art" data-icon="cabin" aria-hidden="true"></span>
        <span class="start-card-content"
          ><strong>从示例开始</strong><span>从一份木屋起稿，熟悉你的建造工具。</span></span
        ><span class="start-action"
          >搭建第一间木屋 <span class="start-arrow" aria-hidden="true">→</span></span
        >
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
            placeholder="搜索设计名称…"
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
    <p id="home-no-results" class="home-no-results" hidden>
      没有找到匹配的设计，试试其他名称。<button type="button" id="home-clear-search">
        清空搜索
      </button>
    </p>
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
    <button data-home-guide>查看建造指南 <span aria-hidden="true">→</span></button>
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
<p class="home-disclaimer">非 Minecraft 官方产品。未经 Mojang 或 Microsoft 批准，也不与其关联。</p>
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
`,xe="/assets/builders-hx_ODmRa.png",j=new Map;let f=null,J=Promise.resolve();const A=new Set;function H(){A.forEach(e=>e.disconnect()),A.clear()}function ke(e,t,n){const s=new IntersectionObserver(o=>{o.some(r=>r.isIntersecting)&&(s.disconnect(),A.delete(s),J=J.then(async()=>{if(e.isConnected)try{const r=`${t}:${n}`;let c=j.get(r);if(!c){const l=await fetch(`/api/projects/${encodeURIComponent(t)}/render`,{method:"POST",signal:AbortSignal.timeout(2e4)});if(!l.ok)throw new Error("preview unavailable");const d=await l.json();c=await Ee(d,t),j.set(`${t}:${d.revision}`,c),j.size>48&&j.delete(j.keys().next().value)}if(!e.isConnected)return;const i=new Image;i.alt="",i.src=c,e.replaceChildren(i),e.classList.add("has-preview")}catch{e.isConnected&&(e.textContent="预览暂不可用 · 点击进入设计",e.classList.add("preview-unavailable"))}}))},{rootMargin:"160px"});s.observe(e),A.add(s)}function Ce(e,t){const n=[],s=[],o=[];for(const c of e.faces){const i=t.atlas.uv[c.texture];if(!i)continue;const l=new ge(c.color??(c.tint?"#91ae63":"#ffffff"));for(const d of[0,1,2,0,2,3])n.push(...c.vertices.slice(d*3,d*3+3)),s.push((i[0]+c.uv[d*2]*i[2])/t.atlas.width,1-(i[1]+c.uv[d*2+1]*i[3])/t.atlas.height),o.push(l.r,l.g,l.b)}const r=new ye;return r.setAttribute("position",new U(n,3)),r.setAttribute("uv",new U(s,2)),r.setAttribute("color",new U(o,3)),r.computeVertexNormals(),r}async function Ee(e,t){const n=await new oe().loadAsync(`/api/atlas.png?project=${encodeURIComponent(t)}`);n.magFilter=n.minFilter=re,n.colorSpace=G;const s=new ie,o=[],r=[],c=[];try{f||(f=new ce({alpha:!0,antialias:!0,preserveDrawingBuffer:!0}),f.setPixelRatio(1),f.setSize(560,300,!1),f.setClearColor("#202820",0),f.outputColorSpace=G),s.add(new de(16777215,2));const i=new le(16773591,2.5);i.position.set(-3,7,5),s.add(i);const l=new Map;for(const _ of Object.values(e.chunks))for(const b of _)l.has(b[3])||l.set(b[3],[]),l.get(b[3]).push(b);for(const[_,b]of l){const x=e.models[_];if(!x?.faces.length)continue;const S=Ce(x,e);o.push(S);const z=new pe({map:n,vertexColors:!0,alphaTest:.1,side:he,transparent:x.render_layer==="translucent",depthWrite:x.render_layer!=="translucent"});r.push(z);const I=new ue(S,z,b.length);c.push(I);const ne=new me;b.forEach(($,te)=>I.setMatrixAt(te,ne.makeTranslation($[0],$[1],$[2]))),s.add(I)}const d=e.summary.occupied_bounds;if(!d)throw new Error("empty project");const u=new fe(new k(...d.low),new k(...d.high).addScalar(1)),w=u.getCenter(new k),W=u.getSize(new k).length()/2,m=new be(-1,1,1,-1,.1,Math.max(100,W*12));m.position.copy(w).add(new k(1,.8,1.3).normalize().multiplyScalar(W/Math.sin(ve.degToRad(17.5))*1.06)),m.lookAt(w),m.updateMatrixWorld();let R=0,N=0;for(const _ of[u.min.x,u.max.x])for(const b of[u.min.y,u.max.y])for(const x of[u.min.z,u.max.z]){const S=new k(_,b,x).applyMatrix4(m.matrixWorldInverse);R=Math.max(R,Math.abs(S.x)),N=Math.max(N,Math.abs(S.y))}const M=Math.max(N,R/(560/300))*1.08;return m.left=-M*(560/300),m.right=M*(560/300),m.top=M,m.bottom=-M,m.updateProjectionMatrix(),f.render(s,m),f.domElement.toDataURL("image/png")}finally{c.forEach(i=>i.dispose()),o.forEach(i=>i.dispose()),r.forEach(i=>i.dispose()),n.dispose()}}window.addEventListener("pagehide",()=>{H(),f?.dispose(),f=null});const X=document.querySelector("#app");X.className="home-mode";X.innerHTML=we.replace("__BUILDERS_URL__",xe);B();se();const a=e=>document.getElementById(e),Z=a("home-create-dialog"),K=a("home-guide-dialog"),D=a("home-project-name"),C=a("home-import-file");let g=[],h=!1,Q=!1,V=0,T=null,y=[];const p=a("home-minecraft-version");function E(){const e=y.find(t=>t.minecraft_version===p.value)?.resources_ready;a("home-resource-status").textContent=e?"此版本素材已就绪。":"首次使用此版本，请下载官方素材；之后可离线建造。",a("home-resources-setup").disabled=h||!!e}p.onchange=E;a("home-resources-setup").onclick=async()=>{if(!h){h=!0,p.disabled=!0,a("home-create-submit").disabled=!0,E(),a("home-resource-status").textContent="正在下载官方素材并生成图集，请稍候…";try{const e=await v("/api/resources/setup",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({minecraft_version:p.value})}),t=y.find(n=>n.minecraft_version===e.minecraft_version);t&&(t.resources_ready=e.resources_ready),a("home-create-error").textContent=""}catch(e){a("home-create-error").textContent=e instanceof Error?e.message:"素材下载失败，请重试。"}finally{h=!1,p.disabled=!1,a("home-create-submit").disabled=!1,E()}}};function L(e,t=!1){const n=a("home-notice");n.textContent=e,n.classList.toggle("is-error",t),n.hidden=!1,clearTimeout(V),V=window.setTimeout(()=>n.hidden=!0,t?8e3:4e3)}async function v(e,t){const n=await fetch(e,{signal:!t?.method||t.method==="GET"?AbortSignal.timeout(2e4):void 0,...t}),s=await n.json();if(!n.ok)throw new Error(s.error?.message??s.detail??`请求失败 (${n.status})`);return s}function ee(e,t=!1){const n=new URLSearchParams({project:e});t&&n.set("starter","cabin"),location.assign(`?${n}`)}function _e(){try{const e=JSON.parse(localStorage.getItem("workbench.recentProjects")??"{}");return!e||typeof e!="object"||Array.isArray(e)?{}:Object.fromEntries(Object.entries(e).filter(([,t])=>typeof t=="number"&&Number.isFinite(t)))}catch{return{}}}function O(){H();const e=a("home-search").value.trim().toLocaleLowerCase(),t=g.filter(n=>n.name.toLocaleLowerCase().includes(e));if(a("home-project-count").textContent=String(g.length),a("design-count").textContent=`${g.length} 个项目`,a("home-empty").hidden=g.length>0,a("home-no-results").hidden=!g.length||!!t.length,a("home-projects").replaceChildren(...t.map(n=>{const s=document.createElement("a");s.className="project-card",s.href=`?project=${encodeURIComponent(n.project_id)}`;const o=document.createElement("span");o.className="project-art",o.textContent=n.blocks?"正在生成建筑预览…":"空白画布 · 从第一个方块开始",n.blocks||o.classList.add("preview-unavailable"),o.setAttribute("aria-hidden","true");const r=document.createElement("div"),c=document.createElement("strong");c.textContent=n.name;const i=document.createElement("small");i.textContent=`${n.blocks.toLocaleString()} 个方块 · Java ${n.minecraft_version}`;const l=document.createElement("small"),d=n.events?.[0]?.created,u=d?Date.parse(d):NaN;l.textContent=Number.isFinite(u)?`最近编辑 ${new Intl.DateTimeFormat("zh-CN",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}).format(u)}`:"尚未编辑 · 等待你的灵感",d&&(l.title=new Date(d).toLocaleString("zh-CN")),r.append(c,i,l);const w=document.createElement("span");return w.className="project-arrow",w.textContent="继续建造 →",w.setAttribute("aria-hidden","true"),s.append(o,r,w),n.blocks&&ke(o,n.project_id,n.revision),s})),g.length&&!e){const n=document.createElement("button");n.className="project-create-tile",n.type="button",n.innerHTML='<span class="project-create-plus" aria-hidden="true">＋</span><strong>下一个世界，等你创造</strong><span>新建设计，从第一个方块开始</span><span class="project-create-label">开始建造 →</span>',n.onclick=()=>q(),a("home-projects").append(n)}}function q(e=!1){h||(Q=e,D.value=e?"我的林间小屋":"",a("home-create-title").textContent=e?"从一间小屋开始":"给你的灵感起个名字",a("home-create-error").textContent="",E(),Z.showModal(),D.focus())}document.querySelectorAll("[data-home-create]").forEach(e=>{e.onclick=()=>q()});a("home-cabin").onclick=()=>q(!0);document.querySelectorAll("[data-home-guide]").forEach(e=>{e.onclick=()=>K.showModal()});document.querySelectorAll("[data-home-close]").forEach(e=>{e.onclick=()=>e.closest("dialog")?.close()});for(const e of[Z,K])e.addEventListener("click",t=>{if(t.target!==e)return;const n=e.getBoundingClientRect();(t.clientX<n.left||t.clientX>n.right||t.clientY<n.top||t.clientY>n.bottom)&&e.close()});a("home-create-form").onsubmit=async e=>{if(e.preventDefault(),h)return;const t=D.value.trim();if(!t){a("home-create-error").textContent="给你的设计起一个名字吧。",D.focus();return}h=!0;const n=a("home-create-submit");n.disabled=!0,n.textContent="正在准备你的世界…";try{if(T=await v(`/api/info?minecraft_version=${encodeURIComponent(p.value)}`),T&&!T.resources_ready)throw new Error("此版本素材尚未配置，请点击「下载所选版本的官方素材」。");const s=await v("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:t,minecraft_version:p.value})});ee(s.project_id,Q)}catch(s){a("home-create-error").textContent=s instanceof Error?s.message:"创建失败，请检查本地服务后重试。",n.disabled=!1,n.textContent="创建并开始建造 →",h=!1}};document.querySelectorAll("[data-home-import]").forEach(e=>{e.onclick=()=>{h||C.click()}});C.onchange=async()=>{const e=C.files?.[0];if(!(!e||h)){if(!e.name.toLowerCase().endsWith(".litematic")){L("请选择 .litematic 格式的建筑蓝图。",!0),C.value="";return}if(e.size>32e6){L("蓝图文件不能超过 32 MB，请选择较小的文件。",!0),C.value="";return}h=!0,document.querySelectorAll("[data-home-import]").forEach(t=>{t.disabled=!0}),L(`正在导入「${e.name}」…`);try{const t=new FormData;t.set("file",e);const n=await v("/api/blueprints/info",{method:"POST",body:t});if(!n.resources_ready)throw p.value=n.minecraft_version,new Error(`蓝图使用 Java ${n.minecraft_version}。请在「开始建造」中下载此版本素材，再导入。`);const s=await v("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:e.name.replace(/\.litematic$/i,"").slice(0,128)||"导入的建筑",minecraft_version:n.minecraft_version})});g.unshift(s),O();const o=new FormData;o.set("file",e),o.set("expected_revision",String(s.revision)),o.set("request_id",crypto.randomUUID()),await v(`/api/projects/${encodeURIComponent(s.project_id)}/import`,{method:"POST",body:o}),ee(s.project_id)}catch(t){L(t instanceof Error?t.message:"导入失败，请检查蓝图后重试。",!0),h=!1,document.querySelectorAll("[data-home-import]").forEach(n=>{n.disabled=!1})}finally{C.value=""}}};a("home-search").oninput=O;a("home-clear-search").onclick=()=>{a("home-search").value="",O(),a("home-search").focus()};a("design-toggle").onclick=()=>{const e=a("design-toggle"),t=a("home-projects").classList.toggle("is-list");e.setAttribute("aria-pressed",String(t)),e.setAttribute("aria-label",t?"以网格显示设计":"以列表显示设计"),e.innerHTML=`<span data-icon="${t?"grid":"list"}" aria-hidden="true"></span>`,B(e)};const Y=["不用一次搭完一座城。先放下第一个方块，剩下的灵感会慢慢到来。","先做建筑轮廓，再补细节。用「盒体填充」和「双坡屋顶」快速确定你的建筑比例。","试试逐层播放：一层一层看清结构，也让复杂的建造变得井井有条。","按 G 进入第一人称。走进自己的建筑，才能发现窗外那一束刚刚好的风景。","多用分组整理墙体、屋顶和窗户。想换一种材料时，就可以一次替换整组。"];let P=0;a("home-next-tip").onclick=()=>{P=(P+1)%Y.length,a("home-tip-text").textContent=Y[P]};async function F(){H(),a("home-projects").setAttribute("aria-busy","true"),a("home-projects").innerHTML='<span class="projects-loading sr-only">正在读取你的设计…</span>'+'<div class="project-skeleton" aria-hidden="true"></div>'.repeat(3),v("/api/versions").then(t=>{const n=p.value;y=t.items,p.replaceChildren(...y.map(s=>new Option(`Java ${s.minecraft_version}`,s.minecraft_version))),p.value=y.some(s=>s.minecraft_version===n)?n:t.default,E()}).catch(()=>{y.length||(a("home-resource-status").textContent="版本列表暂不可用，请重新连接本地工作台。")});const e=a("home-connection");v("/api/info").then(t=>{T=t,y.length||(y=[t],p.replaceChildren(new Option(`Java ${t.minecraft_version}`,t.minecraft_version)),E()),e.replaceChildren(document.createElement("i"),document.createTextNode(t.resources_ready?"本地工作台已连接":"已连接 · 待配置方块素材")),e.classList.toggle("is-offline",!t.resources_ready)}).catch(()=>{e.replaceChildren(document.createElement("i"),document.createTextNode("本地服务未连接")),e.classList.add("is-offline")});try{const t=await v("/api/projects"),n=_e();g=t.items.sort((s,o)=>(n[o.project_id]??(Date.parse(o.events?.[0]?.created??"")||0))-(n[s.project_id]??(Date.parse(s.events?.[0]?.created??"")||0))),O(),t.errors?.length&&L("部分设计暂时无法读取，其余设计已显示。",!0)}catch{a("home-projects").replaceChildren();const t=document.createElement("p");t.className="projects-error",t.textContent="暂时无法读取设计，请确认本地工作台已启动。";const n=document.createElement("button");n.textContent="重新连接",n.onclick=()=>void F(),t.append(n),a("home-projects").append(t)}a("home-projects").setAttribute("aria-busy","false")}F();window.addEventListener("pageshow",e=>{e.persisted&&F()});ae(async()=>{const{HomeScene:e}=await import("./homeScene-BskHhR8t.js");return{HomeScene:e}},__vite__mapDeps([0,1])).then(({HomeScene:e})=>{let t;try{t=new e(a("home-scene"),r=>{a("scene-building-name").textContent=r.name,a("scene-building-index").textContent=`${String(r.index+1).padStart(2,"0")} / ${String(r.total).padStart(2,"0")}`,a("scene-building-phase").textContent={build:"正在搭建",hold:"一方天地，无限可能",dismantle:"方块轻轻散开",switch:"下一份灵感…"}[r.phase]})}catch{a("scene-fallback").hidden=!1,a("scene-pause").hidden=a("scene-replay").hidden=a("scene-next").hidden=!0;return}let n=!1;const s=a("scene-pause"),o=()=>{s.setAttribute("aria-pressed",String(n)),s.setAttribute("aria-label",n?"继续首页动画":"暂停首页动画"),s.title=n?"继续动画":"暂停动画",s.innerHTML=`<span data-icon="${n?"play":"pause"}" aria-hidden="true"></span>`,B(s)};s.onclick=()=>{n=!n,t.setPaused(n),o()},a("scene-replay").onclick=()=>{n=!1,t.replay(),o()},a("scene-next").onclick=()=>t.nextBuilding(),window.addEventListener("pagehide",r=>{r.persisted||t.dispose()})}).catch(()=>{a("scene-fallback").hidden=!1,a("scene-pause").hidden=a("scene-replay").hidden=a("scene-next").hidden=!0});
