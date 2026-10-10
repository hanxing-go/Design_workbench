# P6 验收记录

日期：2026-10-10。结论：P6.1–P6.5 已实现并完成实际外部客户端、Windows 浏览器、两平台核心/安装验收，交付点 B 达成。P7/P8 与 E2 仍未开始。

## 任务与证据

| 任务 | 实现与验证 |
| --- | --- |
| P6.1 | 15 个版本化工具，CLI/HTTP/MCP 同一工具门面和 SceneService；真实 MCP 初始化、工具发现、字段校验、创建、预演、提交、历史、导入导出测试 |
| P6.2 | 真实 PNG、多视角、Y 剖切、自定义相机；capture.ts 直接复用 GUI Viewer；返回相机、尺寸、修订、资源与快照哈希 |
| P6.3 | SQLite 原子快照含 NBT 来源；并发写入后原快照哈希不变，透视 PNG 与修改前逐字节一致；新截图出现新建筑；旧修订提交与截图拒绝 |
| P6.4 | 编辑、空间、分页、JSON、像素、输出字节、队列和独立进程耗时预算；错误定位字段，截断不伪装完整结果 |
| P6.5 | 三种入口同请求与幂等结果一致；真实 Chrome、MCP ImageContent、HTTP PNG 下载、队列拒绝、取消、超时、失败和输出预算测试；CLI 修改后网页自动刷新 |

协议与浏览器测试分别在 `tests/contract/test_tools.py`、`tests/e2e/test_p6.py`。独立回读和外部 AI 记录位于忽略目录 `artifacts/p6/`。

## 实际外部 AI 客户端

驱动者是本次 Codex 对话中的 AI。它通过独立的 MCP Python SDK 客户端 1.30.0 调用 stdio 服务（工具版本 1.0.0，协议 2025-11-25）；辅助客户端只发送 Agent 选择的请求并保存结果，没有预制建造或改稿循环。平台自身没有调用模型，符合 P6 的外部客户端边界。

1. `catalog.search` 实际查询“木板”，返回橡木、云杉和白桦等合法材料。
2. `project.create` 创建独立木屋项目；`scene.commit_edit` 生成主体、基础、屋顶、入口及一扇窄窗，修订 r1，共 838 格。
3. `render.views` 返回正面、透视与 Y=3 的俯视剖切 PNG，Agent 实际读取三张图片。
4. Agent 观察到山墙缺口、正面窗户不对称和侧墙缺少窗户，在读图后生成修改；通过预演与原子提交补前后山墙、六扇窗、角柱与门楣。
5. r2 的四张 PNG 覆盖正面、透视、剖切及室内相机。Agent 实际读取结果，山墙闭合、窗户和内部空腔可见。
6. `asset.export` 导出最终 870 格；独立 litemapy 0.11.0b0 逐格核对所有非空气方块坐标、名称和完整属性，全部一致，DataVersion 3465。

项目 ID `21dfe9ef7492a7c442c88a1e2820b02b`。记录在 `artifacts/p6/ai-client/`，包括请求、每次协议响应、PNG、`visual-observation.md`、最终 `final.litematic` 和 `independent-export-report.json`。导出 SHA-256：`feee3839f03e045d4103e07634980f148d81e926ee1c65bc5b19d8833da005f6`。

这证明外部 AI 能操作并观察工作台；不据此宣称 P7 的平台内自主设计、通用建筑审美或 Minecraft 客户端内验收完成。

## 失败与修复

外部 MCP 客户端第一次截图超时，失败响应保留在 `04-draft-views/`。截图工作进程随后显式使用 DEVNULL 标准输入，避免继承 MCP 协议输入流。相同木屋在独立 CLI 与 MCP 客户端中重新验证成功；新增真实 MCP PNG 与取消测试覆盖该链路。失败尝试没有删除或改写为成功。

截图的自动取景按宽高比和视野计算安全距离，避免原轨道相机的近距离导致边缘裁切。自定义相机后恢复预设视野，防止下一张图继承上一张 FOV。

导出时间字段使重复生成字节不同，现使用持久化导出回执；同一请求在后续编辑或撤销后仍能取得原文件。SQLite 导出也在同一事务快照读取方块与 NBT。

Linux mypy 最初不接受 Windows 专属的 `CREATE_NO_WINDOW` 条件表达式；改为显式 `if sys.platform == "win32"` 分支后两平台严格类型检查通过。失败尝试保留在 `artifacts/p6/linux-check-attempt1.log`。

最终 Windows 全量第一次为 81 passed / 1 failed / 1 skipped：超时停止后子进程的日志文件句柄短暂尚未释放，回收任务目录遇到 WinError 32。现对服务拥有的绝对目录校验后进行最多 2 秒的有界重试，清理成功后才移除任务索引；没有吞掉清理失败。补充 0.01/0.15/0.3 秒连续超时回收和正常关闭的实际测试，P6 四项与最终全量通过。失败报告保留在 `pytest-windows-before-cleanup.xml/.log`。

本机执行 Playwright 管理的 Chromium 下载时官方 CDN 多次连接超时，未安装成功；Windows 的实际 PNG 与浏览器验证使用系统 Chrome 154.0.8037.98。本轮 Linux 只验证核心、协议与安装，没有执行 Linux 实际浏览器。CI 配置已增加 ai/render extras，仍需远端执行，不能把旧 P5 CI 结果当作本轮浏览器证据。

## 验证状态

| 检查 | 结果与本地证据 |
| --- | --- |
| Windows 全量 | 82 passed / 1 skipped，129.94 秒；`artifacts/p6/pytest-windows.xml`、`.log`。跳过项是既有的 Windows 打开 SQLite 文件不能替换 |
| 三入口与边界 | 9 项契约通过，含真实 MCP、重试/修订冲突、导出原字节与非法相机/超像素/视角限制 |
| P6 实际浏览器 | 4 项通过，39.79 秒；`artifacts/p6/pytest-p6-windows.xml`。覆盖真实 PNG、冻结修订、并发修改、HTTP 下载、CLI 刷新、错误浏览器、超时/取消、格数/空间/输出预算 |
| Linux 核心 | WSL Ubuntu 22.04 / Python 3.12，63 passed；`artifacts/p6/pytest-linux.xml`、`linux-check.log` |
| 两平台工程检查 | strict mypy、Ruff lint/format 通过；前端 TypeScript/Prettier 与 main/capture 完整构建通过 |
| 干净 wheel | Windows/Linux 安装 gui,ai,render extras，包内前端/注册表、18 格编辑导出、15 个 Schema、真实 MCP 初始化/调用通过；`install-smoke-windows.json`、`install-smoke-linux.json` |
| 实际外部 AI | 870 格木屋修订 r2；四张 PNG、协议记录、litemapy 全状态/坐标一致，见上文 |
| 100,000 格截图 | 原混合小镇夹具，三视角 768×768，包含 Y=10 剖切；总耗时 5,782 ms，worker 5,078 ms，所有图片 snapshot_cells=100,000；`artifacts/p6/large-capture/manifest.json` 与 PNG |

最终源文件、已打包前端、wheel 与验证报告哈希汇总在 `artifacts/p6/verification-manifest.json`。产物由当前开发工作区生成；本轮没有推送、发布或游戏客户端验收。使用命令和接入取舍见 [P6_USAGE](P6_USAGE.md)。
