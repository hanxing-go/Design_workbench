# P1–P5 验收记录

日期：2026-10-09。版本：0.1.0。结论：原路线 27 项任务已在下列声明范围内完成，交付点 A 达成。P6–P8 仍未开始。使用方法见 [快速开始](QUICKSTART.md)，兼容范围见 [资源与限制](RESOURCES_AND_LIMITS.md)。

## 逐项映射

路径相对于项目根目录，dw 表示 `src/design_workbench/`。

| 任务 | 实现 | 验收证据 |
| --- | --- | --- |
| P1.1 独立工程 | Git、pyproject.toml、uv.lock、src 布局、GUI extra | 锁定环境及干净 wheel 安装；无旧 JS 运行依赖 |
| P1.2 依赖与目录 | dw/domain、application、adapters、interfaces；config.py | tests/unit/test_foundation.py 的依赖方向与便携路径检查 |
| P1.3 配置/错误/日志/CLI | dw/config.py、logging.py、domain/errors.py、interfaces/cli.py | CLI 帮助/info、配置优先级、HTTP 请求关联与冲突错误 |
| P1.4 持续检查 | Ruff、strict mypy、pytest、前端检查、.github/workflows/check.yml | Windows 与 WSL 本地检查；远端 CI 只配置未运行 |
| P1.5 可安装/路径独立 | wheel 含注册表及 static；scripts/install_smoke.py | 源码目录外的临时 venv：CLI、创建/编辑/导出、静态文件检查 |
| P2.1 注册材料 | dw/data/registry-1.20.1.json、resources/catalog.py | tests/unit/test_catalog.py；1,003 块、24,135 状态、分页/合法性/中文 |
| P2.2 资源管理 | resources/acquire.py、pack.py、manifest 与相对 current 指针 | 官方哈希与版本核对；资源复制到独立路径后的实际模型验证 |
| P2.3 模型/纹理 | pack.py 的继承、variants、multipart、旋转/UV/图集 | tests/integration/test_resources.py；代表性几何/纹理与方向截图 |
| P2.4 材料查看 | frontend/src/main.ts、viewer.ts 的实际缩略图/属性 | artifacts/representative-materials.png；浏览器材料与属性操作 |
| P2.5 支持分类 | resources audit、pack.support | artifacts/resource-coverage.json；21,879 静态、2,175 特殊、81 不可见、0 缺项 |
| P3.1 场景 | domain/models.py、editing.py，分组/区域、保护位置与 NBT 附件 | tests/integration/test_scene.py、test_litematic.py；实体内容独立保留，不作为状态字段 |
| P3.2 存储 | adapters/storage/sqlite.py，schema=2、16³ 分块/局部调色板 | 重开、分支、迁移备份、事务中断及写竞争测试 |
| P3.3 基本编辑 | domain/editing.py；set/fill/delete/replace/group/transform | 单元/集成及实际 GUI；楼梯方向、镜像、碰撞、完整门部件、受保护格 |
| P3.4 编辑可靠性 | application/scenes.py、SQLite 原子状态/历史/request 指纹 | test_atomic_preview_revision_and_idempotence、历史重开与单调修订测试 |
| P3.5 CLI/恢复 | interfaces/cli.py 调用同一 SceneService | wheel CLI 创建/编辑/导出；os._exit 中断真实事务；迁移失败保留原件 |
| P4.1 NBT 实现 | nbtlib，Litematica v6 适配 | tests/integration/test_litematic.py；独立 litemapy 作者样例与输出核对 |
| P4.2 格式细节 | formats/litematic.py 的负尺寸、多区域、位打包、特殊空气 | 独立负尺寸/跨位样例、特殊空气删除和跨区域移动回读；长整数保留 |
| P4.3 复杂内容 | 原压缩 NBT 附件、保护位置/未知区域保护 | 方块实体/实体/unknown tags 保留与保护编辑测试；版本/重叠明确拒绝 |
| P4.4 导入导出 | SceneService import/export、GUI 上传/下载 | scripts/verify_exports.py 逐格核对木屋/教堂；67 方块实体及区域内容一致 |
| P4.5 预览 | packets.py、viewer.ts，多视角/剖切/比较；static 随 wheel | 真 Chrome、独立安装、church-full/cutaway 和材料截图；无外部网络请求 |
| P4.6 性能基线 | scripts/benchmark_core.py | artifacts/p4-baseline.json，先记录门槛再进行 P5 验收 |
| P5.1 面板/选择 | GUI 材料/属性、canvas 拾取、Shift/选区/分组/相机 | scripts/verify_browser.py 的真实属性、扩选、分组树和负 Y 拾取 |
| P5.2 实时编辑/差异 | GUI 预演/提交/历史/变换与前后比较 | 木屋流程、移动复制旋转镜像、取消预演；真实负 Y canvas 删除 |
| P5.3 增量更新 | packets.py 内容哈希、viewer.ts 分块/邻块重建、实例化/裁剪 | 教堂 62 块中局部编辑更新 2 块；常用透明与代表性方向目视核对 |
| P5.4 组合工具 | array/extrude/arc/roof/window | test_design_tools.py 与 GUI 全部工具表单；服务端读取确认结果 |
| P5.5 一致性 | domain/validation.py、建议预演入口 | test_consistency.py、GUI 检查；限定常见规则，不做完整游戏模拟 |
| P5.6 用户流程 | 浏览器新建/木屋/材料/屋顶/窗/放置/撤销重做/重开/导出 | artifacts/p5-browser-verification.json、前后截图及独立 export-crosscheck.json |

