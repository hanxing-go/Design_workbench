# AI 设计任务、预算与候选稿

更新日期：2026-10-10。外部 AI 的创作链路已经实际跑通：苦情巨树 478,228 格 / r55，迪迦初版 104,633 格 / r7，650 格高的迪迦版本 455,858 格 / r26。它们均经 CLI 创建与修改、真实截图检查及独立蓝图核对。巨树与迪迦初版还保留了看图后的修订记录。这些已有结果不需要重新实现。

本次新增工作台对外部 AI 任务的持久化控制。没有新增供应商 API 连接或平台内自动模型调用；创建任务后，仍由用户正在使用的 AI 接入并执行。P7 的任务控制部分已实现，平台内模型适配、自动调度及原路线的三类任务各三次验收仍未完成。

## 网页使用

1. 打开项目，点击顶部 **AI 任务**，填写需求、可选模型名称和预算。
2. 把任务编号交给外部 AI。它使用 `design.update/call/propose/usage` 工作；页面自动更新阶段、消息、工具/模型调用数、时长、修改批次、tokens 与费用。
3. AI 修改已有建筑时必须先提交预演。页面显示修改原因、基准修订和格数；点击“在画布查看”显示差异，再回到面板确认或拒绝。
4. 保存候选稿时填写名称和评价。候选稿保存完整 SQLite 工程，包括状态、分组、区域、保护格、原始 NBT、历史，以及关联修订的截图和需求/模型/用量资料。后续编辑和撤销不会改变该快照。
5. “打开副本继续修改”创建新项目和新的设计任务，继承原始需求、候选稿反馈及模型名称；原项目和候选稿保持不变。工程也可下载保存。

新任务默认所有 AI 编辑都要确认。只有**空项目**可以选择“自动生成初稿”；进入 reviewing/revising/exporting 后，这项权限永久撤回，不能通过退回 building 阶段重新启用。用户在普通编辑器中的手工操作始终可用；确认预演时仍会重新检查修订，过期预演不会覆盖手工修改。同一项目只允许一个进行中或待确认任务。

等待用户确认时暂停时长计量；取消、失败或预算停止后也暂停。继续时保留全部消耗和记录，丢弃旧预演，AI 必须重新读取当前修订。失败的操作保留错误；已成功操作使用原 request_id 重试，不重复计数或提交。

## 预算与取消的实际范围

默认预算：256 次工具、64 次模型调用、30 分钟活动时间、3,000,000 tokens、64 批修改；费用上限可选，单位 USD。工作台直接计量受控工具、活动时间和成功修改批次。最后一个预算内的预演仍可确认，下一次超限操作会停止。扩大预算不重置已消耗用量。

**模型调用数、tokens 和费用来自外部 AI 回报的实际累计计数。** 未上报显示“尚未报告”；未知费用为 null，不按零费用处理，不按字数估算，也不擅自使用某个费率换算。缓存输入包含在 input_tokens 中，推理输出包含在 output_tokens 中，不能再相加。平台会在收到超额计数后停止后续受控操作，但不能撤销外部客户端已经发出的模型请求或控制其独立账单。

取消后拒绝新的受控调用和编辑，保留已经提交的原子批次、历史、图片和候选稿。尚在执行的原子编辑完成或失败后，取消生效于下一步；不能中途截断 SQLite 事务。所属截图由任务后台监测预算并停止自有工作进程，不依赖网页持续轮询。无法终止用户在其他应用中运行的外部 AI 进程。

设计任务绑定项目。任务存在且未完成时，基础 AI 修改工具会要求改用受控入口，避免旧的 `scene.commit_edit` 请求绕开任务。确认入口专用于网页，不加入 AI 工具目录。本地 HTTP 服务仍按既有的本机信任边界运行，无远程身份认证；此区分不是针对有任意本机访问权限的程序的安全隔离。

## CLI / MCP 接入

基础 15 个工具保持可用，新增 11 个控制工具：

| 工具 | 用途 |
| --- | --- |
| design.start / list / status | 创建、列出、观察持久任务 |
| design.update | 报告 planning/building/reviewing/revising/exporting 阶段 |
| design.usage | 报告累计 input_tokens、cached_input_tokens、output_tokens、model_calls、可选 cost_usd 及 source |
| design.call | 在预算内调用材料查询、场景查询/预演、编辑、截图或导出 |
| design.propose | 带说明的改稿预演，等待用户确认 |
| design.cancel / resume / finish | 停止、明确继续或记录结果；成功前必须有独立候选稿 |
| candidate.save | 保存指定修订的完整候选稿 |

