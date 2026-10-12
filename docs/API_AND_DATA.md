# API 与数据契约

当前应用版本 0.1.0；编辑/工具请求 schema_version=1；MCP 工具服务版本 1.0.0；项目 SQLite schema=3；资源清单 schema_version=1；蓝图 Version=6。它们不是同一个版本号。

## 编辑请求

传输使用 JSON，权威建筑保存在 SQLite 分块中。模型或用户只需发操作，不必逐格列出整栋建筑。例如一次生成 18 格盒体：

```json
{
  "schema_version": 1,
  "expected_revision": 0,
  "request_id": "example-fill-001",
  "operations": [
    {
      "op": "fill",
      "bounds": {"low": [0, 0, 0], "high": [2, 1, 2]},
      "state": {"name": "minecraft:oak_planks", "properties": {}},
      "group": "body",
      "hollow": false
    }
  ]
}
```

字段来自 `application/contracts.py` 的 Pydantic 判别联合。未知字段拒绝，坐标必须是整数。材料由 1.20.1 注册表进一步验证；可省略合法属性并补默认值，非法名称/属性/取值返回错误。

`expected_revision` 必须匹配当前场景。`request_id` 表示同一逻辑修改：相同 ID、相同内容重试返回原结果；换内容复用 ID 返回 REQUEST_ID_REUSED。预演不改状态，最终提交仍重新核对修订。

| op | 主要字段与范围 |
| --- | --- |
| set | blocks：position、state、可选 group |
| place | support、face、heading、hit_height、ground、state、group；按支撑面自动定向，见 [自动吸附](PLACEMENT_SNAP.md) |
| painting | support、face 为水平四向、variant=auto 或官方图案名；创建画实体 |
| delete_painting | id：新增画的 UUID |
| fill | bounds、state、group、hollow；闭区间盒体或外壳 |
| delete | selector |
| replace | selector、state |
| group | selector、name |
| transform | selector、origin、offset、rotation=0/90/180/270、mirror=x/z/null、copy、overwrite、group |
| array | selector、count、step、overwrite、group；重复数含原件，各轴独立计算 |
| extrude | polygon：XZ 整数顶点、base_y、height、state、group；按格中心填充简单二维轮廓 |
| arc | center、radius、thickness、height、start、end、state、group；XZ 平面的角度区间，单位度 |
| roof | bounds、ridge_axis=x/z、height、state、group；双坡、选区 low.Y 为檐口 |
| window | bounds、axis=x/z、frame、glass、group；单格厚矩形窗组 |

selector 可包含 bounds、name、group、region，多个条件取交集。屋顶/窗组/轮廓不是独立对象系统，输出是普通可编辑格。圆弧不跨越 360→0 的区间，需拆成两次；挤出未提供通用 CAD 拓扑修复。

## HTTP

本地服务同时提供 `/docs` 和 `/openapi.json`；当前 HTTP 路径为 `/api/`，编辑体有独立 schema 版本。P6 已提供 CLI/HTTP/MCP 共用的版本化工具，完整格式见 [P6_USAGE](P6_USAGE.md)。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /api/info | 版本、资源准备状态及清单 |
| GET | /api/catalog | query、category、offset、limit 分页 |
| GET | /api/material/{name} | 模型与贴图信息；properties 是 JSON 字符串查询参数 |
| GET | /api/atlas.png | 本地纹理图集 |
| GET | /api/paintings | 画的图案与尺寸 |
| GET / POST | /api/projects | 列表 / 创建 |
| GET | /api/projects/{id} | 摘要、历史、修订 |
| POST | /api/projects/{id}/inspect | selector；limit 默认 128、最大 2048 |
| POST | /api/projects/{id}/preview | 编辑预演；差异最多返回 10,000 格并标明截断 |
| POST | /api/projects/{id}/edit | 原子提交编辑 |
| POST | /api/projects/{id}/history/{undo或redo} | expected_revision、request_id |
| POST | /api/projects/{id}/import | multipart：file、expected_revision、request_id |
| POST | /api/projects/{id}/export | expected_revision、allow_lossy；返回二进制蓝图和 X-Export-Report |
| POST | /api/projects/{id}/render | 已知 chunk_versions；返回增量分块、模型和警告 |
| GET | /api/projects/{id}/consistency | 规则问题与待预演建议 |
| GET | /api/tools/v1 | 15 个基础工具 + 11 个设计控制工具及完整 JSON Schema |
| POST | /api/tools/v1/{name} | 与 CLI/MCP 共用的工具请求 |
| POST | /api/projects/{id}/views | 固定修订的实际多角度 PNG；wait=false 异步返回任务 |
| GET | /api/render-jobs/{task_id} | 截图状态、进度与结果 |
| POST | /api/render-jobs/{task_id}/cancel | 停止截图任务与自有进程树 |
| GET | /api/render-jobs/{task_id}/images/{index}.png | 下载生成的 PNG |
| GET / POST | /api/projects/{id}/design-runs | 列出 / 创建持久设计任务 |
| GET | /api/design-runs/{run_id} | 阶段、预算、用量、预演、候选稿与事件 |
| POST | /api/design-runs/{run_id}/{cancel或resume或finish} | 取消、保留用量继续、记录结果 |
| POST | /api/design-runs/{run_id}/decision | 用户确认或拒绝 proposal_id；确认时检查修订 |
| POST | /api/design-runs/{run_id}/candidates | 保存 expected_revision 对应的完整候选稿 |
| POST | /api/design-runs/{run_id}/candidates/{candidate_id}/open | 新项目副本和继承需求/反馈的新任务 |
| GET | /api/design-runs/{run_id}/candidates/{candidate_id}/download | 下载不可变 SQLite 工程 |
| GET | /api/design-runs/{run_id}/renders/{task_id} | 查看受控截图；已完成 PNG 持久保留 |

