# E1 第一人称精修验收

验收日期：2026-10-10。状态：E1.1–E1.5 已完成。E2、P6–P8 仍未开始；交付点 A/B/C 的定义不变。行为规范见 [扩展计划](PLANNED_EXTENSIONS.md)，使用入口见 [快速开始](QUICKSTART.md)。

## 可运行产物与操作

前端源码和随 Python wheel 交付的静态页面已同步。启动服务后刷新页面即可使用：

```powershell
.\.venv\Scripts\design-workbench.exe serve --config config.example.toml
```

打开 `http://127.0.0.1:8765`，选择建筑或生成木屋，点击工具栏“第一人称”或在画布上按 G。建筑画布铺满窗口，普通顶栏、工具栏和两侧面板收起；底部显示当前材料。

| 操作 | 行为 |
| --- | --- |
| 鼠标、WASD | 转动视线、按水平朝向移动；垂直抬头也可水平移动 |
| Space / Shift / Ctrl | 上升 / 下降 / 加速；普通速度 8 格/秒，加速 16 格/秒，帧时间上限 50ms |
| 左键 / 右键 | 删除已有格 / 在命中面外侧的空格放置当前材料；每次点击一笔事务 |
| Alt+左键 | 首次选择一格，之后扩展矩形选区；Shift 不扩选 |
| 命中距离 | 默认 5 格；Esc 菜单可配置有限正数，包含地面射线的距离限制；只存浏览器设置 |
| 第一次 Esc | 释放指针并打开浮动菜单，保留第一人称位置与未提交预演；切换“方块材料”或“设计工具”，使用材料属性、剖切、分组和对比 |
| 再次 Esc | 取消预演；点击画布或“继续编辑”重新锁定并收起菜单，恢复锁定的点击不编辑 |
| G / 退出第一人称 | 恢复进入前的相机位置、目标、旋转、视野和面板布局；输入框、下拉框和文本区里的 G 正常输入 |

进入时保留轨道相机的 X/Z 与水平朝向，初始脚下高度取最低占用层顶面，眼睛在其上 1.62 格；空场景以 Y=0 为脚下平面。后续可以自由飞行。行走相机只存在于当前页面；重开项目为轨道相机，方块和历史保留。

## 逐项证据

新增 `tests/e2e/test_walk.py`，通过 Playwright 操作真实桌面 Chrome，服务端使用独立临时项目和已导入的官方 1.20.1 素材。方块核对读取 HTTP 权威场景，不从前端假定编辑成功。小网格测试有时通过相机参数设置固定观察位置，实际飞行、指针锁定、旋转和点击仍使用浏览器输入。

| 任务 | 验证与结果 |
| --- | --- |
| E1.1 | 模式开关、准星、指针锁定、G 和按钮退出；Esc 释放时预演保留、再次按下取消；位置、目标、四元数和 FOV 恢复 |
| E1.2 | 从室外 Z=14 按 W 穿过木屋 Z=10 的墙到室内；8/16 格速度、升降、真实鼠标转向和垂直抬头通过；800ms 主线程暂停不会飞出，blur 清除按键 |
| E1.3 | 449 格木屋内右键放置一格、左键删除另一格，r1→r2→r3；请求含不同 request_id 和准确 expected_revision；实际方块坐标、状态与分组可回读 |
| E1.4 | 行走中 Ctrl+Z / Ctrl+Shift+Z 撤销重做；Alt 扩选、Shift 下降、预演、分组和修改前后对比并存；另一写入者先提交后，旧修订点击返回 409 且不覆盖新场景；重开后编辑保留，逐步撤销回到进入前场景，重做恢复 |
| E1.5 | 四条第一人称浏览器流程无 pageerror；1440×1000 与 640×500 画布均铺满窗口；材料菜单调整云杉楼梯朝东后回读实际放置状态；退出恢复控件位置、面板设置与相机；矮窗口滚动后退出按钮仍可点；截图验证室内画面、材料与工具菜单 |

附加拾取验证覆盖：默认 5 格的精确边界、修改为 12 格、无效距离拒绝、浏览器保存其他距离后重开、轨道拾取不受行走射线距离污染、Y 剖切隐藏层不能命中、负 Y 方块、Y=0 地面起笔、按住鼠标只编辑一次，以及从实体方块内部穿出。

## 验证命令与结果

Windows：Python 3.12.7、Node.js 24.14.0、本机 Chrome 154.0.8037.98、Minecraft Java 1.20.1 / DataVersion 3465。浏览器测试为 headless 的实际 Chrome，不是模拟浏览器或游戏客户端。

```powershell
npm.cmd run check --prefix frontend
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
$env:DW_BROWSER_CHANNEL = 'chrome'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=artifacts/e1/pytest-final-windows.xml
.\.bootstrap\Scripts\uv.exe build
.\.venv\Scripts\python.exe scripts/install_smoke.py --report artifacts/e1/install-smoke-final-windows.json
```

最终全量 Windows 回归：69 项通过，1 项因 Windows 对打开的 SQLite 文件的替换锁机制跳过。Ruff、strict mypy、前端 TypeScript/Prettier/build、wheel 构建和干净环境安装通过。安装冒烟核对了包内前端、材料目录、CLI 创建/编辑/导出；wheel 中的 HTML、JS 和 CSS 与当前工作区逐字节一致。最终结果及源码/静态文件哈希见 `final-verification-manifest.json`。

最终回归包含四条第一人称浏览器流程和普通工作台流程，材料库、工具菜单及矮窗口截图已人工核对。运行中的本地服务返回最终构建文件；只读模式切换检查前后 14 个现有项目保持一致，无编辑请求或页面脚本错误。`immersive-manifest.json` 与 `verification-manifest.json` 分别保留沉浸界面调整阶段和最初 E1 基线的验证记录。

