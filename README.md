# Design Workbench

独立的 Minecraft 建筑设计工作台。Python 保存权威场景并执行编辑、历史、资源和蓝图读写；TypeScript/Three.js 提供实际方块的三维界面。

**P1–P6 已完成，交付点 A/B 达成；P7 进行中。** 现支持 **17 个 Minecraft Java 发行版本（1.20.1 至 26.1）**，每个项目固定版本与 DataVersion，具体列表见 [多版本支持](docs/VERSION_SUPPORT.md)。CLI、HTTP、MCP 共用工具服务，外部 AI 已实际完成木屋、苦情巨树和迪迦等作品的创作及导出。工作台现提供任务阶段、预算、取消恢复、用户确认改稿和独立候选稿；平台内自主模型调度仍待实现。

公开仓库：<https://github.com/hanxing-go/Design_workbench>。`v0.1.0` 保存 P1–P5 的交付版本，开发与版本管理约定见 [贡献指南](CONTRIBUTING.md)。

[![Check](https://github.com/hanxing-go/Design_workbench/actions/workflows/check.yml/badge.svg)](https://github.com/hanxing-go/Design_workbench/actions/workflows/check.yml)

## 快速启动

普通 Windows 用户可使用标准便携包：完整解压后双击 `DesignWorkbench.exe`，按启动窗口提示下载官方素材或导入 1.20.1 客户端，随后自动打开浏览器。无需安装 Python 或 Node.js；构建、数据目录与升级说明见 [Windows 便携包](docs/WINDOWS_PORTABLE.md)。便携包由 Windows 发布工作流构建，标准版不包含 MCP 与截图依赖。

首次使用先完成下方的“安装与开发”。已安装依赖、构建前端并导入官方素材后，在项目根目录的 PowerShell 中运行：

```powershell
uv run --extra gui design-workbench serve --config config.example.toml
```

打开 <http://127.0.0.1:8765>。服务默认只监听本机，按 Ctrl+C 停止，之后使用同一命令重新启动。

启动命令中的 `--extra gui` 必须保留：`uv run` 会按本次指定的 extras 同步依赖，仅执行过 `uv sync --extra gui` 不足以保证后续命令安装网页服务依赖。若出现 `No module named fastapi`，重新执行上面的启动命令即可。MCP 使用 `--extra ai`，截图还需 `--extra gui --extra render`。

`config.example.toml` 中的相对路径以配置文件所在目录为基准：项目保存在 `.local/data/projects/`，官方素材缓存在 `.local/cache/resources/`，日志保存在 `.local/logs/`。拉取源码不会下载这些本地数据、Python 环境或游戏素材。

## 当前可以做什么

- 按项目版本浏览注册方块、查询中文/英文名称、分页和类别；选择合法属性，查看实际缩略图及支持标记。
- 新建建筑或导入 `.litematic`；旋转相机、切换视角、按 Y 层剖切、比较最近一次修改前的画面。
- 点击和 Shift 扩选、坐标选区、分组；放置、删除、填充、替换、移动、复制、旋转、镜像。
- [自动吸附](docs/PLACEMENT_SNAP.md)：火把、告示牌、梯子等按点击面定向，保留手动属性；画支持静态预览、保存、撤销和实体蓝图导出。
- 阵列、二维轮廓挤出、圆弧、双坡屋顶与窗组；生成的结果仍能逐格编辑。
- 预演修改差异再应用；原子提交、自动保存、撤销/重做、重开和修订冲突检查。
- 检查常见门床部件和连接状态，预览建议后应用；导出蓝图供外部工具使用。
- 外部 AI 通过 CLI 或 MCP 查询材料、批量编辑、查看固定修订的多视角/剖切 PNG 并改稿；网页同步刷新外部编辑，修订冲突与重试有统一处理。
- 顶部“AI 任务”创建持久任务，查看进度和预算，确认或拒绝改稿、取消和继续；候选稿保留完整工程及截图，打开副本继承需求与反馈。外部模型用量须按实际计数回报，详见 [AI 任务控制](docs/AI_CONTROLS.md)。

已在真实 Chrome 中完成木屋完整设计流程、36,094 格教堂导入与局部编辑、全部高级表单操作。导出用独立的 litemapy 逐格核对完整状态与坐标，教堂的 67 个方块实体保留。

## 安装与开发

从源码安装需要 Git、Python 3.12、uv 和 Node.js 22+，浏览器须支持 WebGL。安装已构建的 wheel 时不需要 Node.js，前端也不通过 CDN 加载。

以下命令拉取本文对应的 `codex/p6-ai-tools` 分支并完成首次安装：

```powershell
git clone https://github.com/hanxing-go/Design_workbench.git
cd Design_workbench
uv sync --locked --extra gui
npm.cmd ci --prefix frontend
npm.cmd run build --prefix frontend
uv run --extra gui design-workbench resources setup --config config.example.toml
uv run --extra gui design-workbench serve --config config.example.toml
```

Windows PowerShell 使用 `npm.cmd`；Linux/macOS 将其替换为 `npm`。已拉取项目可从 `uv sync` 开始执行。更新源码时，在工作区干净的情况下执行 `git pull --ff-only`，再同步依赖并重新构建前端。

首页新建时可选择 Java 版本并下载对应官方素材；导入蓝图会识别版本。游戏模型和贴图从官方客户端单独导入，不包含在 wheel 中。已有客户端可使用 `resources setup --jar ... --language ...`，详见 [快速开始](docs/QUICKSTART.md)。

AI 工具采用 CLI 优先的接入方式：`uv run design-workbench tools` 查看 Schema，`uv run design-workbench tool 工具名 请求.json --config config.example.toml` 调用工具。MCP 和截图需另安装 `ai`、`render` extras，并安装 Chromium 或配置已有 Chrome。完整命令、实际 PNG 和浏览器依赖见 [P6 使用指南](docs/P6_USAGE.md)。

```powershell
uv sync --locked --extra gui --extra ai --extra render
uv run --extra gui --extra ai --extra render python -m playwright install chromium
uv run design-workbench tools --config config.example.toml
uv run --extra gui --extra ai --extra render design-workbench mcp --config config.example.toml
```

最后一条命令启动供 AI 客户端连接的 stdio MCP 服务。已有 Chrome 时，可在配置文件中设置 `browser_channel = "chrome"`，使用该浏览器进行截图；查询、编辑和导出无需启动浏览器。平台内自主模型配置与调度仍待实现，当前通过外部 AI 接入。

构建与验证：

```powershell
uv run --extra gui --extra ai --extra render ruff check .
uv run --extra gui --extra ai --extra render ruff format --check .
uv run --extra gui --extra ai --extra render mypy
uv run --extra gui --extra ai --extra render pytest -m "not e2e and not resources"
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
uv build
uv run python scripts/install_smoke.py
```

实际资源与浏览器检查的前提、命令和结果见 [P5 验收记录](docs/P5_ACCEPTANCE.md)。

## 项目结构

| 路径 | 内容 |
| --- | --- |
| `src/design_workbench/` | Python 场景、编辑、持久化、资源与 CLI/HTTP/MCP 接口 |
| `frontend/` | TypeScript/Three.js 界面及 Vite 构建配置 |
| `tests/` | 核心契约、资源与真实浏览器测试 |
| `scripts/` | 安装验证、浏览器验收与渲染基准脚本 |
| `docs/`、`figures/` | 使用指南、架构、验收记录与图解 |
| `config.example.toml` | 本地路径、Minecraft 版本、编辑与截图预算配置 |

## 渲染性能

大建筑优化已实现：分块合批、全局透明排序与未变化透明几何复用、分帧剖切重建、增量后端缓存、独立缩略图和缓冲释放，保留每格状态与拾取身份。本机 Windows 11 / RTX 5060 Ti / Chrome 154 下，100,000 格混合建筑每帧调用从 **29,596 降至 243**，相机旋转帧间隔 P95 从 **183.4 ms 降至 16.8 ms**，约从 5–6 FPS 达到 60 FPS；105,102 格真实城堡裁片也达到约 60 FPS。10 万方块普通画布 DPR1/DPR2 各阶段 6 秒×3 次重复，真实建筑、专注宽视图与连续交互分别验证，完整数据、所有成功/失败和回退尝试见 [渲染优化实验记录](docs/RENDERING_OPTIMIZATION_LOG.md)。本机快速重测：

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label current --quick
```

基准使用独立端口与临时数据库、完整加载全部测试格，结果和截图保存在 `artifacts/performance/`。默认读取 `.local/cache` 的官方资源；测试场景由脚本确定性生成，可通过 `--asset` 增加同版本蓝图、`--project` 增加明确来源的渲染项目，详细参数和证据边界见实验记录。

这些结果只代表记录中的机器与场景。首次导入仍需数秒，编辑或前后比较需等待完整网格；连续操作存在偶发约 50 ms 帧，严格像素对照仍未通过，差异主要在边缘。1,156,099 格完整城堡压力探索的全景约 30 FPS，未达到 60 FPS。用户链接别墅原件是 v5 / DataVersion 3578，本轮仅测试完整状态投影，不能据此宣称原生导入或 NBT 导出无损。

## 文档

| 文档 | 用途 |
| --- | --- |
| [项目目标](docs/GOALS.md) | 总目标、优先级与交付点 A/B/C |
| [实施路线](docs/ROADMAP.md) | P0–P8 分阶段任务及完成条件 |
| [扩展计划](docs/PLANNED_EXTENSIONS.md) | 已实现的行走精修和待实现的网格体素化 |
| [E1 验收](docs/E1_ACCEPTANCE.md) | 行走操作、真实 Chrome 编辑与持久化证据 |
| [当前能力](docs/CURRENT_CAPABILITIES.md) | 已实现内容和后续缺口 |
| [快速开始](docs/QUICKSTART.md) | 本机启动、全新安装、GUI 流程及验证 |
| [架构](docs/ARCHITECTURE.md) | Python 领域/应用/适配器/接口与前端边界 |
| [性能计划](docs/PERFORMANCE_PLAN.md) | 渲染瓶颈、优化顺序及客户端方案 |
| [渲染优化实验记录](docs/RENDERING_OPTIMIZATION_LOG.md) | 每次优化、失败/回退、真实大建筑基准与100,000格验收 |
| [渲染优化新手图解](docs/rendering-guide/README.md) | 一点一篇，生活类比、前后流程与详细图示；另有可放大图片的离线网页 |
| [显示修复](docs/RENDERING_FIXES.md) | 特殊方块、透明材质及 MC 版本边界 |
| [自动吸附](docs/PLACEMENT_SNAP.md) | 支撑面定向、手动模式、画与保存迁移 |
| [多版本支持](docs/VERSION_SUPPORT.md) | 项目版本选择、官方素材下载、版本列表与新增版本验证 |
| [工程规范](docs/ENGINEERING.md) | 类型、锁文件、事务恢复、检查与发布 |
| [API 和数据契约](docs/API_AND_DATA.md) | 操作格式、修订、幂等、配置和恢复 |
| [资源与兼容范围](docs/RESOURCES_AND_LIMITS.md) | 来源、版本、静态预览和 NBT 限制 |
| [P5 验收记录](docs/P5_ACCEPTANCE.md) | 27 项任务到实现和真实验证的映射 |
| [P6 使用指南](docs/P6_USAGE.md) | CLI 优先、MCP/HTTP 接入、截图任务与预算 |
| [P6 验收记录](docs/P6_ACCEPTANCE.md) | 实际外部 AI 看图改稿、协议/浏览器与安装验证 |
| [AI 任务控制](docs/AI_CONTROLS.md) | 预算、取消恢复、改稿确认、候选稿和外部 Agent 接入 |
| [范围与验收](docs/SCOPE.md) | 全项目边界和后续验收要求 |

## 当前边界

数据覆盖与预览覆盖分别记录：24,135 个注册状态中，23,399 个可解析为静态模型，655 个需特殊渲染，81 个不可见，0 个缺资源。没有实现完整游戏光照、群系颜色、动画或通用实体渲染；画已有独立静态预览。特殊内容保留数据并显示限制提示。

蓝图兼容范围是版本一致的 Litematica v5/v6、不重叠区域。实体/NBT 关联格受到编辑保护；存在歧义的区域或导出会明确失败。已验证独立读取器，尚未执行 Minecraft/Litematica 客户端内验收。

Windows 已验证真实浏览器工作流；Linux 已在 WSL Ubuntu 中验证核心检查及干净环境安装。[首次 GitHub Actions](https://github.com/hanxing-go/Design_workbench/actions/runs/37935155062) 的 Windows/Linux 核心与安装、Linux 官方资源与真实浏览器任务全部通过。

第一人称沉浸编辑已实现：点击“第一人称”或按 G，建筑铺满窗口，使用准星在室内放置、删除和选择方块；Esc 打开材料与工具菜单，“退出第一人称”恢复原视图与面板布局。操作与验证见 [E1 验收](docs/E1_ACCEPTANCE.md)。把 OBJ/glTF 转成方块的 E2 仍未开始，规则见 [扩展计划](docs/PLANNED_EXTENSIONS.md)。

源码采用 MIT 许可；Minecraft 素材和第三方建筑不受本项目 MIT 许可覆盖。用户项目、游戏资源、日志、导出及本地验收产物留在 `.local/` 和 `artifacts/`，不提交到源码仓库。
