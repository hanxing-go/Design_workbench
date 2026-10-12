# Windows 便携包

标准包面向 Windows 10/11 x64，包含 Python 运行时、网页服务、注册表及已构建的前端。用户无需安装 Python、Node.js 或 uv。需要支持 WebGL 的浏览器；不包含官方游戏素材、用户作品、MCP SDK 或 Playwright。

## 使用

完整解压发布 ZIP，双击 `DesignWorkbench.exe`。首次启动选择“下载官方素材”，或导入已有 Minecraft Java 1.20.1 客户端 jar。下载使用现有官方清单与 SHA-1 校验，失败后可重试。界面显示下载、解析与启动阶段；本地 jar 未附加中文语言文件时，材料名称使用可用的默认名称。

素材准备完成后，自动打开浏览器。关闭浏览器不会停止后台服务；点击启动窗口中的“退出工作台”或关闭启动窗口可正常停止。重复启动同一数据目录不会再起一份服务。优先使用本机端口 8765，被占用时自动选择空闲端口。

## 数据与升级

默认使用系统用户目录，启动窗口显示作品路径并可打开数据目录。工程在数据目录的 `projects/` 中，缓存与日志使用独立的系统用户目录。升级前退出旧版本，将新版本解压到新文件夹；同一 Windows 用户的默认数据保持不变。迁移或降级前应备份工程。

在可执行文件旁创建空的 `portable.flag` 可启用随目录移动模式：工程、素材和日志分别写入 `userdata/data`、`userdata/cache`、`userdata/logs`。文件夹必须可写。切换模式不会自动迁移数据；整包搬动时保留 `userdata`，升级时将该目录和标记文件复制到新包。

高级用户可在程序旁提供 `config.toml`，字段与仓库 `config.example.toml` 一致。路径相对于配置文件解析。便携模式的三个数据路径优先于配置与环境变量；其他配置仍遵循现有规则。请勿将自己的配置、作品和缓存放入公开发布包。

## 命令行

`WorkbenchCLI.exe` 提供原有 CLI，示例：

```powershell
.\WorkbenchCLI.exe --help
.\WorkbenchCLI.exe info
```

CLI 默认遵循原有系统配置规则，不自动读取启动器的 `portable.flag` 或旁边的 `config.toml`。与便携模式共用数据时，创建含以下内容的配置并显式传入 `--config`：

```toml
data_dir = "userdata/data"
cache_dir = "userdata/cache"
log_dir = "userdata/logs"
```

本标准包支持基础查询、编辑与导出工具；`mcp` 和截图功能需源码安装对应 extras，参见 P6 使用指南。冻结程序的隔离工具子进程由包内 `WorkbenchCLI.exe` 执行，无需系统 Python。

## 构建与检查

在 Windows x64 安装 uv、Node.js 22+，于仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows_portable.ps1
```

脚本同步锁定依赖，执行核心检查、前端构建、PyInstaller 文件夹打包及冻结程序冒烟验证，然后生成 `dist/DesignWorkbench-版本-windows-x64.zip` 与 SHA-256 文件。`-SkipChecks` 仅省略开发检查，仍执行构建和包验证。`packaging` 依赖组固定打包工具版本。

冒烟测试在含中文和空格的临时路径复制整包，清除开发环境路径，使用冻结 CLI 验证 HTTP 前端、创建/编辑/重开项目、蓝图导出与隔离工具子进程。官方素材仍需独立验证，不从开发机器混入分发包。发布工作流另检查 ZIP 解压后的同一流程。

包内 `LICENSE.txt` 是本项目许可，`_internal/licenses/python/` 保存 Python 运行时许可，依赖的 dist-info 包含可获得的许可文件。正式对外发布时应保留这些文件。未签名的 EXE 在部分机器上可能触发 Windows 提示；代码签名和自动更新尚未实现。

## 本地验收记录

2026-10-12，在 Windows 11 x64 / Python 3.12.13 / PyInstaller 6.16.0 上执行：

| 检查 | 结果 |
| --- | --- |
| Ruff、格式、strict mypy、前端 TypeScript/Prettier 与构建 | 通过 |
| 核心 pytest（排除需要真实资源/浏览器的标记） | 79 通过；1 项原有 SQLite 文件替换测试因 Windows 锁机制跳过 |
| 启动器服务就绪后打开浏览器、正常停止、重复实例锁、端口回退 | 5 项启动器相关测试通过 |
| 冻结 GUI 的首次启动窗口与正常关闭 | 实际可执行文件验证通过 |
| 官方素材 | 实际下载 1.20.1 客户端与中文语言文件；冻结 CLI 在独立缓存导入 966 张贴图通过 |
| 迁移后的冻结程序 | 中文/空格路径、无开发环境 PATH 下，网页、编辑、持久化重开、蓝图导出与隔离工具进程通过 |

开发机上的验证不能替代所有 Windows 设备验收；Windows 10 和干净虚拟机尚未独立验证。GitHub 工作流已加入仓库，远程运行结果需推送后确认。
