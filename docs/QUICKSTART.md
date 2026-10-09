# 快速开始

当前交付版本 0.1.0，P1–P5，Minecraft Java 1.20.1。

## 当前机器

Python 环境和官方素材已经在项目中准备好：

```powershell
cd D:\Study\program\Design_workbench
.\.venv\Scripts\design-workbench.exe serve --config config.example.toml
```

访问 <http://127.0.0.1:8765>。如果该服务已运行，直接打开页面；无需启动第二个相同端口的服务。Ctrl+C 关闭服务。

项目数据在 `.local/data/projects/*.dwbench`，资源在 `.local/cache/resources/`，日志在 `.local/logs/`。`.dwbench` 是 SQLite 项目文件，`.litematic` 是与外部工具交换的压缩 NBT 蓝图。

## GUI 操作

1. 点击“新建”并输入名称，或选择已有项目。“导入蓝图”读入版本一致的 `.litematic`。
2. 左侧查询材料，点击卡片并选择属性，例如楼梯的 facing 和 half。
3. 可用“生成简单木屋”起稿。也可在右侧设置整数选区，再选择填充、挤出等工具。
4. “预览修改”显示绿色新增/替换、红色删除；“应用修改”提交，所有成功修改自动保存。“取消预览”不改项目。
5. 点击方块选择，Shift+点击扩展；分组树可选整组。拖动旋转，右键平移，滚轮缩放；视角按钮和最高显示层控制观察。
6. 撤销/重做产生新修订。“保存 / 重读”重新读取已保存结果。“上次修改前”比较本次浏览器会话中的最近快照；刷新页面不保留这张比较快照，数据库历史仍保留。
7. “检查部件与连接”给出建议；先预览建议再应用。“导出蓝图”下载当前修订。

导入会替换当前项目场景，作为可撤销事务记录。建议为新资产先建项目。特殊实体关联格只能查看和保留，相关编辑返回明确限制。

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
