# 开发与版本管理

本仓库独立于 ai-mod。工程规范见 [ENGINEERING](docs/ENGINEERING.md)，阶段范围见 [ROADMAP](docs/ROADMAP.md)，当前支持范围见 [RESOURCES_AND_LIMITS](docs/RESOURCES_AND_LIMITS.md)。

## 分支、提交和标签

- `main` 保存已验收的项目状态；开发使用 `feat/<功能>`、`fix/<问题>` 或 `docs/<主题>` 分支，通过 Pull Request 合并。
- 一个提交解决一个可说明的问题，提交信息写清行为或结果。不要把源码、资源下载、项目数据和运行日志混入同一提交。
- 发布使用带说明的版本标签 `vMAJOR.MINOR.PATCH`。`v0.1.0` 是 P1–P5 工作台交付点，后续 AI 阶段有独立验收；不移动已有交付标签。
- 推送前检查 `git status`、`git diff` 与暂存内容。避免对共享 `main` 强制推送；已提交问题通常通过新修复提交处理。

这些是协作约定，目前未配置 GitHub 分支保护。独立开发时也应保留可审查的提交与验收记录。

## 本地检查

Python 3.12、uv、Node.js 22+：

```powershell
uv sync --locked --extra gui
npm.cmd ci --prefix frontend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -m "not e2e and not resources" -q
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
uv build
uv run python scripts/install_smoke.py
```

Linux 使用 `npm`。前端构建产物位于 `src/design_workbench/static/`，随 Python 包交付；修改前端后同步提交构建结果。依赖变更同步更新 `uv.lock` 或 `frontend/package-lock.json`。

实际资源/浏览器测试需先配置官方素材和 Playwright。参见 [快速开始](docs/QUICKSTART.md)；数据或格式变更须同时检查导入、编辑、预览及导出。CI 在 push/PR 时执行 Windows/Linux 核心与安装检查，以及 Linux 官方资源/浏览器测试。

## 不进入 Git 的内容

用户场景、第三方建筑、游戏客户端、模型与贴图、虚拟环境、依赖安装目录、导出、日志和验收临时产物由 `.gitignore` 排除。`.env`、`.env.*` 和 `config.local.toml` 是本机配置；可分享的无凭据示例另行核对。

不要使用 `git add -f` 上传上述文件。游戏素材在用户机器按资源清单导入，公开仓库只提供获取/校验工具。新增小型测试夹具须明确来源、分发条件和版本。

## 拉取与恢复交付版本

```powershell
git fetch origin --tags
git switch main
git pull --ff-only
```

需要单独查看初始交付时，另建工作树：

```powershell
git worktree add --detach ../Design_workbench-v0.1.0 v0.1.0
```

重新建立该目录的 Python 环境；项目数据和资源仍独立管理。Git 标签恢复代码，不会恢复游戏世界、`.dwbench` 用户项目或其他被忽略的数据。