工作台默认监听 127.0.0.1，无远程鉴权或多人实时同步设计。CLI 可以使用任意项目文件路径；GUI 管理配置 data_dir 下的 projects 目录。

## 错误

领域错误包含 code、message、location、revision；HTTP 增加 request_id 并返回同名响应头。修订冲突、碰撞、重复 ID 等返回 409，缺项目/任务/图片/导入资产返回 404，截图队列满返回 429，普通工具硬超时返回 504，其余已知校验错误返回 422。请求字段错误包含 details。已接收的截图任务在结果中返回 failed/timed_out/cancelled 及具体错误。

常见错误：INVALID_REQUEST、UNKNOWN_BLOCK、INVALID_STATE、OUT_OF_BOUNDS、EDIT_LIMIT、REVISION_CONFLICT、REQUEST_ID_REUSED、EDIT_COLLISION、PROTECTED_CONTENT、INCOMPLETE_MULTIBLOCK、VERSION_MISMATCH、REGION_OVERLAP、EXPORT_REGION_OVERLAP、MISSING_RESOURCE。

## 保存、历史与恢复

项目使用 16³ 分块、局部调色板和压缩内容。一个 SQLite 事务同时写入分块、修订、差异、事件、请求指纹和必要的原始蓝图附件。撤销/重做也产生单调递增修订；撤销后新编辑清空重做分支。

异常退出后 SQLite 回滚未提交事务；已测试写入竞争和进程中断。重开项目会读取持久化历史。schema 1/2→3 迁移前使用 SQLite backup 创建 `.v1-backup-*` 或 `.v2-backup-*`，迁移失败保留原件；未知或更高 schema 明确拒绝。新增画与方块共用事务和历史，保存在场景元数据。不是自动恢复任意损坏数据库的工具。

手工备份前先关闭服务，再复制项目文件；不要在事务进行时仅复制主文件而漏掉 WAL。恢复时保留原损坏文件，将已核验备份复制为新项目路径后打开。CLI 可查询摘要，GUI 项目列表会报告不能读取的文件。

## 配置

优先级：显式覆盖 > DW_* 环境变量 > TOML > 默认值。`--config` 指定文件，DW_CONFIG 可指定默认配置。TOML 的相对路径以配置文件所在目录为基准；环境变量中的相对路径以进程目录为基准。

默认限制：250,000 个存储格；一次编辑触达 500,000 格、256 项操作；蓝图区域总体积 2,000,000 格；输入压缩文件 32 MB、解压 64 MB。它们是资源预算，不是交互流畅度承诺。

默认新建工作区 X/Z=-512..511，Y=-64..511。GUI/HTTP 可在创建请求指定范围。data_dir、cache_dir、log_dir 分开配置，日志轮转 2 MB×4；没有后台模型任务或凭据配置。

设计控制使用单独 schema 1 数据库，保持项目 SQLite schema 2。预算、累计计数、暂停/恢复、用户确认与快照规则见 [AI_CONTROLS](AI_CONTROLS.md)。工具结果可包含持久化的 error 字段；客户端须检查错误，不把 HTTP 成功传输当作设计操作成功。

P6 默认普通工具硬超时 30 秒，输入 4 MB、JSON 响应 2 MB；截图 100,000 个存储格、6 视角、8M 像素、16 MB PNG、60 秒、2 个工作进程和 16 个任务。新增创建/导出回执保证同一 request_id 重试；导出保存原字节。MCP 的 PNG 使用 ImageContent，CLI 将 PNG 与 manifest 保存到 output-dir，HTTP 提供下载 URL。截图任务生命周期和配置见 [P6_USAGE](P6_USAGE.md)。
