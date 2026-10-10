# Design Workbench

独立的 Minecraft 建筑设计工作台。Python 保存权威场景并执行编辑、历史、资源和蓝图读写；TypeScript/Three.js 提供实际方块的三维界面。

**P1–P5 已完成，交付点 A：人可使用的设计工作台。** 当前支持 Minecraft Java **1.20.1 / DataVersion 3465**。MCP 与自主 AI 设计分别属于后续 P6、P7，目前未实现。

公开仓库：<https://github.com/hanxing-go/Design_workbench>。`v0.1.0` 保存 P1–P5 的交付版本，开发与版本管理约定见 [贡献指南](CONTRIBUTING.md)。

[![Check](https://github.com/hanxing-go/Design_workbench/actions/workflows/check.yml/badge.svg)](https://github.com/hanxing-go/Design_workbench/actions/workflows/check.yml)

## 直接启动本机项目

项目位置：`D:\Study\program\Design_workbench`。依赖和官方素材已配置，PowerShell 中运行：

```powershell
cd D:\Study\program\Design_workbench
.\.venv\Scripts\design-workbench.exe serve --config config.example.toml
```

打开 <http://127.0.0.1:8765>。服务默认只监听本机，关闭终端服务后使用同一命令重新启动。

## 当前可以做什么

- 浏览 1,003 个注册方块、查询中文/英文名称、分页和类别；选择合法属性，查看实际缩略图及支持标记。
- 新建建筑或导入 `.litematic`；旋转相机、切换视角、按 Y 层剖切、比较最近一次修改前的画面。
- 点击和 Shift 扩选、坐标选区、分组；放置、删除、填充、替换、移动、复制、旋转、镜像。
- 阵列、二维轮廓挤出、圆弧、双坡屋顶与窗组；生成的结果仍能逐格编辑。
- 预演修改差异再应用；原子提交、自动保存、撤销/重做、重开和修订冲突检查。
- 检查常见门床部件和连接状态，预览建议后应用；导出蓝图供外部工具使用。

已在真实 Chrome 中完成木屋完整设计流程、36,094 格教堂导入与局部编辑、全部高级表单操作。导出用独立的 litemapy 逐格核对完整状态与坐标，教堂的 67 个方块实体保留。

## 安装与开发

需要 Python 3.12、uv；修改前端需要 Node.js 22+。已打包运行时不需要 Node.js，也不通过 CDN 加载前端。

```powershell
git clone https://github.com/hanxing-go/Design_workbench.git
cd Design_workbench
uv sync --locked --extra gui
npm.cmd ci --prefix frontend
npm.cmd run build --prefix frontend
uv run design-workbench resources setup --config config.example.toml
uv run design-workbench serve --config config.example.toml
```

游戏模型和贴图从官方客户端单独导入，不包含在 wheel 中。已有客户端可使用 `resources setup --jar ... --language ...`，详见 [快速开始](docs/QUICKSTART.md)。

构建与验证：

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -m "not e2e and not resources"
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
uv build
uv run python scripts/install_smoke.py
```

实际资源与浏览器检查的前提、命令和结果见 [P5 验收记录](docs/P5_ACCEPTANCE.md)。

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
| [多版本计划](docs/VERSION_SUPPORT.md) | 当前支持范围和新增版本的配套要求 |
| [工程规范](docs/ENGINEERING.md) | 类型、锁文件、事务恢复、检查与发布 |
| [API 和数据契约](docs/API_AND_DATA.md) | 操作格式、修订、幂等、配置和恢复 |
| [资源与兼容范围](docs/RESOURCES_AND_LIMITS.md) | 来源、版本、静态预览和 NBT 限制 |
| [P5 验收记录](docs/P5_ACCEPTANCE.md) | 27 项任务到实现和真实验证的映射 |
| [范围与验收](docs/SCOPE.md) | 全项目边界和后续验收要求 |

## 当前边界

数据覆盖与预览覆盖分别记录：24,135 个注册状态中，21,879 个可解析为静态模型，2,175 个需特殊渲染，81 个不可见，0 个缺资源。没有实现完整游戏光照、群系颜色、动画或实体渲染。特殊内容保留数据并显示限制提示。

蓝图兼容范围是版本一致的 Litematica v6、不重叠区域。实体/NBT 关联格受到编辑保护；存在歧义的区域或导出会明确失败。已验证独立读取器，尚未执行 Minecraft/Litematica 客户端内验收。

Windows 已验证真实浏览器工作流；Linux 已在 WSL Ubuntu 中验证核心检查及干净环境安装。[首次 GitHub Actions](https://github.com/hanxing-go/Design_workbench/actions/runs/37935155062) 的 Windows/Linux 核心与安装、Linux 官方资源与真实浏览器任务全部通过。

第一人称沉浸编辑已实现：点击“第一人称”或按 G，建筑铺满窗口，使用准星在室内放置、删除和选择方块；Esc 打开材料与工具菜单，“退出第一人称”恢复原视图与面板布局。操作与验证见 [E1 验收](docs/E1_ACCEPTANCE.md)。把 OBJ/glTF 转成方块的 E2 仍未开始，规则见 [扩展计划](docs/PLANNED_EXTENSIONS.md)。

源码采用 MIT 许可；Minecraft 素材和第三方建筑不受本项目 MIT 许可覆盖。用户项目、游戏资源、日志、导出及本地验收产物留在 `.local/` 和 `artifacts/`，不提交到源码仓库。
