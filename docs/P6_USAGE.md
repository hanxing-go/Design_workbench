# P6：CLI、HTTP 与 MCP 的 AI 操作入口

P6 让外部 AI 使用现有设计工作台；平台内模型调度、预算与候选稿仍属于 P7。所有入口调用同一场景服务，模型不需要逐格输出整栋建筑。验收证据见 [P6_ACCEPTANCE](P6_ACCEPTANCE.md)。

## 为何 CLI 优先，同时保留 MCP

CLI 适合有终端和本地图片读取能力的 Agent：输入输出明确、便于脚本批处理、重放和调试。CLI 返回 JSON 与 PNG 路径，Agent 再读实际图片即可完成视觉反馈。MCP 提供标准工具发现、参数 Schema、结构化响应与 PNG ImageContent，便于兼容客户端直接连接。MCP 本身不提高建筑质量，也不负责运行模型。

两种接入共用 `interfaces/tools.py`，编辑最终进入 `SceneService`；HTTP 为网页和常驻截图任务提供同一入口。工具契约、修订冲突、幂等与预算都由服务实现，不能因切换入口而改变行为。新能力先在应用服务与 CLI 中可重放，再通过同一门面提供 MCP/HTTP。

公开的 [Blender MCP](https://github.com/ahujasid/blender-mcp) 可作工作流程参考。其 README 描述了 MCP 服务与 Blender 内 socket 插件，模型通过 Blender Python 操作场景，再读取场景摘要和视口/多角度图像检查。具体视频可能使用其他实现；这个项目不能证明某段未核实视频的接法。

对应本项目，模型选择尺寸、比例、材料和局部改动，现有填充、挤出、阵列、圆弧、屋顶与窗组工具负责展开合法方块。`scene.summary/inspect` 对应场景读取，`scene.preview_edit/commit_edit` 对应建造和修改，`render.views` 对应视觉检查，`asset.export` 对应交付。需要新几何能力时扩展确定性编辑工具，并沿用预演、原子事务和历史。

近期使用方式是外部 Agent 执行“需求 → 查询材料 → 组合建造 → 多角度/剖切看图 → 局部修改 → 导出”，木屋、苦情巨树和迪迦已实际验证。网页现有持久任务、阶段/预算、取消恢复、改稿确认和候选稿，接入见 [AI_CONTROLS](AI_CONTROLS.md)。平台内自主模型配置和调度仍待 P7。Blender 网格转方块是另一个 E2 方向，尚未实现；导入网格后的材质匹配和体素化验收不由 MCP 自动解决。

## 安装与浏览器

```powershell
uv sync --locked --extra gui --extra ai --extra render
uv run python -m playwright install chromium
uv run design-workbench resources setup --config config.example.toml
```

`ai` 是 MCP Python SDK，`render` 是 Playwright，`gui` 包含网页服务与素材图集所需依赖。仅查询、编辑和导出不需要启动浏览器。浏览器是本机依赖，不打进 wheel；缺少浏览器时截图返回 `BROWSER_UNAVAILABLE`。Windows 已有 Chrome 时，可在 TOML 配置 `browser_channel = "chrome"`，或设置 `DW_BROWSER_CHANNEL=chrome`；默认使用 Playwright 管理的 Chromium。

## CLI 优先的接入

```powershell
uv run design-workbench tools --config config.example.toml
uv run design-workbench catalog "橡木" --config config.example.toml
uv run design-workbench tool project.create create.json --config config.example.toml
```

`tools` 输出完整 JSON Schema。`tool` 的输入是 JSON 文件、输出是 JSON，出错时退出码为 1。现有 `create/summary/edit --preview/history/import/export` 命令继续可用；`inspect` 可对任意项目文件使用选区 JSON。新版 `tool` 使用配置 `data_dir/projects` 中的项目 ID，和 GUI、MCP 一致。

创建请求 `create.json`：

```json
{
  "schema_version": 1,
  "request_id": "create-cabin-001",
  "request": { "name": "AI 木屋" }
}
```

记录返回的 `project_id`。后续编辑请求包含 `project` 和现有编辑 `request`：

```json
{
  "schema_version": 1,
  "project": "返回的项目ID",
  "request": {
    "expected_revision": 0,
    "request_id": "cabin-body-001",
    "operations": [
      {
        "op": "fill",
        "bounds": { "low": [0, 0, 0], "high": [8, 6, 10] },
        "state": { "name": "minecraft:oak_planks" },
        "hollow": true,
        "group": "body"
      }
    ]
  }
}
```

```powershell
uv run design-workbench tool scene.preview_edit edit.json --config config.example.toml
uv run design-workbench tool scene.commit_edit edit.json --config config.example.toml
uv run design-workbench tool render.views views.json --config config.example.toml --output-dir artifacts/my-cabin/r1
```

截图请求 `views.json`：

```json
{
  "project": "返回的项目ID",
  "request": {
    "expected_revision": 1,
    "request_id": "observe-cabin-r1",
    "width": 768,
    "height": 768,
    "views": [
      { "name": "front" },
      { "name": "iso" },
      { "name": "top", "layer": 3 }
    ]
  }
}
```

CLI 将实际 PNG 与 `manifest-任务ID.json` 保存到指定目录。给不同修订使用不同目录；输出文件有内容冲突时拒绝覆盖。Agent 需要读取返回的 PNG，才能完成看图改稿。

## MCP

stdio 服务启动命令：

```powershell
uv run design-workbench mcp --config config.example.toml
```

客户端也可直接启动虚拟环境的 Python：`python -m design_workbench.interfaces.cli mcp --config 配置文件的绝对路径`。按所用客户端的配置格式填写 command/args；不需要为本项目配置模型凭据。协议输出只走 stdout，日志写入配置的 log_dir。

服务器名称 `design-workbench`，工具契约版本 `1.0.0`；每个请求和 JSON 结果的 `schema_version=1`。MCP 的 `render.views` 和完成后的 `render.status` 返回 PNG ImageContent，并附带结构化元数据。

| 工具 | 用途 |
| --- | --- |
| catalog.search / catalog.material | 材料分页、中文/英文名称、合法属性、规范状态和支持范围 |
| project.list / project.create | 列出项目、创建项目；创建按 request_id 幂等 |
| scene.summary / scene.inspect | 修订、材料统计、分组及范围/名称/分组/区域选区 |
| scene.preview_edit / scene.commit_edit | 预演与原子批次提交 |
| history.undo / history.redo | 撤销与重做 |
| asset.import / asset.export | 本机蓝图文件导入导出；导出需要 request_id，返回路径、哈希与保留报告 |
| render.views / render.status / render.cancel | 固定修订的实际截图、任务状态和取消 |

修改重试使用相同 request_id 与相同参数；换内容要换 ID。导出回执保存原文件字节，重试不会因为文件时间字段变化而产生另一份结果。`REVISION_CONFLICT` 返回当前修订，Agent 应重新读取场景、看图并生成新编辑，不直接把旧请求的修订号改大。

## HTTP 与异步截图

启动 `serve` 后：

| 路径 | 用途 |
| --- | --- |
| GET /api/tools/v1 | 工具说明和 Schema |
| POST /api/tools/v1/{name} | 调用与 CLI/MCP 相同的工具 |
| POST /api/projects/{id}/views | 直接提交截图请求 |
| GET /api/render-jobs/{task_id} | 状态、进度、结果 |
| POST /api/render-jobs/{task_id}/cancel | 取消任务 |
| GET /api/render-jobs/{task_id}/images/{index}.png | 下载 PNG |

在截图 `request` 中指定 `wait=false`，先得到 task_id，再查询或取消。CLI 使用 `tool ... --server http://127.0.0.1:8765` 时也可以控制这些任务；独立 CLI 进程只支持等待截图完成并保存结果。任务在服务进程内，服务正常关闭时清理其拥有的临时目录；任务 ID 不跨服务重启保存。客户端应保存需要保留的 PNG。

网页每 1.5 秒检查外部修订并增量刷新。查看旧画面的比较模式保留当前显示；切回当前设计时再读取新修订。外部修改不会替用户提交已有预演，旧预演仍受修订检查保护。

## 截图一致性与限制

接收任务时在一个 SQLite 读事务里读取方块和 NBT 来源。随后场景快照与贴图固定，浏览器只读取此快照，和 UI 共用 `Viewer`、材质、模型、透明排序及剖切逻辑。结果记录 revision、resource_hash、snapshot_sha256、atlas_sha256、相机、剖切层和像素尺寸。等待纹理与网格构建完成后才截取实际画布。

支持 front、side、back、top、iso、custom；custom 必须提供 position、target、fov。bounds 只指定取景范围，不删除范围外的建筑；layer 才控制 Y 剖切。截图中的特殊内容警告随结果返回，支持范围沿用现有渲染器。

默认限制：

- 单次工具输入 4 MB、JSON 响应 2 MB；列表缩短时显式返回 response_truncated 与原总数。
- 普通工具独立进程执行，30 秒超时；超时响应后不能继续运行该工作进程。恰好已经提交的修改通过同一 ID 重试回读。
- 编辑沿用 256 项操作、500,000 个触达格、250,000 个存储格及现有工作区边界；选区/取景体积上限 2,000,000。
- 截图最多 100,000 个存储格、6 个视角、总计 8,000,000 像素、PNG 总计 16 MB；单张尺寸 64–1600。
- 截图默认总时限 60 秒，最多配置到 120 秒；2 个并行工作进程，最多保留 16 个任务。满队列先回收已结束任务，全部活动时拒绝新增。
- 失败、超时与取消有明确状态；终止所拥有的截图进程树，移除未完成 PNG，不写场景。

## 重放外部客户端记录

`scripts/p6_mcp_client.py` 是独立 stdio 客户端，实际执行 initialize/list_tools/call_tool，保存协议版本、请求、结果和 PNG。下一步操作由调用它的 Agent 在读图后选择，它不包含自动造房脚本：

```powershell
uv run python scripts/p6_mcp_client.py render.views views.json --config config.example.toml --output-dir artifacts/client/r1
```

模型驱动的完整验收经过及失败尝试见 [P6_ACCEPTANCE](P6_ACCEPTANCE.md)。