所有调用仍使用 `design-workbench tool 工具名 请求.json --config ...`；操作正在运行的网页工作台时建议加 `--server http://127.0.0.1:8765`。MCP 使用相同 Schema。

启动请求示例（project 替换为真实项目编号，expected_revision 替换为当前修订）：

```json
{
  "project": "项目编号",
  "request_id": "start-design-001",
  "expected_revision": 0,
  "prompt": "设计木屋，保留可进入的室内空间",
  "budget": {"tool_calls": 128, "model_calls": 32, "seconds": 1800, "tokens": 3000000, "revisions": 32}
}
```

将原有工具包进受控调用：

```json
{
  "run_id": "返回的任务编号",
  "request_id": "observe-001",
  "tool": "scene.summary",
  "arguments": {}
}
```

`design.call` 自动绑定项目，不能传入其他项目。已有建筑的 `scene.commit_edit` 会转为待确认预演。需要详细改稿理由时直接使用 `design.propose`，其 request 字段就是原有 EditRequest。

截图同样通过 `design.call` 包装 `render.views`。本机 CLI 同步截图需指定 `--output-dir`；wait=false 必须使用长期运行的 HTTP 或 MCP 服务。成功图片自动保存到任务目录，不随截图临时队列回收或服务正常关闭而删除；相同请求可重取保存的图片。未完成截图在服务重启后需使用新请求重新生成，旧截图查询会明确报告中断。

## 持久化与备份

- `<data_dir>/design-runs.sqlite3`：schema 1 的任务状态、预算、用量、事件、预演与幂等回执。
- `<data_dir>/design-candidates/<candidate_id>.dwbench`：通过 SQLite 在线 backup 获得的固定修订，含 WAL 中已提交数据；保存后记录 SHA-256。
- `<data_dir>/design-candidates/<run_id>/<render_task>/`：固定修订的 PNG。

备份设计控制数据时先关闭服务，再一起复制上述数据库和候选目录。候选稿打开时核对 SHA-256；不覆盖原项目，重复打开同一 request_id 返回原副本。更高数据库 schema 明确拒绝，损坏文件保留。

## 验证与证据

10 项契约测试覆盖既有建筑保护、过期预演、确认/拒绝与重复请求、预算/取消/恢复、累计用量、候选 NBT/历史保存、并发重复提交、自动初稿权限撤回、手工编辑后自动权限撤回，以及最后一项预算内预演。

2 项真实 Chrome 测试覆盖网页新任务、18 格预演确认、拒绝、候选保存/下载与实际 PNG、服务重启后图片和任务保留、错误恢复、超限后扩大预算、390px 窄屏副本编辑，以及取消自有截图进程和无页面轮询的异步时间预算。测试计数夹具不是实际模型用量，不作为自主设计效果证据。

命令：

```powershell
.venv/Scripts/python.exe -m pytest tests/contract/test_design_controls.py -q
$env:DW_BROWSER_CHANNEL = "chrome"
.venv/Scripts/python.exe -m pytest tests/e2e/test_design_ui.py -q
```

真实测试代码随仓库提交；桌面和窄屏 QA 图片保存在忽略目录 `artifacts/ai-controls/`。旧作品的完整请求、失败和实际核验分别在 `artifacts/kq-tree/TEST_REPORT.md`、`artifacts/tiga/REPORT.md`、`artifacts/tiga-classic/verification.json`；它们继续留在本机，不随源码推送第三方参考图、游戏素材或用户工程。

本轮 Windows 完整回归 93 passed / 1 skipped；跳过项为原有 Windows 打开 SQLite 文件不能替换。最后增加“手工编辑撤回自动初稿权限”后，最终 10 项契约与 2 项真实 Chrome 控制检查通过。记录为 `artifacts/ai-controls/pytest-windows.xml` 和 `pytest-controls-final.xml`。strict mypy、Ruff lint/format、TypeScript/Prettier/build 通过；最终隔离 wheel 的 gui/ai/render extras 安装、编辑导出、任务预演门槛、取消后重开、候选副本与真实 stdio MCP 工具发现通过，见 `install-smoke-windows-final.json`。本轮未在 Linux 本地执行新增控制；Windows/Linux CI 持续验证对应范围。
