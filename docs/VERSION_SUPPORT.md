# Minecraft Java 多版本支持

项目按版本保存与加载注册表、官方资源和格式适配器。同一服务可以打开不同版本的项目，无需修改配置或重启。以下是明确支持的发行版本；其他版本（包括未列出的补丁版、快照、Bedrock 和模组方块）会返回 `UNSUPPORTED_VERSION`。

| Java 版本 | DataVersion | 注册方块 |
| --- | ---: | ---: |
| 1.20.1 | 3465 | 1,003 |
| 1.20.2 | 3578 | 1,003 |
| 1.20.3 | 3698 | 1,058 |
| 1.20.4 | 3700 | 1,058 |
| 1.20.5 | 3837 | 1,060 |
| 1.20.6 | 3839 | 1,060 |
| 1.21 | 3953 | 1,060 |
| 1.21.1 | 3955 | 1,060 |
| 1.21.3 | 4082 | 1,084 |
| 1.21.4 | 4189 | 1,095 |
| 1.21.5 | 4325 | 1,104 |
| 1.21.6 | 4435 | 1,105 |
| 1.21.8 | 4440 | 1,105 |
| 1.21.9 | 4554 | 1,166 |
| 1.21.10 | 4556 | 1,166 |
| 1.21.11 | 4671 | 1,166 |
| 26.1 | 4786 | 1,168 |

## 网页使用

首页「开始建造」选择 Minecraft Java 版本。首次使用点击「下载所选版本的官方素材」，下载完成后直接创建项目。已有项目保留创建时的版本，打开或切换项目后材料、缩略图、图集、编辑校验和导出自动跟随项目。

首页导入 `.litematic` 时先读取真实 MinecraftDataVersion，自动创建对应版本的项目。若该版本素材尚未安装，会提示先下载。工作台内导入仍要求蓝图与当前项目版本相同；不能把新版建筑直接覆盖到旧版项目。

## CLI 与 AI

配置中的 `minecraft_version` 是默认创建版本，不覆盖已有项目。可在命令中指定版本：

```powershell
uv run --extra gui design-workbench resources setup --minecraft-version 1.21.4 --config config.example.toml
uv run design-workbench create .local/data/pale-oak.dwbench --minecraft-version 1.21.4 --config config.example.toml
uv run --extra gui design-workbench serve --config config.example.toml
uv run design-workbench tool versions.list empty.json --config config.example.toml
```

`empty.json` 内容为 `{}`。AI 的 `project.create` 在 `request.minecraft_version` 指定版本；`catalog.search` / `catalog.material` 用 `project` 选择该项目的材料，或用 `minecraft_version` 查询指定版本。若同时指定二者，版本必须一致。持久 AI 任务的材料查询自动绑定任务项目。

HTTP 提供 `/api/versions`、`POST /api/resources/setup`（`{"minecraft_version":"1.21.4"}`）、`POST /api/blueprints/info`（上传 `file`）。`/api/info`、`/api/catalog`、`/api/material/{name}`、`/api/atlas.png` 支持 `project` 或 `minecraft_version` 查询参数，未提供时使用配置默认版本。

## 资源、保存与格式边界

注册表来自 PrismarineJS/minecraft-data 固定提交 `33a0f3e7323e124a81960a6d6c62df797d69cd85`，每份文件保存源 URL 与 SHA-256。下载的客户端按 Mojang 清单 SHA-1 验证，导入时检查客户端版本与 DataVersion；模型、贴图和图集按版本隔离在 `.local/cache/resources/<版本>/`。

项目固定游戏版本与 DataVersion，服务读元数据后选择对应编辑器和格式适配器。已有 1.20.1 数据库无需迁移。SQLite 保存完整状态、原始 NBT、保护格和历史；资源 manifest 记录组合哈希，渲染包和截图记录实际资源哈希。资源首次安装后运行中的服务可直接识别，网页创建时重新读取就绪状态。

蓝图支持 Litematica v5/v6，不重叠区域；原件导出保留其格式版本、未知 NBT 与实体内容，新项目导出 v6。游戏 DataVersion 必须严格匹配，不改写版本号来冒充转换。跨版本转换尚未实现；目标版本缺少的块不能直接丢弃。

1.21 的裸贴图变量以及 26.1 的 `sprite` / `force_translucent` 贴图对象已适配。特殊实体、动态模型仍按支持标记显示限制，预览不模拟完整游戏光照、物理或动画。全状态解析通过不等于所有状态与游戏逐像素一致。

## 验证和新增版本

```powershell
uv run --extra gui python scripts/audit_versions.py --download
uv run --extra gui --extra ai --extra render pytest tests/contract/test_versions.py -q
$env:DW_BROWSER_CHANNEL = 'chrome'
$env:DW_TEST_VERSIONS = '1.20.1,1.21.4,26.1'
uv run --extra gui --extra ai --extra render pytest tests/e2e/test_version_ui.py -q
```

资源审计逐状态检查支持分类，并构建每个方块的默认模型；结果含资源哈希和注册表来源，保存于 `artifacts/version-audit.json`。游戏素材和这些本地产物不提交到 Git。

新增发行版本需要从固定上游提交生成注册表，例如 `python scripts/fetch_registry.py --version 1.21.4 --commit <完整提交哈希>`；再完成对应官方资源审计、模型适配、蓝图往返和浏览器验证后加入发行范围。程序从打包的 `registry-*.json` 列举支持版本，未来 MC 更新不会未经验证自动启用。

逐版本状态数、实际验证和修复记录见 [多版本验证记录](VERSION_ACCEPTANCE.md)。
