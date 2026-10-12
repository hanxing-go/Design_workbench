import{h as Ce,i as Se}from"./minecraftUI-Cl_zRL2Y.js";import{V as je,t as Ee}from"./viewer-BFSwvv6A.js";import"./three.module-BKyUEcGm.js";const Ae=`<header>
  <a class="workbench-home-link" href="/" aria-label="返回首页" title="返回首页">⌂</a>
  <div class="brand">
    <span class="brand-mark" data-icon="grass" aria-hidden="true"></span>
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
  <button id="ai-tasks" aria-controls="ai-panel">AI 任务</button>
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
      <h3>画</h3>
      <select id="painting-variant" aria-label="画的图案"></select>
      <button id="choose-painting">选择画</button>
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
      <ul id="check-issues" class="consistency-issues" hidden></ul>
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
`,_=e=>document.getElementById(e);class Ie{constructor(t){this.viewer=t,this.play.onclick=()=>this.toggle(),this.slider.oninput=()=>{const n=Number(this.slider.value);this.stop(),this.seek(n)},this.number.onchange=()=>{const n=this.number.valueAsNumber;this.stop(),Number.isFinite(n)?this.seek(this.low+Math.round(n)-1):this.sync()},_("layer-prev").onclick=()=>this.step(-1),_("layer-next").onclick=()=>this.step(1),_("layer-reset").onclick=()=>{this.stop(),this.viewer.setLayer(1/0),this.sync()},this.speed.onchange=()=>{this.playing&&this.schedule()},this.sync()}low=0;high=0;available=!1;suspended=!0;timer=0;playing=!1;slider=_("layer");number=_("layer-number");play=_("layer-play");speed=_("layer-speed");update(t){const n=t.occupied_bounds;if(this.available=n!==null,this.low=n?.low[1]??0,this.high=n?.high[1]??0,this.slider.min=String(this.low),this.slider.max=String(this.high),this.number.max=String(this.high-this.low+1),!this.available)this.stop(),this.viewer.layer!==1/0&&this.viewer.setLayer(1/0);else if(this.viewer.layer!==1/0&&(this.viewer.layer<this.low||this.viewer.layer>this.high)){const i=Math.max(this.low,Math.min(this.high,this.viewer.layer));this.viewer.setLayer(i)}this.sync()}setBusy(t){this.suspended=t,t&&this.stop(),this.sync()}stop(){window.clearTimeout(this.timer),this.timer=0,this.playing=!1,this.sync()}toggle(){if(this.playing){this.stop();return}!this.available||this.suspended||this.low===this.high||(this.viewer.layer>=this.high&&this.seek(this.low),this.playing=!0,this.sync(),this.schedule())}step(t){this.stop(),this.seek(this.current+t)}get current(){return this.viewer.layer===1/0?this.high:this.viewer.layer}seek(t){if(!this.available||this.suspended)return;const n=Math.max(this.low,Math.min(this.high,Math.round(t)));this.viewer.layer!==n&&this.viewer.setLayer(n),this.sync()}schedule(){window.clearTimeout(this.timer),this.timer=window.setTimeout(()=>{this.seek(this.current+1),this.current>=this.high?this.stop():this.schedule()},600/Number(this.speed.value))}sync(){const t=!this.available||this.suspended;this.slider.value=String(this.current),this.slider.style.setProperty("--progress",`${this.high===this.low?100:(this.current-this.low)/(this.high-this.low)*100}%`),this.slider.setAttribute("aria-valuetext",`第 ${this.current-this.low+1} 层，Y ${this.current}`),this.number.value=String(this.available?this.current-this.low+1:0),_("layer-total").textContent=String(this.available?this.high-this.low+1:0),_("layer-label").textContent=this.available?`Y ${this.current}${this.viewer.layer===1/0?" · 全部显示":" · 逐层显示"}`:"暂无方块",this.play.textContent=this.playing?"Ⅱ":"▶",this.play.setAttribute("aria-label",this.playing?"暂停逐层建造":"播放逐层建造"),this.play.setAttribute("aria-pressed",String(this.playing)),this.play.disabled=t||this.low===this.high,this.slider.disabled=t||this.low===this.high,this.number.disabled=t,this.speed.disabled=t,_("layer-prev").disabled=t||this.current<=this.low,_("layer-next").disabled=t||this.current>=this.high,_("layer-reset").disabled=t}}const Ne=`<aside id="ai-panel" class="ai-panel" aria-label="AI 设计任务" hidden>
  <div class="ai-heading">
    <h2>AI 设计任务</h2>
    <button id="ai-close" aria-label="关闭 AI 任务面板">×</button>
  </div>
  <p class="muted">
    由你正在使用的 AI 执行。创建任务后，将任务编号交给它，即可在这里查看进度、确认改稿和保留结果。
  </p>
  <div class="ai-toolbar">
    <select id="ai-runs" aria-label="选择设计任务"></select
    ><button id="ai-new">新任务</button>
  </div>
  <form id="ai-create-form">
    <label
      >设计需求<textarea
        id="ai-prompt"
        required
        maxlength="16000"
        placeholder="描述想建造的建筑，以及尺寸、材料和必须保留的部分"
      ></textarea>
    </label>
    <label
      >模型名称（可选）<input id="ai-model" maxlength="256" placeholder="用于记录本次使用的模型"
    /></label>
    <fieldset id="ai-budget">
      <legend>任务预算</legend>
      <div class="ai-budget-grid">
        <label
          >工具次数<input
            id="ai-budget-calls"
            type="number"
            min="1"
            max="4096"
            value="256"
            required
        /></label>
        <label
          >模型调用<input
            id="ai-budget-model-calls"
            type="number"
            min="1"
            max="4096"
            value="64"
            required
        /></label>
        <label
          >时长（分钟）<input
            id="ai-budget-minutes"
            type="number"
            min="1"
            max="1440"
            value="30"
            required
        /></label>
        <label
          >Tokens<input id="ai-budget-tokens" type="number" min="1" value="3000000" required
        /></label>
        <label
          >修改批次<input
            id="ai-budget-revisions"
            type="number"
            min="1"
            max="1024"
            value="64"
            required
        /></label>
        <label
          >费用上限（USD，可选）<input
            id="ai-budget-cost"
            type="number"
            min="0.0001"
            step="any"
            placeholder="不设费用上限"
        /></label>
      </div>
    </fieldset>
    <label class="ai-checkbox"
      ><input id="ai-auto-build" type="checkbox" />空项目允许自动生成初稿，后续改稿仍需确认</label
    >
    <button id="ai-create" class="primary" type="submit">创建任务</button>
  </form>
  <section id="ai-detail" hidden>
    <h3 id="ai-run-title"></h3>
    <label>任务编号<input id="ai-run-id" readonly aria-label="AI 任务编号" /></label>
    <p id="ai-state" role="status" aria-live="polite"></p>
    <p id="ai-progress"></p>
    <div id="ai-usage" class="ai-usage"></div>
    <p id="ai-usage-source" class="muted"></p>
    <div class="ai-actions">
      <button id="ai-cancel">取消任务</button><button id="ai-resume" hidden>继续任务</button
      ><button id="ai-extend" hidden>调整预算并继续</button
      ><button id="ai-finish" hidden>标记完成</button>
    </div>
    <form id="ai-extend-form" hidden>
      <p>已消耗的用量会保留。增加预算后，AI 需要读取当前场景再继续。</p>
      <div id="ai-extend-fields"></div>
      <button type="submit" class="primary">保存预算并继续</button>
    </form>
    <section id="ai-proposal" class="ai-proposal" hidden>
      <h3>待确认的改稿</h3>
      <p id="ai-proposal-message"></p>
      <p id="ai-proposal-count"></p>
      <div class="ai-actions">
        <button id="ai-view-proposal">在画布查看</button
        ><button id="ai-approve" class="primary">确认并应用</button
        ><button id="ai-reject">拒绝修改</button>
      </div>
    </section>
    <h3>候选稿</h3>
    <form id="ai-candidate-form">
      <label
        >候选稿名称<input
          id="ai-candidate-name"
          required
          maxlength="128"
          placeholder="例如：初稿、调整树冠后" /></label
      ><label
        >评价与后续要求<textarea
          id="ai-candidate-feedback"
          maxlength="4000"
          placeholder="保留这稿的原因，或下一步想改什么"
        ></textarea></label
      ><button id="ai-save-candidate" type="submit">保存当前工程为候选稿</button>
    </form>
    <div id="ai-candidates"></div>
    <h3>运行记录</h3>
    <ol id="ai-events" class="ai-events"></ol>
  </section>
  <p id="ai-error" role="alert" class="error"></p>
</aside>
`,X={active:"进行中",awaiting_approval:"等待确认改稿",cancelled:"已取消",failed:"发生错误",budget_exceeded:"预算已用完",interrupted:"运行已中断",succeeded:"已完成",planning:"理解需求与规划",building:"生成初稿",reviewing:"查看实际画面",revising:"局部改稿",exporting:"保存与导出"};class Pe{constructor(t){this.hooks=t,document.querySelector("#app").insertAdjacentHTML("beforeend",Ne),this.node=this.el("ai-panel"),this.el("ai-tasks").onclick=()=>{this.node.hidden=!this.node.hidden,this.node.hidden||this.safe(async()=>{await this.load()})},this.el("ai-close").onclick=()=>{this.node.hidden=!0},this.el("ai-new").onclick=()=>{this.el("ai-create-form").hidden=!1},this.el("ai-runs").onchange=()=>void this.safe(async()=>{const i=this.value("ai-runs");this.run=i?await this.api(`/api/design-runs/${i}`):null,this.render()}),this.el("ai-create-form").onsubmit=i=>{i.preventDefault(),this.safe(async()=>{const s=this.hooks.summary();if(!s)throw new Error("请先选择项目");const r=await this.api(`/api/projects/${this.hooks.project()}/design-runs`,{project:this.hooks.project(),expected_revision:s.revision,request_id:crypto.randomUUID(),prompt:this.value("ai-prompt").trim(),model:this.value("ai-model").trim(),auto_build:this.el("ai-auto-build").checked,budget:this.budget("")});await this.load(r.run_id),this.hooks.notice("任务已创建，将编号交给 AI 后即可开始")})},this.el("ai-cancel").onclick=()=>void this.act("cancel"),this.el("ai-resume").onclick=()=>void this.act("resume"),this.el("ai-finish").onclick=()=>void this.act("finish",{outcome:"succeeded",message:"用户确认候选稿可用，任务完成"}),this.el("ai-extend").onclick=()=>{if(!this.run)return;const i=this.el("ai-budget").cloneNode(!0);i.id="ai-extended-budget",i.querySelectorAll("input").forEach(r=>{r.id+="-extend"}),this.el("ai-extend-fields").replaceChildren(i);const s=this.run.budget;for(const[r,p]of Object.entries({calls:s.tool_calls,"model-calls":s.model_calls,minutes:Math.ceil(s.seconds/60),tokens:s.tokens,revisions:s.revisions,cost:s.cost_usd??""}))this.el(`ai-budget-${r}-extend`).value=String(p);this.el("ai-extend-form").hidden=!1},this.el("ai-extend-form").onsubmit=i=>{i.preventDefault(),this.act("resume",{budget:this.budget("-extend")})},this.el("ai-view-proposal").onclick=()=>{this.run?.pending&&(this.displayedProposal=this.run.pending.proposal_id,this.hooks.preview(this.run.pending.preview.changes),this.node.hidden=!0,this.hooks.notice("AI 改稿已显示在画布；打开 AI 任务面板确认或拒绝"))},this.el("ai-approve").onclick=()=>void this.decide(!0),this.el("ai-reject").onclick=()=>void this.decide(!1),this.el("ai-candidate-form").onsubmit=i=>{i.preventDefault(),this.safe(async()=>{!this.run||!this.hooks.summary()||(await this.api(`/api/design-runs/${this.run.run_id}/candidates`,{...this.action(),name:this.value("ai-candidate-name").trim(),feedback:this.value("ai-candidate-feedback").trim(),expected_revision:this.hooks.summary().revision}),this.el("ai-candidate-name").value="",await this.poll(),this.hooks.notice("候选稿已保存，后续修改不会改变这份工程"))})};const n=window.setInterval(()=>{!document.hidden&&!this.loading&&this.poll().catch(i=>{this.el("ai-error").textContent=i instanceof Error?i.message:"读取任务失败"})},1500);window.addEventListener("pagehide",()=>window.clearInterval(n),{once:!0})}run=null;loading=!1;polling=!1;generation=0;displayedProposal="";node;el(t){return document.getElementById(t)}value(t){return this.el(t).value}async api(t,n){const i=await fetch(t,{method:n===void 0?"GET":"POST",headers:n===void 0?{}:{"Content-Type":"application/json"},body:n===void 0?void 0:JSON.stringify(n)}),s=await i.json();if(!i.ok||s.error)throw new Error(s.error?.message??`请求失败 ${i.status}`);return s}action(){return{run_id:this.run.run_id,request_id:crypto.randomUUID()}}budget(t){const n=i=>Number(this.value(`ai-budget-${i}${t}`));return{tool_calls:n("calls"),model_calls:n("model-calls"),seconds:n("minutes")*60,tokens:n("tokens"),revisions:n("revisions"),cost_usd:this.value(`ai-budget-cost${t}`)?n("cost"):null}}async safe(t){if(!this.loading){this.loading=!0,this.el("ai-error").textContent="",this.node.querySelectorAll("button").forEach(n=>n.disabled=!0);try{await t()}catch(n){const i=n instanceof Error?n.message:"操作失败";this.el("ai-error").textContent=i,this.hooks.notice(i,!0),await this.poll().catch(()=>{})}finally{this.loading=!1,this.node.querySelectorAll("button").forEach(n=>n.disabled=!1),this.render()}}}async act(t,n={}){await this.safe(async()=>{this.run&&(this.run=await this.api(`/api/design-runs/${this.run.run_id}/${t}`,{...this.action(),...n}),this.el("ai-extend-form").hidden=!0,this.render())})}async decide(t){await this.safe(async()=>{this.run?.pending&&(this.run=await this.api(`/api/design-runs/${this.run.run_id}/decision`,{...this.action(),proposal_id:this.run.pending.proposal_id,approve:t}),this.hooks.preview(null),this.displayedProposal="",await this.hooks.refresh(),this.render())})}async load(t){const n=this.hooks.project(),i=++this.generation;if(this.run=null,this.displayedProposal&&this.hooks.preview(null),this.displayedProposal="",!n)return;const s=await this.api(`/api/projects/${n}/design-runs`);if(i!==this.generation||n!==this.hooks.project())return;const r=this.el("ai-runs");r.replaceChildren(...s.items.map(l=>new Option(`${X[l.status]??l.status} · ${l.prompt.slice(0,25)}`,l.run_id))),this.run=s.items.find(l=>l.run_id===t)??s.items[0]??null,this.run&&(r.value=this.run.run_id),this.el("ai-create-form").hidden=!!this.run,this.el("ai-extend-form").hidden=!0;const p=this.el("ai-auto-build");p.disabled=!!this.hooks.summary()?.blocks,p.disabled&&(p.checked=!1),this.render()}async poll(){if(this.polling||!this.run)return;this.polling=!0;const t=this.run,n=this.generation;try{const i=await this.api(`/api/design-runs/${t.run_id}`);if(n!==this.generation||this.run?.run_id!==t.run_id)return;this.run=i,this.render()}finally{this.polling=!1}}render(){const t=this.run;if(this.el("ai-detail").hidden=!t,this.el("ai-tasks").textContent=t?.pending?"AI 任务 · 待确认":"AI 任务",!t)return;this.el("ai-run-title").textContent=t.prompt,this.el("ai-run-id").value=t.run_id,this.el("ai-state").textContent=`${X[t.status]??t.status} · ${X[t.stage]??t.stage}`,this.el("ai-progress").textContent=t.message;const n=this.el("ai-runs").selectedOptions[0];n&&(n.textContent=`${X[t.status]??t.status} · ${t.prompt.slice(0,25)}`);const i=t.usage,s=l=>l.toLocaleString(),r=i.source?`${s(i.input_tokens+i.output_tokens)} / ${s(t.budget.tokens)}`:`尚未报告 / ${s(t.budget.tokens)}`;this.el("ai-usage").replaceChildren(...[`工具 ${i.tool_calls} / ${t.budget.tool_calls} 次`,`模型调用 ${i.source?i.model_calls:"尚未报告"} / ${t.budget.model_calls} 次`,`时长 ${(t.elapsed_seconds/60).toFixed(1)} / ${(t.budget.seconds/60).toFixed(1)} 分钟`,`修改 ${i.revisions} / ${t.budget.revisions} 批`,`Tokens ${r}`,`费用 ${i.cost_usd===null?"尚未报告":"$"+i.cost_usd.toFixed(4)}${t.budget.cost_usd===null?"":" / $"+t.budget.cost_usd}`].map(l=>{const b=document.createElement("span");return b.textContent=l,b})),this.el("ai-usage-source").textContent=i.source?`模型：${t.model||"未记录"}；用量来源：${i.source}。缓存输入包含在输入总量中。`:"外部 AI 尚未回报模型用量；工具与时长预算由工作台计量。";const p=["cancelled","failed","budget_exceeded","interrupted"].includes(t.status);this.el("ai-cancel").hidden=!["active","awaiting_approval"].includes(t.status),this.el("ai-resume").hidden=!p||t.status==="budget_exceeded",this.el("ai-extend").hidden=!p,this.el("ai-finish").hidden=t.status!=="active"||!t.candidates.length,this.el("ai-proposal").hidden=!t.pending||t.status!=="awaiting_approval",t.pending?(this.el("ai-proposal-message").textContent=t.pending.explanation,this.el("ai-proposal-count").textContent=`基于 r${t.pending.expected_revision}，将修改 ${s(t.pending.preview.changed)} 格。${t.pending.preview.truncated?"画布预演显示前 10,000 格。":""}`):this.displayedProposal&&(this.hooks.preview(null),this.displayedProposal=""),this.el("ai-candidates").replaceChildren(...t.candidates.map(l=>{const b=document.createElement("article");b.className="ai-candidate";const $=document.createElement("strong");$.textContent=`${l.name} · r${l.revision}`;const B=document.createElement("p");B.textContent=l.feedback;const u=document.createElement("div");u.className="ai-candidate-images";for(const y of l.screenshots??[])for(const w of y.images){const v=document.createElement("a");v.href=w.url,v.target="_blank",v.rel="noopener";const O=document.createElement("img");O.src=w.url,O.alt=`${l.name}，修订 ${l.revision} 的实际截图`,O.loading="lazy",v.append(O),u.append(v)}const A=document.createElement("button");A.textContent="打开副本继续修改",A.onclick=()=>void this.safe(async()=>{const y=await this.api(`/api/design-runs/${t.run_id}/candidates/${l.candidate_id}/open`,{request_id:crypto.randomUUID()});await this.hooks.openProject(y.project_id)});const f=document.createElement("a");return f.href=`/api/design-runs/${t.run_id}/candidates/${l.candidate_id}/download`,f.textContent="下载工程",b.append($,B,u,A,f),b})),this.el("ai-events").replaceChildren(...t.events.slice(-20).reverse().map(l=>{const b=document.createElement("li");return b.textContent=`${new Date(l.at*1e3).toLocaleTimeString()} · ${l.message}`,b}))}}const Y={facing:"方向",half:"上下位置",shape:"形态",type:"类型",waterlogged:"含水",axis:"轴向",open:"打开",hinge:"门轴",powered:"激活",rotation:"旋转",north:"北侧连接",east:"东侧连接",south:"南侧连接",west:"西侧连接",face:"附着面",hanging:"悬挂",part:"部件",persistent:"保持叶片"},ae={north:"北 ↑",east:"东 →",south:"南 ↓",west:"西 ←",up:"向上",down:"向下",top:"上半部",bottom:"下半部",upper:"上半部",lower:"下半部",double:"双层",straight:"直线",inner_left:"内左拐角",inner_right:"内右拐角",outer_left:"外左拐角",outer_right:"外右拐角",true:"是",false:"否",left:"左侧",right:"右侧",single:"单个",floor:"地面",wall:"墙面",ceiling:"天花板",head:"床头",foot:"床尾",none:"不连接",low:"低墙",tall:"高墙",x:"东西",y:"上下",z:"南北"};class Le{constructor(t,n,i){this.container=t,this.change=n,this.thumbnail=i}automatic=!0;material=null;state={name:"",properties:{}};generation=0;advancedOpen=!1;show(t,n){this.material=t,this.state=n,this.automatic=!0,this.advancedOpen=!1,this.draw()}choose(t,n){this.state.properties[t]=n,this.automatic=!1,this.change(this.state,this.automatic),this.draw()}draw(){if(!this.material)return;const t=this.material,n=++this.generation,i=document.createElement("label");i.className="placement-mode";const s=document.createElement("input");s.type="checkbox",s.id="automatic-placement",s.checked=this.automatic,s.onchange=()=>{this.automatic=s.checked,this.change(this.state,this.automatic),this.draw()},i.append(s,"自动朝向与贴合");const r=document.createElement("p");r.className="placement-hint",r.textContent=this.automatic?"按点击位置和视角放置；连接与拐角随邻居更新。":"按所选形态放置，本次保留手动属性。重新勾选可恢复自动放置。",this.container.replaceChildren(i,r);const p=document.createElement("img");p.className="material-state-preview",p.alt="当前材料形态预览",this.container.append(p);const l=(u,A)=>{this.thumbnail(A).then(f=>{n===this.generation&&(u.src=f)}).catch(()=>{n===this.generation&&(u.hidden=!0)})};t.support.status==="static"?l(p,this.state):p.hidden=!0;const b=t.name.endsWith("_stairs")?["shape","half","facing"]:t.name.endsWith("_slab")?["type"]:t.properties.facing?["facing"]:[];for(const u of b){const A=t.properties[u];if(!A)continue;const f=document.createElement("fieldset");f.className="material-variants";const y=document.createElement("legend");y.textContent=Y[u]??u,f.append(y);for(const w of A){const v=document.createElement("button");if(v.type="button",v.dataset.variantProperty=u,v.dataset.variantValue=w,v.setAttribute("aria-pressed",String(this.state.properties[u]===w)),v.title=`${Y[u]??u}：${ae[w]??w}`,u!=="facing"&&t.support.status==="static"){const O=document.createElement("img");O.alt="",v.append(O),l(O,{name:this.state.name,properties:{...this.state.properties,[u]:w}})}v.append(ae[w]??w),v.onclick=()=>this.choose(u,w),f.append(v)}this.container.append(f)}const $=document.createElement("details");$.className="material-advanced",$.open=this.advancedOpen,$.ontoggle=()=>{this.advancedOpen=$.open};const B=document.createElement("summary");B.textContent="高级属性",$.append(B);for(const[u,A]of Object.entries(t.properties)){const f=document.createElement("label");f.textContent=Y[u]??u,f.title=u;const y=document.createElement("select");y.dataset.property=u,y.setAttribute("aria-label",Y[u]??u),y.replaceChildren(...A.map(w=>new Option(ae[w]??w,w))),y.value=this.state.properties[u],y.onchange=()=>this.choose(u,y.value),f.append(y),$.append(f)}this.container.append($)}}const T=document.querySelector("#app");T.innerHTML=Ae;Ce(T);Se();document.title="Design Workbench · 建筑设计";const a=e=>document.getElementById(e),c=e=>a(e).value,P=(e,t)=>{a(e).value=t};let de=0;function m(e,t=!1){a("status").textContent=e,a("status").classList.toggle("error",t);const n=a("walk-feedback");n.textContent=e,n.classList.toggle("error",t),n.hidden=!1,clearTimeout(de),de=window.setTimeout(()=>n.hidden=!0,t?8e3:3500)}async function g(e,t,n){h&&/^\/api\/(catalog|material\/)/.test(e)&&(e+=(e.includes("?")?"&":"?")+"project="+encodeURIComponent(h));const i=await fetch(e,{method:n??(t===void 0?"GET":"POST"),headers:t===void 0?{}:{"Content-Type":"application/json"},body:t===void 0?void 0:JSON.stringify(t)}),s=await i.json();if(!i.ok)throw new Error(s.error?.message??s.detail??`请求失败 ${i.status}`);return s}const o=new je(a("stage")),S=new Ie(o);let h="",d=null,J=null,C={name:"minecraft:oak_planks",properties:{}},L=null,be="select",N=0,K=0,F=!1,ne=null,I=null,U=null,Z=null,ge=[],fe=-1;const le=new Le(a("properties"),e=>{C=e,j(),ye().catch(t=>m(String(t),!0))},async e=>{const t=h,n=U?.resource_hash,i=new URLSearchParams({properties:JSON.stringify(e.properties)}),s=await g(`/api/material/${e.name.split(":")[1]}?${i}`);if(t!==h||n!==U?.resource_hash)throw new Error("材料预览请求已过期");return o.atlas=s.atlas,o.thumbnail(s,96)}),pe=new URLSearchParams(location.search),ue=e=>{F=e,a("properties").inert=e,a("search").disabled=e,a("category").disabled=e,a("projects").disabled=e,a("materials").querySelectorAll(".material-card").forEach(t=>{t.disabled=e}),a("commit").disabled=e,a("preview").disabled=e,a("rename-submit").disabled=e,S.setBusy(e)},D=(e="")=>`/api/projects/${h}${e}`,qe=new Pe({project:()=>h,summary:()=>d,refresh:async()=>{j(),await q()},preview:e=>{j(),e&&o.showGhosts(e)},openProject:async e=>{await G(e)},notice:m});function M(e){const t=e.split(",").map(n=>Number(n.trim()));if(t.length!==3||t.some(n=>!Number.isInteger(n)))throw new Error("坐标需要三个整数，例如 0,0,0");return t}function ce(){const e=M(c("low")),t=M(c("high"));return{low:e.map((n,i)=>Math.min(n,t[i])),high:e.map((n,i)=>Math.max(n,t[i]))}}function H(){const e=c("group-filter");return e?{group:e}:{bounds:L??ce()}}function te(e){L=e,o.showSelection(e),e&&(P("low",e.low.join(",")),P("high",e.high.join(","))),we(),P("group-filter","")}function we(){const e=o.walk.active?"Alt+点击选择或扩展选区；Shift 下降":"点击选中；Shift+点击扩展选区";a("selection-hint").textContent=L?`选区 ${L.low.join(",")} → ${L.high.join(",")} · ${e}`:e}let W="library";const Q=new Map;function Oe(e){if(e&&!Q.size){const t={"walk-menu-exit":["walk-toggle"],"walk-menu-actions":["undo","redo","save"],"walk-menu-settings":["walk-reach-control","compare"],"walk-panel-host":["library","inspector"],"walk-menu-layers":["slice-controls","workspace-details"],"walk-menu-notices":["warnings"]};for(const[n,i]of Object.entries(t))for(const s of i){const r=a(s),p=document.createComment(s);r.before(p),Q.set(r,p),a(n).append(r)}}else if(!e){for(const[t,n]of Q)n.replaceWith(t);Q.clear()}}o.walk.onChange=()=>{const e=o.walk.active,t=o.walk.locked,n=T.classList.contains("pointer-locked"),i=T.classList.contains("first-person-mode");Oe(e),T.classList.toggle("first-person-mode",e),T.classList.toggle("pointer-locked",e&&t),T.classList.toggle("walk-menu-open",e&&!t),a("walk-toggle").textContent=e?"退出第一人称":"第一人称",a("walk-toggle").setAttribute("aria-pressed",String(e)),a("walk-crosshair").hidden=!e||!t,a("walk-hud").hidden=!e,a("walk-menu").hidden=!e||t,a("walk-status").hidden=!t,a("walk-reach-control").hidden=!e,a("camera-bar").hidden=e,document.querySelectorAll("[data-tool]").forEach(s=>s.disabled=e),we(),z(),e&&n&&!t?a("walk-resume").focus():!e&&i&&a("walk-toggle").focus()};o.walk.onError=e=>m(e,!0);a("walk-toggle").onclick=()=>{o.walk.active?o.walk.exit():d&&(S.stop(),o.walk.enter(d.occupied_bounds?d.occupied_bounds.low[1]+1:0))};a("walk-resume").onclick=()=>void o.walk.lock();try{const e=Number(localStorage.getItem("workbench.walkReach"));Number.isFinite(e)&&e>0&&(o.walkReach=e)}catch{}P("walk-reach",String(o.walkReach));a("walk-reach").onchange=()=>{const e=a("walk-reach").valueAsNumber;if(!Number.isFinite(e)||e<=0){P("walk-reach",String(o.walkReach)),m("命中距离需要大于零。",!0);return}o.walkReach=e;try{localStorage.setItem("workbench.walkReach",String(e))}catch{}};function j(){ne=null,o.clearGhosts(),a("preview-description").textContent="",a("cancel-preview").hidden=!0}function ie(){return U?{...U,chunks:Object.fromEntries([...o.chunks].map(([e,t])=>[e,t.map(n=>[...n])])),models:Object.fromEntries(o.models),removed_chunks:[]}:null}async function q(e=!1){if(!h)return;const t=h,n=performance.now();let i,s,r=0;do if(i=await g(`/api/projects/${t}/render`,e?{}:o.versions),s=await g(`/api/projects/${t}`),++r>=3&&i.revision!==s.revision)throw new Error("场景正在连续更新，请稍后重新读取");while(i.revision!==s.revision);if(h!==t)return;e&&o.clearScene(),o.update(i),await o.whenReady(),U=i,d=s,Te(d);const p=d.events;a("history").replaceChildren(...p.slice(0,8).map(l=>{const b=document.createElement("div"),$={edit:"编辑",import:"导入",rename:"重命名",undo:"撤销",redo:"重做"};return b.textContent=`r${l.revision} · ${$[l.kind]??l.kind} · ${l.changed} 格`,b})),a("stats").textContent=`${i.summary.blocks.toLocaleString()} 方块 · ${Object.keys(i.chunks).length} 分块更新 · ${Math.round(performance.now()-n)} ms`,a("warnings").hidden=i.warnings.length===0,a("warnings").textContent=i.warnings.map(l=>`${l.name.split(":")[1]}：${l.count} 格（${l.reason}）`).join("；")}function Te(e){a("scene-name").textContent=e.name;const t=a("projects").selectedOptions[0];t&&(t.textContent=e.name),a("revision").textContent=`修订 ${e.revision}`,a("scene-meta").textContent=`${e.blocks.toLocaleString()} 个方块 · 修订 ${e.revision} · 已保存`,a("empty-message").hidden=e.blocks>0,a("undo").disabled=!e.undo_available,a("redo").disabled=!e.redo_available;const n=c("group-filter");a("group-filter").replaceChildren(new Option("当前选区",""),...Object.keys(e.groups).map(i=>new Option(`${i} · ${e.groups[i]}`,i))),e.groups[n]&&P("group-filter",n),a("group-tree").replaceChildren(...Object.entries(e.groups).map(([i,s])=>{const r=document.createElement("button");return r.textContent=`${i}  ${s}`,r.onclick=()=>{P("group-filter",i),o.showSelection(null),a("selection-hint").textContent=`分组：${i}${o.walk.active?" · Alt+点击扩展选区；Shift 下降":""}`},r})),S.update(e)}async function G(e){o.walk.exit();const t=await g("/api/projects"),n=a("projects");if(n.replaceChildren(...t.items.map(r=>new Option(r.name,r.project_id))),!t.items.length){const r=await g("/api/projects",{name:"我的建筑"});await G(r.project_id);return}h=e??h??"",t.items.some(r=>r.project_id===h)||(h=t.items[0].project_id),n.value=h;const i=await g(`/api/info?project=${encodeURIComponent(h)}`);if(a("version").textContent=`Java ${i.minecraft_version}`,!i.resources_ready)throw new Error(`Java ${i.minecraft_version} 素材尚未安装，请回到首页下载此版本素材。`);o.atlasUrl=`/api/atlas.png?project=${encodeURIComponent(h)}`,o.texture||await o.initializeTexture(),o.fitted=!1,o.layer=1/0,I=null,P("compare","current"),te(null),j(),await q(!0),N=0,J=null,C={name:"minecraft:oak_planks",properties:{}},await V();const s=await g("/api/catalog?query=oak_planks&limit=1");s.items[0]&&await ve(s.items[0]),history.replaceState({},"",`?project=${h}`),await qe.load();try{const r=JSON.parse(localStorage.getItem("workbench.recentProjects")??"{}"),p=r&&typeof r=="object"&&!Array.isArray(r)?r:{};localStorage.setItem("workbench.recentProjects",JSON.stringify({...p,[h]:Date.now()}))}catch{}}async function V(){const e=new URLSearchParams({query:c("search"),category:c("category"),offset:String(N*24),limit:"24"}),t=await g(`/api/catalog?${e}`);K=t.total,a("catalog-total").textContent=String(K),a("page").textContent=`${N+1} / ${Math.max(1,Math.ceil(K/24))}`,a("prev-page").disabled=N===0,a("next-page").disabled=(N+1)*24>=K,a("materials").replaceChildren();for(const n of t.items){const i=document.createElement("button");i.className="material-card",i.disabled=!0,i.dataset.name=n.name,i.setAttribute("aria-label",n.chinese_name);const s=document.createElement("img");s.alt="",s.width=56,s.height=56;const r=document.createElement("span");r.textContent=n.chinese_name;const p=document.createElement("small");if(p.textContent={static:"",special:"暂无预览",invisible:"不可见",missing:"缺资源"}[n.support.status],i.title=`${n.chinese_name} · ${n.support.reason}`,i.append(s,r,p),i.onclick=()=>void E(async()=>ve(n)),a("materials").append(i),n.support.status==="static"){const l=await g(`/api/material/${n.name.split(":")[1]}`);o.atlas=l.atlas,s.src=o.thumbnail(l,72)}else{const l=document.createElement("span");l.className="material-placeholder",l.setAttribute("aria-hidden","true"),l.textContent=n.support.status==="invisible"?"◇":"▧",s.replaceWith(l)}}a("materials").querySelectorAll(".material-card").forEach(n=>n.classList.toggle("chosen",n.dataset.name===C.name))}async function ve(e){J=e,Z=null,C={...e.default_state,properties:{...e.default_state.properties}},a("material-name").textContent=e.chinese_name,a("material-id").textContent=e.name,a("material-support").textContent=e.support.reason,le.show(e,C),a("materials").querySelectorAll(".material-card").forEach(t=>t.classList.toggle("chosen",t.dataset.name===e.name)),await ye(),m(`已选择 ${e.chinese_name}`)}let he=0;async function ye(){const e=++he,t=h,n=U?.resource_hash;a("walk-material-name").textContent=J?.chinese_name??C.name;const i={facing:{north:"朝北",south:"朝南",west:"朝西",east:"朝东",up:"朝上",down:"朝下"},axis:{x:"沿 X 轴",y:"沿 Y 轴",z:"沿 Z 轴"},half:{top:"上半部",bottom:"下半部",upper:"上半部",lower:"下半部"},waterlogged:{true:"含水",false:"不含水"}};a("walk-material-properties").textContent=Object.entries(C.properties).filter(([l,b])=>b!==J?.default_state.properties[l]).map(([l,b])=>i[l]?.[b]??`${l}：${b}`).join(" · ");const s=a("walk-material-image");if(s.hidden=!0,J?.support.status!=="static")return;const r=new URLSearchParams({properties:JSON.stringify(C.properties)}),p=await g(`/api/material/${C.name.split(":")[1]}?${r}`);e!==he||t!==h||n!==U?.resource_hash||(o.atlas=p.atlas,s.src=o.thumbnail(p,72),s.hidden=!1)}function ke(){const e=c("operation"),t={fill:'<label><input id="hollow" type="checkbox"> 仅填充外壳</label>',replace:'<p class="muted">将选区或分组替换为当前材料。</p>',delete:'<p class="muted">删除选区或分组中的方块。</p>',group:'<p class="muted">将选区归入“结果分组”。</p>',transform:'<label>位移 <input id="offset" value="0,0,0"></label><label>变换中心 <input id="origin" value="0,0,0"></label><label>旋转 <select id="rotation"><option>0</option><option>90</option><option>180</option><option>270</option></select></label><label>镜像 <select id="mirror"><option value="">无</option><option value="x">沿 X</option><option value="z">沿 Z</option></select></label><label><input id="copy" type="checkbox"> 保留原件，复制</label><label><input id="overwrite" type="checkbox"> 允许覆盖目标</label>',array:'<label>重复数 X,Y,Z <input id="count" value="3,1,1"></label><label>间距 X,Y,Z <input id="step" value="8,0,0"></label>',extrude:`<label>轮廓 X,Z（每行一个点）<textarea id="polygon">0,0
6,0
6,8
0,8</textarea></label><label>起始 Y <input id="base-y" type="number" value="0"></label><label>高度 <input id="height" type="number" value="4" min="1"></label>`,arc:'<label>中心 <input id="center" value="0,0,0"></label><label>半径 <input id="radius" type="number" value="8" min="1"></label><label>厚度 <input id="thickness" type="number" value="1" min="1"></label><label>高度 <input id="height" type="number" value="1" min="1"></label><div class="coordinates"><label>起始角 <input id="start-angle" type="number" value="0"></label><label>结束角 <input id="end-angle" type="number" value="360"></label></div>',roof:'<label>屋脊方向 <select id="ridge"><option value="z">沿 Z</option><option value="x">沿 X</option></select></label><label>最高起伏 <input id="height" type="number" value="4" min="1"></label><p class="muted">选区起点 Y 为檐口高度，使用当前材料。</p>',window:'<label>墙面法向 <select id="window-axis"><option value="z">Z（窗宽沿 X）</option><option value="x">X（窗宽沿 Z）</option></select></label><label>边框材料 <input id="frame" value="oak_log"></label><p class="muted">玻璃使用当前材料；选区必须为单格厚。</p>'};a("operation-fields").innerHTML=t[e]??"",j()}function xe(){const e=c("operation"),t=L??ce(),n=c("result-group")||"main",i={name:C.name,properties:{...C.properties}};switch(e){case"fill":return{op:e,bounds:t,state:i,group:n,hollow:a("hollow").checked};case"replace":return{op:e,selector:H(),state:i};case"delete":return{op:e,selector:H()};case"group":return{op:e,selector:H(),name:n};case"transform":return{op:e,selector:H(),origin:M(c("origin")),offset:M(c("offset")),rotation:Number(c("rotation")),mirror:c("mirror")||null,copy:a("copy").checked,overwrite:a("overwrite").checked,group:n};case"array":return{op:e,selector:H(),count:M(c("count")),step:M(c("step")),group:n};case"extrude":return{op:e,polygon:c("polygon").split(`
`).filter(Boolean).map(s=>{const r=s.split(",").map(Number);if(r.length!==2||r.some(p=>!Number.isInteger(p)))throw new Error("轮廓每行需要 X,Z 两个整数");return r}),base_y:Number(c("base-y")),height:Number(c("height")),state:i,group:n};case"arc":return{op:e,center:M(c("center")),radius:Number(c("radius")),thickness:Number(c("thickness")),height:Number(c("height")),start:Number(c("start-angle")),end:Number(c("end-angle")),state:i,group:n};case"roof":return{op:e,bounds:t,ridge_axis:c("ridge"),height:Number(c("height")),state:i,group:n};case"window":return{op:e,bounds:t,axis:c("window-axis"),frame:{name:c("frame")},glass:i,group:n};default:throw new Error("请选择设计工具")}}function oe(e,t={}){if(!h||!d)throw new Error("请先选择项目");const n=e.some(i=>["place","set","fill","replace","extrude","arc","roof","window"].includes(i.op));return{expected_revision:d.revision,request_id:crypto.randomUUID(),auto_connect:n?le.automatic:!0,operations:e,...t}}async function $e(e,t={}){const n=oe(e??[xe()],t),i=await g(D("/preview"),n);ne=n,o.showGhosts(i.changes),a("preview-description").textContent=`将修改 ${i.changed.toLocaleString()} 格。绿色新增或替换，红色删除。${i.truncated?"预览显示前一万格。":""}`,a("cancel-preview").hidden=!1,m(`修改预览：${i.changed} 格，尚未提交`)}async function R(e){if(c("compare")==="before")throw new Error("先切回当前设计再编辑");const t=e?oe(e):ne??oe([xe()]);I=ie();const n=await g(D("/edit"),t);j(),await q(),m(`已保存修订 ${n.revision}，修改 ${n.changed} 格`)}async function E(e){if(!F){ue(!0);try{await e()}catch(t){m(t instanceof Error?t.message:String(t),!0)}finally{ue(!1)}}}o.onHit=(e,t)=>void E(async()=>{if(!e||!d)return;if(c("compare")==="before")throw new Error("先切回当前设计");const n=o.walk.active?t.button===2?"place":t.altKey?"select":"erase":be;if(n==="select"){const i=e.ground?[e.position[0],0,e.position[2]]:e.position;(o.walk.active?t.altKey:t.shiftKey)&&L?te({low:L.low.map((s,r)=>Math.min(s,i[r])),high:L.high.map((s,r)=>Math.max(s,i[r]))}):te({low:i,high:i}),m(e.protected?"此格包含保留的实体内容；当前只能查看":`选中 ${i.join(",")}`)}else if(n==="place"){if(e.painting)throw new Error("请点击支撑方块表面");if(Z!==null){const s={"0,0,-1":"north","0,0,1":"south","1,0,0":"east","-1,0,0":"west"}[e.normal.join(",")];if(!s)throw new Error("画需要竖直墙面");await R([{op:"painting",support:e.position,face:s,variant:Z}])}else await R([{op:"place",hit:e.position,normal:e.normal,location:e.location,facing:o.placementFacing(),automatic:le.automatic,state:C,group:c("result-group")}])}else if(!e.ground)if(e.painting){if(e.protected)throw new Error("导入的画为只读实体，原始 NBT 会保留");await R([{op:"delete_painting",id:e.painting}])}else await R([{op:"delete",selector:{bounds:{low:e.position,high:e.position}}}])});a("painting-variant").onchange=()=>{Z!==null&&(Z=c("painting-variant"))};a("choose-painting").onclick=()=>{Z=c("painting-variant"),document.querySelector('[data-tool="place"]').click(),m("已选择画：点击墙面挂画；图案和手动朝向可在左侧调整")};function x(e,t){a(e).onclick=()=>void E(t)}const re=a("rename-dialog");a("rename-project").onclick=()=>{F||!d||(o.walk.locked&&document.exitPointerLock(),S.stop(),P("project-name",d.name),a("project-name").setCustomValidity(""),a("rename-error").textContent="",re.showModal(),a("project-name").select())};a("project-name").oninput=()=>{a("project-name").setCustomValidity(""),a("rename-error").textContent=""};a("rename-form").onsubmit=e=>{e.preventDefault();const t=c("project-name").trim();if(!t){a("project-name").setCustomValidity("请输入设计名称"),a("project-name").reportValidity();return}if(t===d?.name){re.close();return}E(async()=>{try{I=ie(),await g(D(),{name:t,expected_revision:d.revision,request_id:crypto.randomUUID()},"PATCH"),j(),await q(),re.close(),m(`已重命名为「${t}」并保存`)}catch(n){throw a("rename-error").textContent=n instanceof Error?n.message:String(n),n}})};a("help").onclick=()=>{o.walk.locked&&document.exitPointerLock(),S.stop(),a("help-dialog").showModal()};document.querySelectorAll("[data-close-dialog]").forEach(e=>{e.onclick=()=>a(e.dataset.closeDialog).close()});function Me(){const e={library:innerWidth>780,inspector:innerWidth>780};try{const t=JSON.parse(localStorage.getItem("workbench.panels")??"null");return t&&typeof t.library=="boolean"&&typeof t.inspector=="boolean"?t:e}catch{return e}}let k=Me(),ee=null;function z(){for(const t of["library","inspector"]){const n=o.walk.active?!o.walk.locked&&W===t:k[t];a(t).hidden=!n,a("workbench-layout").classList.toggle(`${t}-hidden`,!k[t]),a(`toggle-${t}`).setAttribute("aria-expanded",String(k[t]))}const e=!k.library&&!k.inspector;if(a("focus-mode").setAttribute("aria-pressed",String(e)),a("focus-mode").textContent=e?"退出专注":"专注",document.querySelectorAll("[data-walk-panel]").forEach(t=>{t.setAttribute("aria-pressed",String(t.dataset.walkPanel===W))}),a("walk-menu-layers").hidden=W!=="inspector",!o.walk.active)try{localStorage.setItem("workbench.panels",JSON.stringify(k))}catch{}}for(const e of["library","inspector"])a(`toggle-${e}`).onclick=()=>{if(o.walk.active){W=e,o.walk.locked&&document.exitPointerLock(),z();return}ee=null,k[e]=!k[e],z()};document.querySelectorAll("[data-walk-panel]").forEach(e=>{e.onclick=()=>{W=e.dataset.walkPanel,z()}});a("focus-mode").onclick=()=>{o.walk.active||(!k.library&&!k.inspector?(k=ee??{library:!0,inspector:!0},ee=null):(ee={...k},k={library:!1,inspector:!1}),z())};z();document.addEventListener("visibilitychange",()=>{document.hidden&&S.stop()});x("new-project",async()=>{const e=prompt("建筑名称","新建筑");if(!e)return;const t=await g("/api/projects",{name:e,minecraft_version:d?.minecraft_version});await G(t.project_id),m("新项目已创建")});a("projects").onchange=()=>void E(async()=>{await G(c("projects")),m("项目已打开")});x("save",async()=>{await q(),m(`已保存并重新读取，修订 ${d?.revision}`)});for(const e of["undo","redo"])x(e,async()=>{I=ie(),await g(D(`/history/${e}`),{expected_revision:d.revision,request_id:crypto.randomUUID()}),j(),await q(),m(e==="undo"?"已撤销并保存":"已重做并保存")});x("preview",()=>$e());x("commit",()=>R());x("cancel-preview",async()=>j());x("select-bounds",async()=>{te(ce()),m("选区已更新")});a("operation").onchange=ke;a("compare").onchange=()=>void E(async()=>{if(j(),c("compare")==="before"){if(!I)throw P("compare","current"),new Error("还没有可对比的上次修改");o.update({...I,removed_chunks:Object.keys(o.versions).filter(e=>!I.chunks[e])}),await o.whenReady(),S.update(I.summary),m(`查看修改前 r${I.revision}`)}else await q(!0),m("查看当前设计")});document.querySelectorAll("[data-tool]").forEach(e=>e.onclick=()=>{be=e.dataset.tool,document.querySelectorAll("[data-tool]").forEach(t=>t.classList.toggle("active",t===e))});document.querySelectorAll("[data-view]").forEach(e=>e.onclick=()=>{o.view(e.dataset.view),document.querySelectorAll("[data-view]").forEach(t=>t.setAttribute("aria-pressed",String(t===e)))});a("fit").onclick=()=>{d?.occupied_bounds&&o.fit(d.occupied_bounds)};let me=0;a("search").oninput=()=>{clearTimeout(me),me=window.setTimeout(()=>{N=0,E(V)},300)};a("category").onchange=()=>{N=0,E(V)};x("prev-page",async()=>{N=Math.max(0,N-1),await V()});x("next-page",async()=>{N++,await V()});a("import").onclick=()=>a("import-file").click();a("import-file").onchange=()=>void E(async()=>{const e=a("import-file").files?.[0];if(!e||!d)return;const t=new FormData;t.set("file",e),t.set("expected_revision",String(d.revision)),t.set("request_id",crypto.randomUUID()),I=ie();const n=await fetch(D("/import"),{method:"POST",body:t}),i=await n.json();if(!n.ok)throw new Error(i.error?.message??"导入失败");o.fitted=!1,o.layer=1/0,await q(!0),m(`导入完成：${i.import_report.blocks.toLocaleString()} 方块，特殊内容已保留`),a("import-file").value=""});x("export",async()=>{const e=await fetch(D("/export"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_revision:d.revision})});if(!e.ok){const s=await e.json();throw new Error(s.error?.message??"导出失败")}const t=await e.blob(),n=URL.createObjectURL(t),i=document.createElement("a");i.href=n,i.download=`${d.name}-r${d.revision}.litematic`,i.click(),URL.revokeObjectURL(n),m("蓝图已导出，方块状态与保留内容已写入")});x("check",async()=>{const e=await g(D("/consistency"));ge=e.proposals,fe=e.revision,a("check-result").textContent=`${e.issues.length} 个部件问题，${e.proposals.length} 个连接或补全建议。${e.limitations.join("；")}`,a("apply-rules").hidden=!e.proposals.length;const t=a("check-issues");if(t.hidden=!e.issues.length,t.replaceChildren(...e.issues.slice(0,100).map(n=>{const i=document.createElement("li");return i.textContent=`${n.position.join(", ")}：${n.message}`,i})),e.issues.length>100){const n=document.createElement("li");n.textContent=`其余 ${e.issues.length-100} 个问题可通过接口查看。`,t.append(n)}});x("apply-rules",async()=>{if(fe!==d?.revision)throw new Error("设计已修改，请重新检查连接后再预览修复");await $e([{op:"set",blocks:ge}],{auto_connect:!0})});async function _e(){await R([{op:"fill",bounds:{low:[0,0,0],high:[8,0,10]},state:{name:"oak_planks"},group:"floor"},{op:"fill",bounds:{low:[0,1,0],high:[8,4,10]},state:{name:"oak_planks"},group:"walls",hollow:!0},{op:"fill",bounds:{low:[1,4,1],high:[7,4,9]},state:{name:"air"}},{op:"fill",bounds:{low:[4,1,0],high:[4,2,0]},state:{name:"air"}},{op:"roof",bounds:{low:[-1,5,-1],high:[9,5,11]},state:{name:"spruce_stairs"},ridge_axis:"z",height:6,group:"roof"},{op:"window",bounds:{low:[1,1,0],high:[3,3,0]},axis:"z",frame:{name:"oak_log"},glass:{name:"glass"},group:"windows"},{op:"window",bounds:{low:[5,1,0],high:[7,3,0]},axis:"z",frame:{name:"oak_log"},glass:{name:"glass"},group:"windows"},{op:"set",blocks:[{position:[4,1,0],state:{name:"oak_door",properties:{half:"lower",facing:"north"}},group:"door"},{position:[4,2,0],state:{name:"oak_door",properties:{half:"upper",facing:"north"}},group:"door"}]}]),o.fitted=!1,await q(!0),m("木屋起稿完成，可继续自由编辑")}x("cabin",_e);document.addEventListener("keydown",e=>{const t=e.target instanceof HTMLElement?e.target:null;if(e.defaultPrevented||e.isComposing||e.repeat||e.altKey||document.querySelector("dialog[open]")||Ee(t))return;const n=e.key.toLowerCase();if(o.walk.active&&[" ","shift","control"].includes(n)||t?.closest("button")&&[" ","arrowleft","arrowright"].includes(n))return;if(e.ctrlKey||e.metaKey){const s=n==="z"?e.shiftKey?"redo":"undo":n==="y"?"redo":n==="s"?"save":"";s&&(e.preventDefault(),a(s).click());return}const i={" ":()=>S.toggle(),arrowleft:()=>S.step(-1),arrowright:()=>S.step(1),"[":()=>a("toggle-library").click(),"]":()=>a("toggle-inspector").click(),f:()=>a("fit").click(),g:()=>a("walk-toggle").click(),f2:()=>a("rename-project").click(),"?":()=>a("help").click(),escape:()=>{S.stop(),j()}};["1","2","3"].includes(n)?(e.preventDefault(),document.querySelector(`[data-tool="${{1:"select",2:"place",3:"erase"}[n]}"]`)?.click()):n==="tab"&&(t===document.body||t?.tagName==="CANVAS"||t?.id==="stage"||t?.id==="app")?(e.preventDefault(),a("focus-mode").click()):i[n]&&(e.preventDefault(),i[n]())});Object.defineProperty(window,"workbench",{value:{viewer:o,get project(){return h},get summary(){return d},get selection(){return L},get busy(){return F}},writable:!1});ke();E(async()=>{const e=await g("/api/paintings");a("painting-variant").replaceChildren(new Option("自动选择最大可挂图案","auto"),...e.items.map(t=>new Option(`${t.name} · ${t.width}×${t.height}`,t.name))),await G(pe.get("project")??void 0),m("工作台就绪 · 所有修改自动保存"),pe.get("starter")==="cabin"&&d?.blocks===0&&d.revision===0&&await _e()});let se=!1;window.setInterval(()=>{if(se||F||document.hidden||!h||!d||c("compare")==="before")return;se=!0;const e=h;g(`/api/projects/${e}`).then(async t=>{F||h!==e||t.revision===d?.revision||await E(async()=>{await q(),m(ne?`已读取外部编辑 r${d?.revision}；当前预演基于旧修订，请重新预演`:`已读取外部编辑 r${d?.revision}`)})}).catch(t=>{console.warn("读取外部修订失败",t)}).finally(()=>{se=!1})},1500);