## 执行环境与结果

Windows 11，Python 3.12.7，Node.js 24.14.0，Chrome 154.0.8037.98。Windows pytest 25 项通过，其中 1 项真实浏览器、2 项实际资源测试。测试依赖 Starlette 提示未来迁移 httpx2 的弃用警告，不影响通过结果。

WSL Ubuntu 22.04，受管理 Python 3.12.15：22 项核心测试通过，浏览器/资源 3 项不在 Linux 本地运行；mypy、Ruff、构建和干净 wheel 安装通过。Linux 浏览器由 CI 配置承接，尚无运行证据。远端 GitHub Actions 尚未执行。

strict mypy 检查 27 个 Python 源文件通过，Ruff lint/format 通过；前端 TypeScript、Prettier、Vite 构建通过。Vite 对约 534 KB 的主包给出体积建议，当前无运行失败；后续可按实际需要分包。

Windows 与 Linux 安装验收均在独立临时 venv 中安装实际 wheel，从源码目录外执行 CLI，创建 18 格项目、编辑、导出并读取；确认注册表/前端进入安装包，不依赖旧仓库、CDN 或开发用 Node.js。

## 性能

以下是该 Windows 机器、官方 1.20.1 资源、36,094 格教堂的最后一次浏览器实测。P4 门槛已在首次 P5 验收前写入基线，未随结果修改。

| 指标 | P5 实测 | 预设门槛 |
| --- | ---: | ---: |
| 上传、导入并显示 | 1,301 ms | 15,000 ms |
| 1,000 格局部编辑并显示 | 726 ms | 3,000 ms |
| 保存/重读 | 575 ms | 2,000 ms |
| 导出 | 471 ms | 3,000 ms |
| 相机绘制 P95（30 帧） | 23.3 ms | 100 ms |
| 局部新增分块 | 2 / 全场景 62 | 少于全场景 |

浏览器脚本无 pageerror、无外部网络请求；720px 页面无水平溢出。冷启动包含已导入资源与本机浏览器缓存条件，不代表低配设备或远端网络基准。100,000 格扩展基准和峰值内存发布报告仍属 P8。

## 格式与视觉证据

独立读取器 litemapy 0.11.0b0：木屋 449 个非空气格、1,573 格选择体积；教堂 36,094 个非空气格、246,024 格选择体积，完整状态与坐标一致。教堂 67 个方块实体、Entities、PendingTicks、Position 和 Size 保留。

目视检查：完整方块、四向楼梯、半砖、玻璃、门、活板门、栅栏、墙、植物；木屋屋顶替换、窗组、教堂全景/剖切和窄屏。静态模型解析覆盖不能推导游戏光照、群系颜色或特殊实体的完整显示。没有游戏内 Litematica 客户端验收。

本地原始产物位于 artifacts/：p4-baseline.json、p5-browser-verification.json、export-crosscheck.json、resource-coverage.json、install-smoke-windows.json、install-smoke-linux.json 和 PNG。它们及第三方蓝图不提交到源码仓库。本报告保存任务、环境、结果及限制，供后续复测。

## 可重复命令

先按 QUICKSTART 准备环境、构建前端并安装官方素材。Windows：

```powershell
$env:DW_BROWSER_CHANNEL='chrome'
uv run pytest -q
uv run mypy
uv run ruff check .
uv run ruff format --check .
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
uv build
uv run python scripts/install_smoke.py
```

Linux 核心与安装：`bash scripts/linux_check.sh`；脚本隔离临时 venv，不覆盖 Windows 环境，固定 uv 版本并清理其自身临时目录。

扩展 GUI/教堂验收需运行中的服务、本地基线和作者样例 `.local/imports/azalea-church.litematic`：

```powershell
uv run python scripts/verify_browser.py
uv run python scripts/verify_exports.py
```

GUI 脚本会创建独立验收项目，不修改原基准项目。`DW_TEST_URL` 可覆盖服务地址。外部作者样例不随仓库分发，须从来源取得对应文件；资源数据版本不同则验收明确失败。

## 下一阶段入口

P6 复用当前应用服务和 GUI 渲染器，提供 MCP 工具与固定修订多视角 PNG，再以真实外部 AI 客户端验收。P7 才加入模型驱动、低频阶段调用、预算/取消/恢复和候选稿。当前没有自主设计结果或审美成功率声明。
