import{V as ce,t as de}from"./viewer-CTNKt4vi.js";const pe=`<header>
  <div class="brand">
    <span class="brand-mark" aria-hidden="true"
      ><svg viewBox="0 0 32 36" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 1 31 9v18l-15 8L1 27V9Z" fill="#10150d" />
        <path d="m16 3 13 7-13 7L3 10Z" fill="#8cb859" />
        <path d="m3 12 12 7v13L3 25Z" fill="#795135" />
        <path d="m17 19 12-7v13l-12 7Z" fill="#523a2b" />
        <path d="m3 12 12 7v5l-4-2v-3l-4-2v3l-4-2Z" fill="#669343" />
        <path d="m17 19 12-7v5l-4 2v3l-4 2v-3l-4 2Z" fill="#44682e" />
        <path d="m9 8 5-3 4 2-5 3Z" fill="#b1cd7f" />
        <path d="m19 10 4-2 4 2-4 2Z" fill="#659746" />
        <path d="m6 23 3 2v3l-3-2Zm5 3 2 1v3l-2-1Z" fill="#aa7950" />
        <path d="m20 26 3-2v3l-3 2Z" fill="#78543a" /></svg
    ></span>
    <div><strong>Design Workbench</strong><small>MINECRAFT · 建筑设计工作台</small></div>
  </div>
  <div class="project-bar">
    <select id="projects" aria-label="当前项目"></select
    ><button id="rename-project" title="重命名当前设计（F2）">重命名</button
    ><button id="new-project">新建</button><button id="import">导入蓝图</button
    ><button id="export" class="primary">导出蓝图</button
    ><input id="import-file" type="file" accept=".litematic" hidden />
  </div>
  <span id="version" class="tag">连接中</span>
  <button id="help" title="教程与快捷键（?）" aria-haspopup="dialog">? 教程</button>
</header>
<main id="workbench-layout">
  <aside id="library" class="library" aria-label="方块材料面板">
    <div class="panel-title">
      <h2>方块材料</h2>
      <span id="catalog-total"></span>
    </div>
    <input id="search" placeholder="搜索中文名称 / 方块 ID" aria-label="搜索材料" /><select
      id="category"
      aria-label="材料类别"
    >
      <option value="">全部类别</option>
      <option>木材</option>
      <option>构造</option>
      <option>门窗</option>
      <option>植物</option>
      <option>色彩</option>
      <option>其他</option>
    </select>
    <div id="materials" class="materials"></div>
    <div class="pagination">
      <button id="prev-page">上一页</button><span id="page"></span
      ><button id="next-page">下一页</button>
    </div>
    <div class="material-detail">
      <h3 id="material-name">选择材料</h3>
      <code id="material-id"></code>
      <div id="material-support"></div>
      <div id="properties"></div>
    </div>
  </aside>
  <section class="workspace">
    <div class="toolbar">
      <button
        id="toggle-library"
        aria-controls="library"
        aria-expanded="true"
        title="显示 / 隐藏材料面板（[）"
      >
        材料
      </button>
      <div class="tool-tabs">
        <button class="active" data-tool="select">选择</button
        ><button data-tool="place">放置</button><button data-tool="erase">删除</button>
      </div>
      <button id="undo" title="Ctrl+Z">撤销</button
      ><button id="redo" title="Ctrl+Shift+Z">重做</button><button id="save">保存 / 重读</button>
      <button id="walk-toggle" aria-pressed="false" title="第一人称 / 退出第一人称（G）">
        第一人称
      </button>
      <label id="walk-reach-control" hidden
        >命中距离
        <input
          id="walk-reach"
          type="number"
          min="0.1"
          step="0.1"
          value="5"
          aria-label="第一人称命中距离"
        />
        格</label
      >
      <div class="spacer"></div>
      <select id="compare" aria-label="版本对比">
        <option value="current">当前设计</option>
        <option value="before">上次修改前</option>
      </select>
      <button id="focus-mode" aria-pressed="false" title="专注视图：收起两侧面板（Tab）">
        专注
      </button>
      <button
        id="toggle-inspector"
        aria-controls="inspector"
        aria-expanded="true"
        title="显示 / 隐藏工具面板（]）"
      >
        工具
      </button>
    </div>
    <div id="stage" tabindex="0" aria-label="三维建筑画布">
      <div class="stage-label">
        <strong id="scene-name">创建你的建筑</strong
        ><span id="scene-meta">拖动旋转 · 右键平移 · 滚轮缩放</span>
      </div>
      <div id="walk-crosshair" hidden aria-hidden="true">+</div>
      <div id="walk-hud" hidden>
        <span id="walk-status">Esc 材料与工具 · G 退出第一人称</span>
        <output id="walk-feedback" hidden role="status"></output>
        <div class="walk-bottom">
          <p class="walk-movement">WASD 移动 · Space 上升 · Shift 下降 · Ctrl 加速</p>
          <div class="walk-material">
            <img id="walk-material-image" alt="" hidden />
            <div>
              <small>右键放置</small><strong id="walk-material-name">橡木木板</strong
              ><span id="walk-material-properties"></span>
            </div>
          </div>
          <p class="walk-edit-hint">左键删除 · Alt+左键选择或扩选</p>
        </div>
      </div>
      <div id="camera-bar" class="camera-bar">
        <button data-view="iso">等距</button><button data-view="front">正面</button
        ><button data-view="side">侧面</button><button data-view="top">顶视</button
        ><button id="fit">适配</button>
      </div>
      <div id="empty-message">新建项目，或导入已有 .litematic 建筑</div>
    </div>
    <div id="slice-controls" class="slice-bar" aria-label="逐层播放控制">
      <button
        id="layer-play"
        class="primary"
        aria-label="播放逐层建造"
        aria-pressed="false"
        title="播放 / 暂停（空格）"
      >
        ▶
      </button>
      <select id="layer-speed" aria-label="播放速度" title="播放速度">
        <option value="0.5">0.5×</option>
        <option value="1" selected>1×</option>
        <option value="2">2×</option>
        <option value="4">4×</option>
      </select>
      <button id="layer-prev" aria-label="上一层" title="上一层（←）">◀</button>
      <input id="layer" type="range" min="0" max="1" value="1" step="1" aria-label="最高显示层" />
      <button id="layer-next" aria-label="下一层" title="下一层（→）">▶</button>
      <label class="layer-counter"
        >第
        <input id="layer-number" type="number" min="1" max="1" value="1" aria-label="显示层序号" />
        / <span id="layer-total">0</span> 层</label
      >
      <button id="layer-reset" title="停止播放并显示全部层">全部</button>
    </div>
    <div id="workspace-details" class="workspace-meta">
      <output id="layer-label">暂无方块</output>
      <span id="selection-hint">点击选中；Shift+点击扩展选区</span>
    </div>
    <div id="warnings" class="warnings" hidden></div>
  </section>
  <aside id="inspector" class="inspector" aria-label="设计工具面板">
    <div class="panel-title">
      <h2>设计工具</h2>
      <span id="revision" class="tag">修订 0</span>
    </div>
    <section>
      <h3>选区</h3>
      <div class="coordinates">
        <label>起点 <input id="low" value="0,0,0" aria-label="选区起点" /></label
        ><label>终点 <input id="high" value="6,4,8" aria-label="选区终点" /></label>
      </div>
      <button id="select-bounds">应用选区</button
      ><label
        >分组
        <select id="group-filter">
          <option value="">当前选区</option>
        </select></label
      >
      <div id="group-tree" class="group-tree"></div>
    </section>
    <section>
      <h3>编辑与构形</h3>
      <label
        >工具
        <select id="operation">
          <option value="fill">盒体填充</option>
          <option value="replace">替换材料</option>
          <option value="delete">删除选区</option>
          <option value="transform">移动 / 复制 / 旋转 / 镜像</option>
          <option value="array">阵列</option>
          <option value="extrude">轮廓挤出</option>
          <option value="arc">圆弧</option>
          <option value="roof">双坡屋顶</option>
          <option value="window">窗组</option>
          <option value="group">设置分组</option>
        </select></label
      ><label>结果分组 <input id="result-group" value="main" /></label>
      <div id="operation-fields"></div>
      <div class="action-row">
        <button id="preview">预览修改</button><button id="commit" class="primary">应用修改</button>
      </div>
      <button id="cancel-preview" hidden>取消预览</button>
      <p id="preview-description" class="muted"></p>
    </section>
    <section>
      <h3>结构检查</h3>
      <button id="check">检查部件与连接</button>
      <p id="check-result" class="muted">检查门、床、楼梯与常见连接块。</p>
      <button id="apply-rules" hidden>预览规范化建议</button>
    </section>
    <section>
      <h3>起稿</h3>
      <button id="cabin">生成简单木屋</button>
      <p class="muted">生成后，每个方块仍可自由编辑。</p>
    </section>
    <section>
      <h3>历史</h3>
      <div id="history" class="history muted">尚无修改</div>
    </section>
  </aside>
</main>
<footer><span id="status" role="status">正在连接本地工作台…</span><span id="stats"></span></footer>
<section id="walk-menu" hidden aria-label="第一人称编辑菜单">
  <div class="walk-menu-heading">
    <strong>第一人称 · 编辑</strong>
    <div id="walk-menu-exit"></div>
  </div>
  <button id="walk-resume" class="primary">继续编辑</button>
  <div class="walk-menu-tabs" role="group" aria-label="编辑面板">
    <button data-walk-panel="library" aria-controls="library" aria-pressed="true">方块材料</button>
    <button data-walk-panel="inspector" aria-controls="inspector" aria-pressed="false">
      设计工具
    </button>
  </div>
  <div id="walk-menu-actions"></div>
  <div id="walk-menu-settings"></div>
  <div id="walk-panel-host"></div>
  <div id="walk-menu-layers"></div>
  <div id="walk-menu-notices"></div>
</section>
<dialog id="rename-dialog" aria-labelledby="rename-title">
  <form id="rename-form">
    <div class="dialog-heading">
      <h2 id="rename-title">重命名设计</h2>
      <button type="button" data-close-dialog="rename-dialog" aria-label="关闭重命名">×</button>
    </div>
    <p class="muted">名称会自动保存，也可以通过撤销恢复。</p>
    <label for="project-name">设计名称</label>
    <input id="project-name" name="name" required maxlength="128" autocomplete="off" />
    <p id="rename-error" class="error" role="alert"></p>
    <div class="dialog-actions">
      <button type="button" data-close-dialog="rename-dialog">取消</button
      ><button id="rename-submit" type="submit" class="primary">保存名称</button>
    </div>
  </form>
</dialog>
<dialog id="help-dialog" aria-labelledby="help-title">
  <div class="dialog-heading">
    <div>
      <small class="muted">WORKBENCH GUIDE</small>
      <h2 id="help-title">教程与快捷键</h2>
    </div>
    <button data-close-dialog="help-dialog" aria-label="关闭教程">×</button>
  </div>
  <div class="help-steps">
    <p>
      <strong>01 · 开始设计</strong><br />新建或导入 .litematic
      蓝图；也可以在右侧点击“生成简单木屋”开始。
    </p>
    <p>
      <strong>02 · 选择与编辑</strong><br />在左侧挑选材料，用“选择 / 放置 / 删除”操作画布。Shift +
      点击可扩展选区；右侧工具先预览，再应用。
    </p>
    <p>
      <strong>03 · 查看建造过程</strong
      ><br />底部播放条从低层向上逐层展示。可拖动进度、输入层号、调整倍速；播放到最后自动暂停。层序号从
      1 开始，Y 表示实际高度。
    </p>
    <p>
      <strong>04 · 保存与导出</strong
      ><br />编辑自动保存；重命名在顶部，完成后可导出蓝图。左右面板可分别隐藏，“专注”会收起两侧，再次点击恢复。
    </p>
  </div>
  <div class="shortcut-grid">
    <span>旋转 / 平移 / 缩放</span><span>左键拖动 / 右键拖动 / 滚轮</span>
    <span>选择 / 放置 / 删除工具</span><span><kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd></span>
    <span>撤销 / 重做</span
    ><span><kbd>Ctrl Z</kbd> / <kbd>Ctrl Shift Z</kbd> 或 <kbd>Ctrl Y</kbd></span>
    <span>保存并重读</span><kbd>Ctrl S</kbd> <span>重命名设计</span><kbd>F2</kbd>
    <span>播放 / 暂停</span><kbd>Space</kbd> <span>上一层 / 下一层</span
    ><span><kbd>←</kbd> <kbd>→</kbd></span> <span>隐藏材料 / 工具面板</span
    ><span><kbd>[</kbd> <kbd>]</kbd></span> <span>进入 / 退出专注视图</span><kbd>Tab</kbd>
    <span>适配建筑到画布</span><kbd>F</kbd> <span>打开本教程</span><kbd>?</kbd>
    <span>进入 / 退出第一人称</span><kbd>G</kbd> <span>第一人称：移动 / 升降 / 加速</span
    ><span>WASD / Space、Shift / Ctrl</span> <span>第一人称：删除 / 放置 / 选择扩选</span
    ><span>左键 / 右键 / Alt+左键</span> <span>第一人称：打开材料与工具，保留预览</span
    ><kbd>Esc</kbd> <span>暂停播放 / 取消预览 / 关闭弹窗</span><kbd>Esc</kbd>
  </div>
  <p class="muted">
    在输入框、下拉框或弹窗中，保留正常输入与键盘操作。Mac 可用 ⌘ 代替 Ctrl。Tab
    仅在画布或页面背景获得焦点时切换专注视图。
  </p>
  <div class="dialog-actions">
    <button class="primary" data-close-dialog="help-dialog">开始建造</button>
  </div>
</dialog>
`,g=e=>document.getElementById(e);class ue{constructor(t){this.viewer=t,this.play.onclick=()=>this.toggle(),this.slider.oninput=()=>{const a=Number(this.slider.value);this.stop(),this.seek(a)},this.number.onchange=()=>{const a=this.number.valueAsNumber;this.stop(),Number.isFinite(a)?this.seek(this.low+Math.round(a)-1):this.sync()},g("layer-prev").onclick=()=>this.step(-1),g("layer-next").onclick=()=>this.step(1),g("layer-reset").onclick=()=>{this.stop(),this.viewer.setLayer(1/0),this.sync()},this.speed.onchange=()=>{this.playing&&this.schedule()},this.sync()}low=0;high=0;available=!1;suspended=!0;timer=0;playing=!1;slider=g("layer");number=g("layer-number");play=g("layer-play");speed=g("layer-speed");update(t){const a=t.occupied_bounds;if(this.available=a!==null,this.low=a?.low[1]??0,this.high=a?.high[1]??0,this.slider.min=String(this.low),this.slider.max=String(this.high),this.number.max=String(this.high-this.low+1),!this.available)this.stop(),this.viewer.layer!==1/0&&this.viewer.setLayer(1/0);else if(this.viewer.layer!==1/0&&(this.viewer.layer<this.low||this.viewer.layer>this.high)){const i=Math.max(this.low,Math.min(this.high,this.viewer.layer));this.viewer.setLayer(i)}this.sync()}setBusy(t){this.suspended=t,t&&this.stop(),this.sync()}stop(){window.clearTimeout(this.timer),this.timer=0,this.playing=!1,this.sync()}toggle(){if(this.playing){this.stop();return}!this.available||this.suspended||this.low===this.high||(this.viewer.layer>=this.high&&this.seek(this.low),this.playing=!0,this.sync(),this.schedule())}step(t){this.stop(),this.seek(this.current+t)}get current(){return this.viewer.layer===1/0?this.high:this.viewer.layer}seek(t){if(!this.available||this.suspended)return;const a=Math.max(this.low,Math.min(this.high,Math.round(t)));this.viewer.layer!==a&&this.viewer.setLayer(a),this.sync()}schedule(){window.clearTimeout(this.timer),this.timer=window.setTimeout(()=>{this.seek(this.current+1),this.current>=this.high?this.stop():this.schedule()},600/Number(this.speed.value))}sync(){const t=!this.available||this.suspended;this.slider.value=String(this.current),this.slider.style.setProperty("--progress",`${this.high===this.low?100:(this.current-this.low)/(this.high-this.low)*100}%`),this.slider.setAttribute("aria-valuetext",`第 ${this.current-this.low+1} 层，Y ${this.current}`),this.number.value=String(this.available?this.current-this.low+1:0),g("layer-total").textContent=String(this.available?this.high-this.low+1:0),g("layer-label").textContent=this.available?`Y ${this.current}${this.viewer.layer===1/0?" · 全部显示":" · 逐层显示"}`:"暂无方块",this.play.textContent=this.playing?"Ⅱ":"▶",this.play.setAttribute("aria-label",this.playing?"暂停逐层建造":"播放逐层建造"),this.play.setAttribute("aria-pressed",String(this.playing)),this.play.disabled=t||this.low===this.high,this.slider.disabled=t||this.low===this.high,this.number.disabled=t,this.speed.disabled=t,g("layer-prev").disabled=t||this.current<=this.low,g("layer-next").disabled=t||this.current>=this.high,g("layer-reset").disabled=t}}const L=document.querySelector("#app");L.innerHTML=pe;const n=e=>document.getElementById(e),r=e=>n(e).value,x=(e,t)=>{n(e).value=t};let W=0;function d(e,t=!1){n("status").textContent=e,n("status").classList.toggle("error",t);const a=n("walk-feedback");a.textContent=e,a.classList.toggle("error",t),a.hidden=!1,clearTimeout(W),W=window.setTimeout(()=>a.hidden=!0,t?8e3:3500)}async function p(e,t,a){const i=await fetch(e,{method:a??(t===void 0?"GET":"POST"),headers:t===void 0?{}:{"Content-Type":"application/json"},body:t===void 0?void 0:JSON.stringify(t)}),s=await i.json();if(!i.ok)throw new Error(s.error?.message??s.detail??`请求失败 ${i.status}`);return s}const o=new ce(n("stage")),v=new ue(o);let u="",c=null,T=null,w={name:"minecraft:oak_planks",properties:{}},S=null,te="select",j=0,M=0,A=!1,U=null,k=null,H=null,ne=[];const he=new URLSearchParams(location.search),G=e=>{A=e,n("commit").disabled=e,n("preview").disabled=e,n("rename-submit").disabled=e,v.setBusy(e)},_=(e="")=>`/api/projects/${u}${e}`;function E(e){const t=e.split(",").map(a=>Number(a.trim()));if(t.length!==3||t.some(a=>!Number.isInteger(a)))throw new Error("坐标需要三个整数，例如 0,0,0");return t}function K(){const e=E(r("low")),t=E(r("high"));return{low:e.map((a,i)=>Math.min(a,t[i])),high:e.map((a,i)=>Math.max(a,t[i]))}}function I(){const e=r("group-filter");return e?{group:e}:{bounds:S??K()}}function R(e){S=e,o.showSelection(e),e&&(x("low",e.low.join(",")),x("high",e.high.join(","))),ae(),x("group-filter","")}function ae(){const e=o.walk.active?"Alt+点击选择或扩展选区；Shift 下降":"点击选中；Shift+点击扩展选区";n("selection-hint").textContent=S?`选区 ${S.low.join(",")} → ${S.high.join(",")} · ${e}`:e}let O="library";const P=new Map;function me(e){if(e&&!P.size){const t={"walk-menu-exit":["walk-toggle"],"walk-menu-actions":["undo","redo","save"],"walk-menu-settings":["walk-reach-control","compare"],"walk-panel-host":["library","inspector"],"walk-menu-layers":["slice-controls","workspace-details"],"walk-menu-notices":["warnings"]};for(const[a,i]of Object.entries(t))for(const s of i){const l=n(s),h=document.createComment(s);l.before(h),P.set(l,h),n(a).append(l)}}else if(!e){for(const[t,a]of P)a.replaceWith(t);P.clear()}}o.walk.onChange=()=>{const e=o.walk.active,t=o.walk.locked,a=L.classList.contains("pointer-locked"),i=L.classList.contains("first-person-mode");me(e),L.classList.toggle("first-person-mode",e),L.classList.toggle("pointer-locked",e&&t),L.classList.toggle("walk-menu-open",e&&!t),n("walk-toggle").textContent=e?"退出第一人称":"第一人称",n("walk-toggle").setAttribute("aria-pressed",String(e)),n("walk-crosshair").hidden=!e||!t,n("walk-hud").hidden=!e,n("walk-menu").hidden=!e||t,n("walk-status").hidden=!t,n("walk-reach-control").hidden=!e,n("camera-bar").hidden=e,document.querySelectorAll("[data-tool]").forEach(s=>s.disabled=e),ae(),N(),e&&a&&!t?n("walk-resume").focus():!e&&i&&n("walk-toggle").focus()};o.walk.onError=e=>d(e,!0);n("walk-toggle").onclick=()=>{o.walk.active?o.walk.exit():c&&(v.stop(),o.walk.enter(c.occupied_bounds?c.occupied_bounds.low[1]+1:0))};n("walk-resume").onclick=()=>void o.walk.lock();try{const e=Number(localStorage.getItem("workbench.walkReach"));Number.isFinite(e)&&e>0&&(o.walkReach=e)}catch{}x("walk-reach",String(o.walkReach));n("walk-reach").onchange=()=>{const e=n("walk-reach").valueAsNumber;if(!Number.isFinite(e)||e<=0){x("walk-reach",String(o.walkReach)),d("命中距离需要大于零。",!0);return}o.walkReach=e;try{localStorage.setItem("workbench.walkReach",String(e))}catch{}};function C(){U=null,o.clearGhosts(),n("preview-description").textContent="",n("cancel-preview").hidden=!0}function z(){return H?{...H,chunks:Object.fromEntries([...o.chunks].map(([e,t])=>[e,t.map(a=>[...a])])),models:Object.fromEntries(o.models),removed_chunks:[]}:null}async function $(e=!1){if(!u)return;const t=u,a=performance.now();let i,s,l=0;do if(i=await p(`/api/projects/${t}/render`,e?{}:o.versions),s=await p(`/api/projects/${t}`),++l>=3&&i.revision!==s.revision)throw new Error("场景正在连续更新，请稍后重新读取");while(i.revision!==s.revision);if(u!==t)return;e&&o.clearScene(),o.update(i),await o.whenReady(),H=i,c=s,be(c);const h=c.events;n("history").replaceChildren(...h.slice(0,8).map(f=>{const V=document.createElement("div"),le={edit:"编辑",import:"导入",rename:"重命名",undo:"撤销",redo:"重做"};return V.textContent=`r${f.revision} · ${le[f.kind]??f.kind} · ${f.changed} 格`,V})),n("stats").textContent=`${i.summary.blocks.toLocaleString()} 方块 · ${Object.keys(i.chunks).length} 分块更新 · ${Math.round(performance.now()-a)} ms`,n("warnings").hidden=i.warnings.length===0,n("warnings").textContent=i.warnings.map(f=>`${f.name.split(":")[1]}：${f.count} 格（${f.reason}）`).join("；")}function be(e){n("scene-name").textContent=e.name;const t=n("projects").selectedOptions[0];t&&(t.textContent=e.name),n("revision").textContent=`修订 ${e.revision}`,n("scene-meta").textContent=`${e.blocks.toLocaleString()} 个方块 · 修订 ${e.revision} · 已保存`,n("empty-message").hidden=e.blocks>0,n("undo").disabled=!e.undo_available,n("redo").disabled=!e.redo_available;const a=r("group-filter");n("group-filter").replaceChildren(new Option("当前选区",""),...Object.keys(e.groups).map(i=>new Option(`${i} · ${e.groups[i]}`,i))),e.groups[a]&&x("group-filter",a),n("group-tree").replaceChildren(...Object.entries(e.groups).map(([i,s])=>{const l=document.createElement("button");return l.textContent=`${i}  ${s}`,l.onclick=()=>{x("group-filter",i),o.showSelection(null),n("selection-hint").textContent=`分组：${i}${o.walk.active?" · Alt+点击扩展选区；Shift 下降":""}`},l})),v.update(e)}async function B(e){o.walk.exit();const t=await p("/api/projects"),a=n("projects");if(a.replaceChildren(...t.items.map(i=>new Option(i.name,i.project_id))),!t.items.length){const i=await p("/api/projects",{name:"我的建筑"});await B(i.project_id);return}u=e??u??"",t.items.some(i=>i.project_id===u)||(u=t.items[0].project_id),a.value=u,o.fitted=!1,o.layer=1/0,k=null,x("compare","current"),R(null),C(),await $(!0),history.replaceState({},"",`?project=${u}`)}async function q(){const e=new URLSearchParams({query:r("search"),category:r("category"),offset:String(j*24),limit:"24"}),t=await p(`/api/catalog?${e}`);M=t.total,n("catalog-total").textContent=String(M),n("page").textContent=`${j+1} / ${Math.max(1,Math.ceil(M/24))}`,n("prev-page").disabled=j===0,n("next-page").disabled=(j+1)*24>=M,n("materials").replaceChildren();for(const a of t.items){const i=document.createElement("button");i.className="material-card",i.dataset.name=a.name,i.setAttribute("aria-label",a.chinese_name);const s=document.createElement("img");s.alt="",s.width=56,s.height=56;const l=document.createElement("span");l.textContent=a.chinese_name;const h=document.createElement("small");if(h.textContent={static:"",special:"特殊",invisible:"不可见",missing:"缺资源"}[a.support.status],i.append(s,l,h),i.onclick=()=>void y(async()=>ie(a)),n("materials").append(i),a.support.status==="static"){const f=await p(`/api/material/${a.name.split(":")[1]}`);o.atlas=f.atlas,s.src=o.thumbnail(f,72)}else s.remove()}n("materials").querySelectorAll(".material-card").forEach(a=>a.classList.toggle("chosen",a.dataset.name===w.name))}async function ie(e){T=e,w={...e.default_state,properties:{...e.default_state.properties}},n("material-name").textContent=e.chinese_name,n("material-id").textContent=e.name,n("material-support").textContent=e.support.reason,n("properties").replaceChildren(...Object.entries(e.properties).map(([t,a])=>{const i=document.createElement("label");i.textContent=t;const s=document.createElement("select");return s.dataset.property=t,s.replaceChildren(...a.map(l=>new Option(l,l))),s.value=w.properties[t],s.onchange=()=>{w.properties[t]=s.value,Q().catch(l=>d(String(l),!0))},i.append(s),i})),n("materials").querySelectorAll(".material-card").forEach(t=>t.classList.toggle("chosen",t.dataset.name===e.name)),await Q(),d(`已选择 ${e.chinese_name}`)}let J=0;async function Q(){const e=++J;n("walk-material-name").textContent=T?.chinese_name??w.name;const t={facing:{north:"朝北",south:"朝南",west:"朝西",east:"朝东",up:"朝上",down:"朝下"},axis:{x:"沿 X 轴",y:"沿 Y 轴",z:"沿 Z 轴"},half:{top:"上半部",bottom:"下半部",upper:"上半部",lower:"下半部"},waterlogged:{true:"含水",false:"不含水"}};n("walk-material-properties").textContent=Object.entries(w.properties).filter(([l,h])=>h!==T?.default_state.properties[l]).map(([l,h])=>t[l]?.[h]??`${l}：${h}`).join(" · ");const a=n("walk-material-image");if(a.hidden=!0,T?.support.status!=="static")return;const i=new URLSearchParams({properties:JSON.stringify(w.properties)}),s=await p(`/api/material/${w.name.split(":")[1]}?${i}`);e===J&&(o.atlas=s.atlas,a.src=o.thumbnail(s,72),a.hidden=!1)}function oe(){const e=r("operation"),t={fill:'<label><input id="hollow" type="checkbox"> 仅填充外壳</label>',replace:'<p class="muted">将选区或分组替换为当前材料。</p>',delete:'<p class="muted">删除选区或分组中的方块。</p>',group:'<p class="muted">将选区归入“结果分组”。</p>',transform:'<label>位移 <input id="offset" value="0,0,0"></label><label>变换中心 <input id="origin" value="0,0,0"></label><label>旋转 <select id="rotation"><option>0</option><option>90</option><option>180</option><option>270</option></select></label><label>镜像 <select id="mirror"><option value="">无</option><option value="x">沿 X</option><option value="z">沿 Z</option></select></label><label><input id="copy" type="checkbox"> 保留原件，复制</label><label><input id="overwrite" type="checkbox"> 允许覆盖目标</label>',array:'<label>重复数 X,Y,Z <input id="count" value="3,1,1"></label><label>间距 X,Y,Z <input id="step" value="8,0,0"></label>',extrude:`<label>轮廓 X,Z（每行一个点）<textarea id="polygon">0,0
6,0
6,8
0,8</textarea></label><label>起始 Y <input id="base-y" type="number" value="0"></label><label>高度 <input id="height" type="number" value="4" min="1"></label>`,arc:'<label>中心 <input id="center" value="0,0,0"></label><label>半径 <input id="radius" type="number" value="8" min="1"></label><label>厚度 <input id="thickness" type="number" value="1" min="1"></label><label>高度 <input id="height" type="number" value="1" min="1"></label><div class="coordinates"><label>起始角 <input id="start-angle" type="number" value="0"></label><label>结束角 <input id="end-angle" type="number" value="360"></label></div>',roof:'<label>屋脊方向 <select id="ridge"><option value="z">沿 Z</option><option value="x">沿 X</option></select></label><label>最高起伏 <input id="height" type="number" value="4" min="1"></label><p class="muted">选区起点 Y 为檐口高度，使用当前材料。</p>',window:'<label>墙面法向 <select id="window-axis"><option value="z">Z（窗宽沿 X）</option><option value="x">X（窗宽沿 Z）</option></select></label><label>边框材料 <input id="frame" value="oak_log"></label><p class="muted">玻璃使用当前材料；选区必须为单格厚。</p>'};n("operation-fields").innerHTML=t[e]??"",C()}function se(){const e=r("operation"),t=S??K(),a=r("result-group")||"main",i={name:w.name,properties:{...w.properties}};switch(e){case"fill":return{op:e,bounds:t,state:i,group:a,hollow:n("hollow").checked};case"replace":return{op:e,selector:I(),state:i};case"delete":return{op:e,selector:I()};case"group":return{op:e,selector:I(),name:a};case"transform":return{op:e,selector:I(),origin:E(r("origin")),offset:E(r("offset")),rotation:Number(r("rotation")),mirror:r("mirror")||null,copy:n("copy").checked,overwrite:n("overwrite").checked,group:a};case"array":return{op:e,selector:I(),count:E(r("count")),step:E(r("step")),group:a};case"extrude":return{op:e,polygon:r("polygon").split(`
`).filter(Boolean).map(s=>{const l=s.split(",").map(Number);if(l.length!==2||l.some(h=>!Number.isInteger(h)))throw new Error("轮廓每行需要 X,Z 两个整数");return l}),base_y:Number(r("base-y")),height:Number(r("height")),state:i,group:a};case"arc":return{op:e,center:E(r("center")),radius:Number(r("radius")),thickness:Number(r("thickness")),height:Number(r("height")),start:Number(r("start-angle")),end:Number(r("end-angle")),state:i,group:a};case"roof":return{op:e,bounds:t,ridge_axis:r("ridge"),height:Number(r("height")),state:i,group:a};case"window":return{op:e,bounds:t,axis:r("window-axis"),frame:{name:r("frame")},glass:i,group:a};default:throw new Error("请选择设计工具")}}function X(e){if(!u||!c)throw new Error("请先选择项目");return{expected_revision:c.revision,request_id:crypto.randomUUID(),operations:e}}async function re(e){const t=X(e??[se()]),a=await p(_("/preview"),t);U=t,o.showGhosts(a.changes),n("preview-description").textContent=`将修改 ${a.changed.toLocaleString()} 格。绿色新增或替换，红色删除。${a.truncated?"预览显示前一万格。":""}`,n("cancel-preview").hidden=!1,d(`修改预览：${a.changed} 格，尚未提交`)}async function D(e){if(r("compare")==="before")throw new Error("先切回当前设计再编辑");const t=e?X(e):U??X([se()]);k=z();const a=await p(_("/edit"),t);C(),await $(),d(`已保存修订 ${a.revision}，修改 ${a.changed} 格`)}async function y(e){if(!A){G(!0);try{await e()}catch(t){d(t instanceof Error?t.message:String(t),!0)}finally{G(!1)}}}o.onHit=(e,t)=>void y(async()=>{if(!e||!c)return;if(r("compare")==="before")throw new Error("先切回当前设计");const a=o.walk.active?t.button===2?"place":t.altKey?"select":"erase":te;if(a==="select"){const i=e.ground?[e.position[0],0,e.position[2]]:e.position;(o.walk.active?t.altKey:t.shiftKey)&&S?R({low:S.low.map((s,l)=>Math.min(s,i[l])),high:S.high.map((s,l)=>Math.max(s,i[l]))}):R({low:i,high:i}),d(e.protected?"此格包含保留的实体内容；当前只能查看":`选中 ${i.join(",")}`)}else if(a==="place"){const i=e.position.map((s,l)=>s+e.normal[l]);if(o.walk.active&&o.occupied().has(i.join(",")))throw new Error("放置目标已有方块，请先删除或选择空格");await D([{op:"set",complete_beds:w.name.endsWith("_bed"),blocks:[{position:i,state:w,group:r("result-group")}]}])}else e.ground||await D([{op:"delete",selector:{bounds:{low:e.position,high:e.position}}}])});function b(e,t){n(e).onclick=()=>void y(t)}const Y=n("rename-dialog");n("rename-project").onclick=()=>{A||!c||(o.walk.locked&&document.exitPointerLock(),v.stop(),x("project-name",c.name),n("project-name").setCustomValidity(""),n("rename-error").textContent="",Y.showModal(),n("project-name").select())};n("project-name").oninput=()=>{n("project-name").setCustomValidity(""),n("rename-error").textContent=""};n("rename-form").onsubmit=e=>{e.preventDefault();const t=r("project-name").trim();if(!t){n("project-name").setCustomValidity("请输入设计名称"),n("project-name").reportValidity();return}if(t===c?.name){Y.close();return}y(async()=>{try{k=z(),await p(_(),{name:t,expected_revision:c.revision,request_id:crypto.randomUUID()},"PATCH"),C(),await $(),Y.close(),d(`已重命名为「${t}」并保存`)}catch(a){throw n("rename-error").textContent=a instanceof Error?a.message:String(a),a}})};n("help").onclick=()=>{o.walk.locked&&document.exitPointerLock(),v.stop(),n("help-dialog").showModal()};document.querySelectorAll("[data-close-dialog]").forEach(e=>{e.onclick=()=>n(e.dataset.closeDialog).close()});function ge(){const e={library:innerWidth>780,inspector:innerWidth>780};try{const t=JSON.parse(localStorage.getItem("workbench.panels")??"null");return t&&typeof t.library=="boolean"&&typeof t.inspector=="boolean"?t:e}catch{return e}}let m=ge(),Z=null;function N(){for(const t of["library","inspector"]){const a=o.walk.active?!o.walk.locked&&O===t:m[t];n(t).hidden=!a,n("workbench-layout").classList.toggle(`${t}-hidden`,!m[t]),n(`toggle-${t}`).setAttribute("aria-expanded",String(m[t]))}const e=!m.library&&!m.inspector;if(n("focus-mode").setAttribute("aria-pressed",String(e)),n("focus-mode").textContent=e?"退出专注":"专注",document.querySelectorAll("[data-walk-panel]").forEach(t=>{t.setAttribute("aria-pressed",String(t.dataset.walkPanel===O))}),n("walk-menu-layers").hidden=O!=="inspector",!o.walk.active)try{localStorage.setItem("workbench.panels",JSON.stringify(m))}catch{}}for(const e of["library","inspector"])n(`toggle-${e}`).onclick=()=>{if(o.walk.active){O=e,o.walk.locked&&document.exitPointerLock(),N();return}Z=null,m[e]=!m[e],N()};document.querySelectorAll("[data-walk-panel]").forEach(e=>{e.onclick=()=>{O=e.dataset.walkPanel,N()}});n("focus-mode").onclick=()=>{o.walk.active||(!m.library&&!m.inspector?(m=Z??{library:!0,inspector:!0},Z=null):(Z={...m},m={library:!1,inspector:!1}),N())};N();document.addEventListener("visibilitychange",()=>{document.hidden&&v.stop()});b("new-project",async()=>{const e=prompt("建筑名称","新建筑");if(!e)return;const t=await p("/api/projects",{name:e});await B(t.project_id),d("新项目已创建")});n("projects").onchange=()=>void y(async()=>{await B(r("projects")),d("项目已打开")});b("save",async()=>{await $(),d(`已保存并重新读取，修订 ${c?.revision}`)});for(const e of["undo","redo"])b(e,async()=>{k=z(),await p(_(`/history/${e}`),{expected_revision:c.revision,request_id:crypto.randomUUID()}),C(),await $(),d(e==="undo"?"已撤销并保存":"已重做并保存")});b("preview",()=>re());b("commit",()=>D());b("cancel-preview",async()=>C());b("select-bounds",async()=>{R(K()),d("选区已更新")});n("operation").onchange=oe;n("compare").onchange=()=>void y(async()=>{if(C(),r("compare")==="before"){if(!k)throw x("compare","current"),new Error("还没有可对比的上次修改");o.update({...k,removed_chunks:Object.keys(o.versions).filter(e=>!k.chunks[e])}),await o.whenReady(),v.update(k.summary),d(`查看修改前 r${k.revision}`)}else await $(!0),d("查看当前设计")});document.querySelectorAll("[data-tool]").forEach(e=>e.onclick=()=>{te=e.dataset.tool,document.querySelectorAll("[data-tool]").forEach(t=>t.classList.toggle("active",t===e))});document.querySelectorAll("[data-view]").forEach(e=>e.onclick=()=>{o.view(e.dataset.view),document.querySelectorAll("[data-view]").forEach(t=>t.setAttribute("aria-pressed",String(t===e)))});n("fit").onclick=()=>{c?.occupied_bounds&&o.fit(c.occupied_bounds)};let ee=0;n("search").oninput=()=>{clearTimeout(ee),ee=window.setTimeout(()=>{j=0,y(q)},300)};n("category").onchange=()=>{j=0,y(q)};b("prev-page",async()=>{j=Math.max(0,j-1),await q()});b("next-page",async()=>{j++,await q()});n("import").onclick=()=>n("import-file").click();n("import-file").onchange=()=>void y(async()=>{const e=n("import-file").files?.[0];if(!e||!c)return;const t=new FormData;t.set("file",e),t.set("expected_revision",String(c.revision)),t.set("request_id",crypto.randomUUID()),k=z();const a=await fetch(_("/import"),{method:"POST",body:t}),i=await a.json();if(!a.ok)throw new Error(i.error?.message??"导入失败");o.fitted=!1,o.layer=1/0,await $(!0),d(`导入完成：${i.import_report.blocks.toLocaleString()} 方块，特殊内容已保留`),n("import-file").value=""});b("export",async()=>{const e=await fetch(_("/export"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_revision:c.revision})});if(!e.ok){const s=await e.json();throw new Error(s.error?.message??"导出失败")}const t=await e.blob(),a=URL.createObjectURL(t),i=document.createElement("a");i.href=a,i.download=`${c.name}-r${c.revision}.litematic`,i.click(),URL.revokeObjectURL(a),d("蓝图已导出，方块状态与保留内容已写入")});b("check",async()=>{const e=await p(_("/consistency"));ne=e.proposals,n("check-result").textContent=`${e.issues.length} 个部件问题，${e.proposals.length} 个连接建议。${e.limitations.join("；")}`,n("apply-rules").hidden=!e.proposals.length});b("apply-rules",()=>re([{op:"set",blocks:ne}]));b("cabin",async()=>{await D([{op:"fill",bounds:{low:[0,0,0],high:[8,0,10]},state:{name:"oak_planks"},group:"floor"},{op:"fill",bounds:{low:[0,1,0],high:[8,4,10]},state:{name:"oak_planks"},group:"walls",hollow:!0},{op:"fill",bounds:{low:[1,4,1],high:[7,4,9]},state:{name:"air"}},{op:"fill",bounds:{low:[4,1,0],high:[4,2,0]},state:{name:"air"}},{op:"roof",bounds:{low:[-1,5,-1],high:[9,5,11]},state:{name:"spruce_stairs"},ridge_axis:"z",height:6,group:"roof"},{op:"window",bounds:{low:[1,1,0],high:[3,3,0]},axis:"z",frame:{name:"oak_log"},glass:{name:"glass"},group:"windows"},{op:"window",bounds:{low:[5,1,0],high:[7,3,0]},axis:"z",frame:{name:"oak_log"},glass:{name:"glass"},group:"windows"},{op:"set",blocks:[{position:[4,1,0],state:{name:"oak_door",properties:{half:"lower",facing:"north"}},group:"door"},{position:[4,2,0],state:{name:"oak_door",properties:{half:"upper",facing:"north"}},group:"door"}]}]),o.fitted=!1,await $(!0),d("木屋起稿完成，可继续自由编辑")});document.addEventListener("keydown",e=>{const t=e.target instanceof HTMLElement?e.target:null;if(e.defaultPrevented||e.isComposing||e.repeat||e.altKey||document.querySelector("dialog[open]")||de(t))return;const a=e.key.toLowerCase();if(o.walk.active&&[" ","shift","control"].includes(a)||t?.closest("button")&&[" ","arrowleft","arrowright"].includes(a))return;if(e.ctrlKey||e.metaKey){const s=a==="z"?e.shiftKey?"redo":"undo":a==="y"?"redo":a==="s"?"save":"";s&&(e.preventDefault(),n(s).click());return}const i={" ":()=>v.toggle(),arrowleft:()=>v.step(-1),arrowright:()=>v.step(1),"[":()=>n("toggle-library").click(),"]":()=>n("toggle-inspector").click(),f:()=>n("fit").click(),g:()=>n("walk-toggle").click(),f2:()=>n("rename-project").click(),"?":()=>n("help").click(),escape:()=>{v.stop(),C()}};["1","2","3"].includes(a)?(e.preventDefault(),document.querySelector(`[data-tool="${{1:"select",2:"place",3:"erase"}[a]}"]`)?.click()):a==="tab"&&(t===document.body||t?.tagName==="CANVAS"||t?.id==="stage"||t?.id==="app")?(e.preventDefault(),n("focus-mode").click()):i[a]&&(e.preventDefault(),i[a]())});Object.defineProperty(window,"workbench",{value:{viewer:o,get project(){return u},get summary(){return c},get selection(){return S},get busy(){return A}},writable:!1});oe();y(async()=>{const e=await p("/api/info");if(n("version").textContent=`Java ${e.minecraft_version}`,!e.resources_ready)throw new Error("尚未配置素材。先运行 design-workbench resources setup，再重启服务。");await o.initializeTexture(),await B(he.get("project")??void 0),await q();const t=await p("/api/catalog?query=oak_planks&limit=1");t.items[0]&&await ie(t.items[0]),d("工作台就绪 · 所有修改自动保存")});let F=!1;window.setInterval(()=>{if(F||A||document.hidden||!u||!c||r("compare")==="before")return;F=!0;const e=u;p(`/api/projects/${e}`).then(async t=>{A||u!==e||t.revision===c?.revision||await y(async()=>{await $(),d(U?`已读取外部编辑 r${c?.revision}；当前预演基于旧修订，请重新预演`:`已读取外部编辑 r${c?.revision}`)})}).catch(t=>{console.warn("读取外部修订失败",t)}).finally(()=>{F=!1})},1500);