材料图标使用透明 PNG 背景，材料库和第一人称浮层均直接使用面板底色。特殊方块渲染与沉浸材料菜单回归通过；当前服务中 28 张材料缩略图的四角 alpha 均为 0，模型本体仍有可见像素，包含玻璃、染色玻璃、树叶与楼梯。截图核对未见白底，记录在 `pytest-thumbnail-background.xml`、`thumbnail-background-report.json` 和 `transparent-material-menu.png`。

Linux（WSL Ubuntu 22.04）执行 `bash scripts/linux_check.sh`：54 项核心测试、strict mypy、Ruff、wheel 构建和源码目录外干净安装通过。日志在 `artifacts/e1/linux-check.log`，安装报告在 `artifacts/install-smoke-linux.json`；本轮未在 Linux 重跑浏览器，E1 的浏览器证据来自上述 Windows Chrome。

### GitHub Actions 指针锁定回归（2026-10-10）

后续远程运行 `38013163565`、`38028681886`、`38031020887` 的失败集中在四条第一人称浏览器测试；最新运行的 Windows/Linux 代码检查、非浏览器测试、构建和安装验证均通过，浏览器任务为 4 项失败、18 项通过，包含新增的 AI 任务流程。

在 WSL Ubuntu 22.04 对照同版本 Playwright Chromium 153.0.8010.12：默认 headless shell 锁定指针后产生额外的指针回中事件，鼠标位移出现 `+700,+400` 后紧接 `-700,-400`，转向相互抵消；切换 `channel="chromium"` 使用完整 Chromium 后，位移正常，原有四条测试全部通过。Windows Chrome 154.0.8037.98 的四条测试也通过。第一人称实现保持不变。

切换通道后，本地 Linux 全部浏览器与资源回归为 22 项通过、73 项未选中，包含第一人称、AI 任务控制和真实截图流程；报告为 `artifacts/ci-diagnosis/browser-linux-chromium.xml`。

远程重跑 `38032598839` 为 21 项通过、1 项失败：木屋测试固定按 W 一秒，但 CI 较慢的绘制帧结合每帧 50ms 位移上限，只前进 2.8 格。测试改为先等待指针锁定回调完成、画布获得焦点，再在有限超时内等待相机实际穿过墙面。室内坐标范围、鼠标转向、普通/加速速度、单帧暂停位移上限和后续编辑历史断言均保留。

后续本地复核还发现冲突验收与每 1.5 秒的外部修订自动刷新存在竞争：浏览器可能先读到新修订，随后编辑合法成功。冲突测试改为在浏览器已构造编辑请求后，通过独立 HTTP 客户端提交真实的另一笔事务，再放行原请求，稳定验证旧修订返回 409；请求与服务端响应均不伪造。

CI 的 `browser` 任务设置 `DW_BROWSER_CHANNEL=chromium`，所有浏览器流程及截图子进程使用 Playwright 随附的完整 Chromium。`playwright install --with-deps chromium` 已安装所需浏览器，不依赖本机桌面 Chrome。手动进行 Linux 第一人称验收时同样指定该通道：

```bash
DW_BROWSER_CHANNEL=chromium .venv/bin/python -m pytest -m 'e2e or resources'
```

诊断日志、指针事件对照和本地验收报告保留在忽略目录 `artifacts/ci-diagnosis/`。

结果位于忽略目录 `artifacts/e1/`：

- `pytest-final-windows.xml`、`final-verification-manifest.json`：最终全量测试结果、源码/静态文件哈希和 wheel 内容核对。
- `cabin-report.json`：室内坐标、单次编辑修订、冲突、相机恢复与重开/撤销证据。
- `motion-report.json`：普通与加速位移、暂停后的位移、垂直朝向和失焦处理。
- `pick-report.json`：距离、剖切、地面、负 Y 与按住点击的结果。
- `cabin-interior.png`、`narrow-controls.png`：真实浏览器截图。
- `install-smoke-final-windows.json`：最终 wheel 在源码目录外的干净安装结果。
- `pytest-windows.xml`、`verification-manifest.json`：最初 E1 基线的测试和打包核对记录。
- `pytest-immersive.xml`、`immersive-manifest.json`：沉浸界面更新的浏览器结果、源码/静态文件哈希与运行服务核对。
- `immersive-interior.png`、`immersive-material-menu.png`、`immersive-tools-menu.png`、`immersive-narrow-menu.png`：沉浸画布、材料/工具菜单和矮窗口截图。
- `thumbnail-background-report.json`、`transparent-material-menu.png`：透明缩略图的像素检查与真实界面截图。

这些测试针对小场景和确定行为，不将测得的单次飞行或编辑时间推广为所有建筑与机器的性能承诺。

## 修复过的问题与能力边界

测试发现指针锁定的状态可能早于 `pointerlockchange` 回调可见。获得锁定时不再清除已经按下的移动键，防止立即按 W 后移动中断；解除锁定与失焦仍清除按键。浏览器自动化在锁定后点击原位，避免测试脚本移动鼠标导致目标改变。

仍沿用现有可见网格拾取：没有可绘网格的特殊内容不能由准星命中，其警告保留。构建分块期间暂停拾取，受保护格由现有应用服务拒绝；比较旧画面时禁止写入。指针锁定失败显示可重试的提示，场景不受影响。

本次没有碰撞、重力、惯性、生存模式、玩家实体、物品栏、连放连挖或触控行走。每次点击是一笔历史，放置与删除两次操作需要两次撤销。尚无 P6 产品截图接口，不能从此模式隐式取得截图相机。E2 可继续基于 P5 的场景事务和官方资源开展；P6–P8 的依赖和未开始状态不变。
