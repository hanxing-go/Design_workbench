# 快速开始

当前应用版本 0.1.0，Minecraft Java 1.20.1。P1–P5 工作台与 P6 外部 AI 工具已实现，阶段验收状态见 [实施路线](ROADMAP.md)。

## 当前机器

Python 环境和官方素材已经在项目中准备好：

```powershell
cd D:\Study\program\Design_workbench
.\.venv\Scripts\design-workbench.exe serve --config config.example.toml
```

访问 <http://127.0.0.1:8765>。如果该服务已运行，直接打开页面；无需启动第二个相同端口的服务。Ctrl+C 关闭服务。

项目数据在 `.local/data/projects/*.dwbench`，资源在 `.local/cache/resources/`，日志在 `.local/logs/`。`.dwbench` 是 SQLite 项目文件，`.litematic` 是与外部工具交换的压缩 NBT 蓝图。

## GUI 操作

1. 首页点击“开始建造”并输入名称，或从“我的设计”打开已有项目。首页“导入蓝图”会新建独立项目后读入 `.litematic`；“先搭一间小屋”会创建可自由编辑的木屋。进入工作台后，也可以在顶栏新建或切换项目；左上角房屋图标可返回首页。
2. 左侧查询材料，点击卡片并选择属性，例如楼梯的 facing 和 half。
3. 可用“生成简单木屋”起稿。也可在右侧设置整数选区，再选择填充、挤出等工具。
4. “预览修改”显示绿色新增/替换、红色删除；“应用修改”提交，所有成功修改自动保存。“取消预览”不改项目。
5. 点击方块选择，Shift+点击扩展；分组树可选整组。拖动旋转，右键平移，滚轮缩放；视角按钮和最高显示层控制观察。
6. 撤销/重做产生新修订。“保存 / 重读”重新读取已保存结果。“上次修改前”比较本次浏览器会话中的最近快照；刷新页面不保留这张比较快照，数据库历史仍保留。
7. “检查部件与连接”给出建议；先预览建议再应用。“导出蓝图”下载当前修订。

工作台内导入会替换当前项目场景，作为可撤销事务记录；首页导入始终使用独立新项目。特殊实体关联格只能查看和保留，相关编辑返回明确限制。

首页浮空小岛支持拖动和方向键旋转、暂停、重播方块组装动画；离开可见区域或切换到后台时停止动画，遵循系统减少动态效果设置。没有 WebGL 时显示静态草方块。直接访问 `/?project=项目标识` 可打开指定设计，`/?view=workbench` 保留原工作台入口。

### 第一人称沉浸编辑

桌面 Chrome 中点击工具栏“第一人称”，或在画布上按 G。进入时建筑画布铺满窗口，工作台顶栏、工具栏和两侧面板收起，中心显示准星，底部显示当前材料缩略图与名称。鼠标转动视线，WASD 水平移动，Space 上升，Shift 下降，Ctrl 加速。可以穿过墙和楼板，不受碰撞或重力影响。

左键删除准星命中的方块，右键在命中面的空格放置当前材料。Alt+左键第一次选择一格，之后扩选；轨道模式的选择/放置/删除工具在第一人称中暂时禁用。命中距离默认 5 格，在 Esc 编辑菜单中调整；该设置只保存在当前浏览器。

Esc 先释放鼠标并打开浮动编辑菜单，保留第一人称位置和预览，再按 Esc 取消预览。菜单可切换“方块材料”和“设计工具”，使用材料属性、选区、分组、预演、对比、剖切和撤销重做；矮窗口下菜单可滚动，退出按钮固定在顶部。点击“继续编辑”或画布重新锁定并收起菜单。G 或菜单中的“退出第一人称”恢复进入前的轨道相机和面板布局。每次点击各提交一笔自动保存的编辑，撤销需要逐笔执行；重开项目保留方块和历史，恢复轨道视图。详见 [E1 验收](E1_ACCEPTANCE.md)。

## 从源码全新安装

需要 Python 3.12、uv、Node.js 22+；浏览器须支持 WebGL。以下在项目根目录执行：

```powershell
uv sync --locked --extra gui
npm.cmd ci --prefix frontend
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
uv run design-workbench resources setup --config config.example.toml
uv run design-workbench serve --config config.example.toml
```

Linux 使用 `npm`。官方素材获取需要网络，成功导入后设计与预览可以在本地运行。

有本地官方客户端和中文语言文件时：

```powershell
uv run design-workbench resources setup --config config.example.toml --jar "D:\Minecraft\1.20.1.jar" --language "D:\Minecraft\zh_cn.json"
```

客户端 `version.json` 必须与基线一致；1.21 的客户端不能作为 1.20.1 资源包导入。资源导入后重启服务。配置文件中相对路径以该文件所在目录为基准。

## 使用 wheel

本机构建产物在 `dist/`，其中 `minecraft_design_workbench-0.1.0-py3-none-any.whl` 包含注册表及已构建前端，不包含官方游戏素材：

```powershell
python -m venv .install-env
.\.install-env\Scripts\python.exe -m pip install ".\dist\minecraft_design_workbench-0.1.0-py3-none-any.whl[gui]"
.\.install-env\Scripts\design-workbench.exe resources setup --config config.example.toml
.\.install-env\Scripts\design-workbench.exe serve --config config.example.toml
```

无配置参数时使用系统用户数据目录。`design-workbench info --config ...` 显示有效路径。移动整个项目后重建 `.venv`，便携配置与数据可以保留；虚拟环境中的绝对解释器路径不应直接搬用。

## CLI

CLI 是命令行入口，与网页调用同一个 Python 应用服务。例如：

```powershell
uv run design-workbench --help
uv run design-workbench create .local/data/example.dwbench --name 示例 --config config.example.toml
uv run design-workbench summary .local/data/example.dwbench --config config.example.toml
```

编辑文件按 [API 契约](API_AND_DATA.md) 保存后交给 `design-workbench edit 项目路径 请求文件 --preview --config config.example.toml`。去掉 `--preview` 即提交；使用最新修订和独立 request_id。

## 外部 AI 接入

P6 采用 CLI 优先：`design-workbench tools --config config.example.toml` 输出工具 Schema，`design-workbench tool scene.summary summary.json --config config.example.toml` 按项目 ID 调用共用工具。截图返回实际 PNG，需要 `--output-dir` 保存并由 Agent 读图；兼容客户端也可直接使用 stdio MCP 的图片内容。

```powershell
uv sync --locked --extra gui --extra ai --extra render
uv run python -m playwright install chromium
uv run design-workbench mcp --config config.example.toml
```

已有 Chrome 时也可在 TOML 设置 `browser_channel = "chrome"`，或使用 `DW_BROWSER_CHANNEL=chrome`。查询/编辑不需要启动浏览器。完整 JSON、工具列表、截图任务与预算见 [P6 使用指南](P6_USAGE.md)，实际外部 AI 流程见 [验收记录](P6_ACCEPTANCE.md)。平台内自主模型调用尚未实现。

## 开发检查

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -m "not e2e and not resources" -q
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
uv build
uv run python scripts/install_smoke.py
```

完整测试要求实际素材已配置，并安装 Playwright Chromium：

```powershell
uv run playwright install chromium
uv run pytest -q
```

本机已有 Chrome，可设 `$env:DW_BROWSER_CHANNEL='chrome'` 使用已安装浏览器。Linux Chromium 环境另需 `playwright install --with-deps chromium`。

`scripts/verify_browser.py` 是需要正在运行的工作台服务和本地教堂样例的扩展验收，详见 [验收记录](P5_ACCEPTANCE.md)。
