# 渲染优化实验记录

开始记录：2026-10-09；持续实验至 2026-10-10（Asia/Shanghai）。本记录用于持续保存每次尝试、失败、回退和测量条件。目标是 **完整显示至少 100,000 个非空气方块，在正常分辨率下连续旋转、近景查看、剖切和编辑时保持流畅，并保持材质、状态、透明度和拾取正确**。

当前最终实现提交 `100afea81abb93fb40414a0680556c2030b27098`，前端 `index-CeI4Gm9A.js` SHA-256 `bdf7f0b2a29355bbf74f662a37a357e72dd57fbaaaaac68854efa532e3b34257`。完整100k在本机RTX5060Ti/Chrome154、922×751、DPR1/2的6秒×3稳定旋转/近景/剖切和连续层输入P95均16.8ms，源状态/实际几何/真实点选通过；draw calls从原版29,596降到243。73n的8组完整验收是历史包的独立证据，当前CeI4最终回归的范围和原始路径见后文。

保留局限：最终100k初次导入有54ms任务，综合连续交互存在孤立50.1ms帧；strict像素gate未通过，用户别墅是保留原bytes的状态投影、188个NBT未进入渲染/新导出；历史D18候选百万压力探索全景P95为33.4ms，CeI4没有重测百万。稳定帧目标达成不等于所有操作即时或任意硬件均60FPS。

## 验收口径

- 固定本机硬件、Chrome、官方 Java 1.20.1 资源、1440×1000 视口；DPR 1 为主，DPR 2 补测。浏览器必须记录 WebGL 实际 renderer，不把软件栅格器与硬件结果混在一起。
- 全部方块、完整模型和贴图正常加载。不降低方块数量、不隐藏远处内容、不把复杂模型替换成简单方块，也不靠降低分辨率达到目标。正常视锥与不可见内表面剔除允许使用。
- 连续 rAF 帧间隔以 P50/P95/P99、最大值及 >33.4/50/100 ms 次数评估；单独记录 renderer.render 的 CPU 提交耗时。60 Hz 流畅目标 P95 接近 16.7 ms，计时量化允许 20 ms；持续出现 >50 ms 帧或主线程任务必须说明。禁止将 gl.finish() 同步绘制耗时当作 FPS。
- 记录首次导入与显示、无变化刷新、100/1,000 格编辑、预演取消、撤销、剖切与恢复，以及快速反复剖切的耗时和内存趋势。
- 逐格核对浏览器数据与源蓝图的所有坐标和完整方块状态；通过真实画布点击检查合并后的方块身份；检查截图中的透明内容、薄片、楼梯和植被。逐格数据一致只是数据层证据，不能单独证明画面正确。
- 原始结果与截图保存在 `artifacts/performance/<时间>-<实验名>/`。本文件与基准脚本纳入版本控制；大型蓝图、数据库、Chrome 原始数据和截图沿用项目忽略规则。

## 可重复基准

基准脚本：`scripts/benchmark_rendering.py`。自动选择独立端口，新建隔离的数据目录，复制本次静态资源后启动测试服务，不修改用户的现有项目，也不占用主服务 8765。

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label baseline --quick --static-dir artifacts/performance/baseline-static/ui
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label optimized --dpr 1 2 --asset .local/imports/azalea-church.litematic
```

`--quick` 每阶段 2 秒、1 次测量、4 次重复剖切，用于诊断；完整默认每阶段 6 秒、3 次测量、12 次重复剖切。预热单独保留，不算进稳定阶段。支持重复 `--asset` 加入真实建筑，也支持指定 `--seconds`、`--repeats` 和 `--output`。`--url` 只能指向明确隔离的服务，因为脚本会创建临时项目并进行编辑。真实 `.dwbench` 渲染夹具通过 `--project` 原样 SQLite backup 到临时工作区，逐格与源数据库核对；仅临时项目的 X 方向边界增加 32 格用于编辑测试，不改源数据与方块。

后续测试固定实际画布 CSS 922×751（`--canvas-width/--canvas-height` 可调整），匹配当前正常 1440×1000 工作台布局；DPR 2 画布像素为 1844×1502。早期 UI 并发加入逐层播放，导致基线 922×797 和 round1 922×751；这两次是探索性诊断，严格比较使用重新测试的 `baseline-fixed`。

大型公开建筑的包围盒含大量空气。只有隔离测试服务把 `max_selection_volume` 调至 12,000,000；日常项目配置与兼容范围不变。`--max-blocks` 默认仍 250,000，百万格压力时显式指定 1,500,000，不能把提高预算本身称为性能优化。

固定夹具 `mixed-town-100000-v1` 包含 100,000 个非空气格：多个空心建筑的楼板、外墙、彩色玻璃与玻璃板、不同朝向/半层/转角的楼梯、不同连接状态的栅栏、活板门、不同半层的台阶及树叶。使用确定性排列和 mtime=0 的 gzip，记录文件 SHA-256，避免仅用实心立方体低估真实建筑的复杂度。

真实建筑包含杜鹃教堂（36,094 格）、用户链接作品公开预览别墅（46,281 格）、同网站象牙城堡连续 Y≥51 上部裁片（105,102 格、617 状态）及完整象牙城堡（1,156,099 格，后续压力）。来源、哈希和裁片算法记录在 `artifacts/performance/asset-manifest.json` 与 `scripts/prepare_performance_assets.py`。用户别墅原件为 Litematic v5 / DataVersion 3578，不属于产品 v6 / 3465 导入范围；测试明确采用无状态替代的 1.20.1 纯渲染投影项目，不能声称已兼容导入。告示牌文字不能从该投影自动恢复，单独记为限制。城堡裁片原生 v6 / 3465，可正规导入；包围盒 6,020,070 格，所需预算单独说明。不能用教堂或合成夹具的结果替代指定作品的实测。

## 观察开销与证据边界

外部 runner 通过包装 renderer.render、Viewer.update、Viewer.setLayer 测量 CPU 耗时，不修改产品源码。每次调用额外进行两次 performance.now 及数组记录；结果保留原始样本。rAF 轨迹每帧一次更新相机并通过产品原有 requestDraw 绘制，保留浏览器异步流水线。

PerformanceObserver 采集 >50 ms 的主线程任务，只记录时间范围，不能自动推断具体原因。renderer.info.memory 是几何/纹理对象数量，不是显存字节；另记录 CPU 几何 attribute 字节、JS heap 与 CDP heap。内存循环结束后才主动 GC，GC 不计入旋转帧测量。截图与逐格校验放在稳定帧测量区间之外。

## 实验 00：原实现基线

- 原代码 Git SHA、未提交变更、前端源码/静态包哈希、资源 manifest、蓝图哈希与场景修订均由结果 JSON 自动记录。
- 已在开始修改前将原静态包保存到 `artifacts/performance/baseline-static/ui`。后续构建不会覆盖这份基线。
- 原始探索性结果：`artifacts/performance/20261009-231056-baseline/results.json`，静态包保持原版，后端为测试启动时的工作区源码。后端已存在并发改动；这些结果主要用于比较渲染，不代表后端原版基线。
- 固定画布重测：`artifacts/performance/20261009-232816-baseline-fixed/results.json`。Chrome 154.0.8037.98，Windows 11，ANGLE/Direct3D11，NVIDIA RTX 5060 Ti，DPR 1，画布 922×751，quick 单次旋转 2 秒。Git SHA 为 `193f8f1d49a15af4d90cba2d1d8a24588fc804b1`，具体 dirty 状态与所有源码、静态包哈希在 JSON。

| 固定画布原版 | 方块数 | draw calls | rAF P50 / P95 | CPU 提交 P50 / P95 |
| --- | ---: | ---: | ---: | ---: |
| mixed-town-v1 | 100,000 | 29,596 | 166.7 / 183.4 ms | 175.05 / 177.09 ms |
| 杜鹃教堂 | 36,094 | 7,811 | 16.7 / 33.4 ms | 21.3 / 23.69 ms |

100,000 格原版仅约 5–6 FPS，连续旋转每次提交超过 100 ms。两场景所有坐标与完整方块状态一致，真实 UI 点击采样全部通过。初次环境故障：Windows 未安装 tzdata，时间戳改用显式 UTC+8，未安装额外依赖；记录日期遵循客户端 Asia/Shanghai。

## 实验 01：不透明批次合并、增量占用索引与局部剖切

假设：教堂主要瓶颈是按状态和可见面掩码分组产生的小 InstancedMesh，合并每个分块的不透明材质可降低调用；占用索引与剖切避免全部重建。改动由主代理实施，涉及 Viewer 与分块几何构建。半透明仍按方块保留独立对象，以维持原来的对象排序。

原始结果：`artifacts/performance/20261009-231246-round1/results.json`，quick，DPR 1，画布 922×751；原版首次探索基线画布不同，所以保留 CPU/draw calls 的定位价值，不把两者作为严格 GPU 填充率比较。

| 场景 | draw calls | rAF P95 | CPU 提交 P95 | 剖切 / 恢复 UI 总耗时 |
| --- | ---: | ---: | ---: | ---: |
| 100,000 格混合城镇 | 21,332 | 166.7 ms | 158.94 ms | 217.1 / 191.2 ms |
| 36,094 格教堂 | 329 | 16.8 ms | 4.1 ms | 49.8 / 50.6 ms |

结论：教堂达到约 60 Hz，但这轮未完成 100,000 格目标。混合城镇含 10,578 个透明格，逐格透明 DoubleSide 的双遍绘制仍占约两万次调用。必须继续降低透明调用且保持排序。数据层逐格一致，截图显示建筑完整，6 类真实画布点选全部通过；无 pageerror。单纯扩大不透明合并不足，保留本轮优化并推进透明批次。

**后续核查修正：表中 round1 剖切/恢复时间无效。** 并发引入的 LayerPlayer 在 input 回调先 stop()，stop 调用 sync 把滑条数值恢复为当前层，再 seek 读取恢复后的值，实际未切到请求的层。帧测量依然有效，但剖切截图/循环不是本轮要求的操作。此问题由测量揭示，修正产品读取顺序后重测；基准增加每次实际 layer 与请求相等、每轮 5 次 setLayer 被执行的断言。

代价：CPU 侧几何 attribute 数据从共享实例几何提升为大块合并数据，混合城镇约 131 MB；这不是 renderer.info.memory 的显存估算。后续必须用反复剖切/编辑验证释放和缓存边界。不能只报告对象数下降而忽略字节数上升。

## 实验 02：透明几何合并与动态索引排序

主代理把透明几何集中为共享批次，按相机深度重排每格的索引，并按每格背面→正面顺序保持双面透明合成。目标是去除单格 mesh 的绘制与对象开销，不能仅合并整个分块而丢失格间排序。已保存本轮静态快照 `artifacts/performance/round2-static/ui`。原始 quick 结果 `artifacts/performance/20261009-234822-round2/results.json`，画布 922×751，DPR 1。

| 场景 | 非空气格 | draw calls | rAF P95 | CPU 提交 P95 |
| --- | ---: | ---: | ---: | ---: |
| mixed-town-v1 | 100,000 | 177 | 16.8 ms | 6.9 ms |
| 教堂 | 36,094 | 66 | 16.8 ms | 0.7 ms |
| 城堡 Y≥51 裁片 | 105,102 | 190 | 16.8 ms | 1.6 ms |
| 用户链接别墅渲染投影 | 46,281 | 48 | 16.8 ms | 0.4 ms |

旋转阶段全部样本没有 >33.4 ms 帧。所有场景逐格数据一致；尚不能据此宣布完成。剖切受到上述 LayerPlayer 故障影响，原报告相关耗时与内存循环无效，必须修复后完整重测。castle/别墅各一条点选采样落到邻近高处方块，发现 runner 的近似“顶视图”存在 0.001 水平倾斜，加上采样拿到底面时造成遮挡误判；改为选最高水平面、每个探针相机垂直置于正上方、真实点击仍与源方块坐标核对，不用产品拾取结果作为期望值。observer 更新记录原来捕获旧数组而测试清空时替换数组，导致 updateCalls 错失；改为 length=0 保持引用，并按每次 UI 操作保存长任务范围。

## 实验 03：修正逐层输入并核验真实剖切

LayerPlayer 先捕获滑条/数字框输入再停止播放，避免停止时 sync 覆盖输入。透明字牌纳入同一全局排序，保留字牌/玻璃的深度关系；透明拾取加入球体粗筛。原始结果 `artifacts/performance/20261009-235451-round3/results.json`，quick，DPR 1，画布 922×751。每轮快速剖切已确认真正调用 setLayer 5 次、最终显示最高层。全部场景点选样本通过，截图确证屋顶切除、内部楼板显示。

| 场景 | 真正剖切 / 恢复 UI 总耗时 | 5 次急切单轮总耗时 | 最大主线程长任务 |
| --- | ---: | ---: | ---: |
| 100,000 格城镇 | 132.0 / 270.8 ms | 682.5–797.8 ms | 647 ms |
| 教堂 | 98.0 / 166.6 ms | 256.8–334.8 ms | 267 ms |
| 城堡 105,102 格 | 64.4 / 64.9 ms | 328.4–360.5 ms | 310 ms |
| 用户别墅投影 | 82.8 / 97.9 ms | 175.5–211.6 ms | 167 ms |

100,000 格首次 Viewer.update 为 409.7 ms，同任务约 410 ms，随后首次上传约 178 ms。纯旋转仍 rAF P95 16.8 ms，但剖切明显卡顿，**目标尚未完成**。本轮 4 次循环几何 attribute 字节保持稳定，JS heap 多次分配后需 GC；不能把短循环解释为长期无泄漏。

测量修正：透明排序从 renderer.render 之前执行，单独包装 renderer.render 会漏掉排序成本。后续追加 Viewer.drawNow 总 CPU 时间，保留 submission 数值但不混用。新增跨多帧的真实 slider input 连续往返，记录 rAF 与每次请求/实际层一致；快速 5 次输入测试专门验证取消旧任务与合并最新目标。

## 实验 04：异步分块重建、输入合并与独立缩略图

主代理采用约 6 ms 的分块重建时间预算，在任务间让浏览器处理输入与绘制，update/setLayer 共享 pendingBuilds，刷新等待 whenReady；快速输入应只构建最新层，取消陈旧目标。缩略图改用独立 renderer，按资源/状态缓存，避免主画布尺寸与缓冲干扰；模型/缩略图缓存有界。基准 ready 需确认 pendingBuilds 清空，既测输入响应也测最终完整画面。

原始 quick 结果 `artifacts/performance/20261009-235817-round4/results.json`。四场景真正往返 slider sweep 全部 rAF P95 16.8 ms；城镇最长帧 33.3 ms，其余小于 18 ms。所有 slider 请求与实际层相等，四场景 UI 操作/连续剖切无 >50 ms 长任务，真实点选、全量方块状态核对通过。

| 场景 | drawNow 总 CPU P95（旋转） | 真剖切 / 恢复 UI 总耗时 | 5 次急切完成总耗时 |
| --- | ---: | ---: | ---: |
| 100,000 格城镇 | 10.50 ms | 215.9 / 480.4 ms | 740–813 ms |
| 教堂 | 0.70 ms | 164.2 / 213.9 ms | 296–315 ms |
| 城堡 105,102 格 | 2.00 ms | 82.4 / 97.7 ms | 580–661 ms |
| 用户别墅投影 | 0.50 ms | 149.7 / 148.6 ms | 226–265 ms |

结论：异步重建消除了阻塞卡顿，代价是构建分散到多个帧，总完成时间未变快。急切最后回到原最高层，本应沿用已有网格，但仍重建，说明调度只合并了请求、未避免无效构建；继续优化有效网格版本与层键。别墅存在 4 格 chest 的已有 special 渲染限制，方块数据保留，警告显式显示。100,000 格城镇与城堡均无 special/missing 警告。

## 实验 05：根据实际网格版本跳过无变化重建

主代理增加分块生成版本、邻居版本与有效剖切层的网格键；急切回到已有最高层且状态未变时，直接复用网格，避免上传与透明全局重合。快照和结果 `artifacts/performance/20261010-000320-round5/`，本轮 quick 各阶段延长至 4 秒。新增实际几何覆盖核验，检查每一个支持且具有外露面的格在 scene 中确有 geometry owner；独立于数据 Map 的全量状态验证，避免数据存在却画面漏格。分别对全景、剖切、最后恢复检查。

100,000 格城镇急切完成降至 42–49 ms，较 round4 的 740–813 ms 明显改善；真实新层仍需异步构建，剖切/恢复总耗时约 214/466 ms，无主线程 >50 ms 任务。4 秒真实 slider 连续往返 P95 16.8 ms，最长 33.3 ms。全景 100,000 外露格与所有 geometry owner 对应，Y=19 时 68,665 个外露格全部对应，恢复重新得到 100,000；教堂全景 34,017 个外露格、剖切 25,258 个均对应。四个场景纯旋转 P95 16.8 ms，无 >33.4 ms 样本；完整多重复/DPR2验收待进行。

## 后端增量投影、局部存储与编辑规划实验

后端代理对原提交 `193f8f1` 与当前实现独立比较，避免本文件前端快照基准的并发后端改动混淆。可复现命令为 `scripts/benchmark_render_cache.py`；原始结果位于 `artifacts/performance/backend/results.json`，资源 SHA-256 `f9cc524673663d369e50d5af01291b48cd4d34ce166bca59c46cc082495ef13d`。

| 场景 | 无变化 load+render 中位：原版→缓存 | 摘要中位：原版→缓存 |
| --- | ---: | ---: |
| 教堂 36,094 | 347.09 → 0.18 ms | 100.36 → 0.31 ms |
| 别墅 46,281 | 444.87 → 0.19 ms | 152.18 → 0.12 ms |
| 城堡裁片 105,102 | 1007.57 → 0.29 ms | 370.46 → 0.17 ms |
| 混合城镇 100,000 | 992.37 → 0.26 ms | 347.42 → 0.13 ms |

采用由 SQLite 分块版本/资源哈希驱动的缓存，仅加载/组装变化分块及上下文邻居；全量 packet 与增量结果逐项等价验证。这个数字是后端函数级耗时，不包含 HTTP、前端上传或首次缓存。首次完整缓存仍需全量扫描，不能把热缓存数字描述为首次加载性能。

缓存保留的packet嵌套对象当前由直接Python调用者借用共享引用，调用者不得修改；HTTP只读序列化不改变缓存内容。投影和载入由全局RLock保护，超大冷请求会在锁内阻塞其他项目读取。500k格总预算的LRU淘汰限制见百万压力，当前优化没有解决超大场景跨项目并发或为直接Python调用自动复制返回值。

`chunk-write-results.json` 针对 105,102 格/188 分块场景，只测内存 SQLite 写入，不含载入/规划/耐久提交。原版扫描全部格重编码所有块，优化仅写触及块：1 块中位 34.99→0.23 ms，5 块 40.17→5.79 ms，压缩行逐字节相等。**全量 188 块中位反而 184.79→209.69 ms**，保留这个不利结果；改动收益属于局部编辑，不能声称全量写入更快。

`edit-plan-results.json` 只测 Editor.plan，采用局部差异跟踪避免每次复制/比较全场景。1 格中位 67.00→2.51 ms，100 格 67.59→3.33 ms，1,000 格 73.66→8.63 ms；最终 cells、delta、touched 完全相同，不包含数据库提交。HTTP编辑整体还受 SQLite读入、API与浏览器刷新影响，最终端到端结果单独验收。

## 实验 06：GPU 保留本地顶点的画面精度尝试

问题：实例化改为 CPU 世界坐标合并后，楼梯、植物的部分边缘出现亚像素/单像素差异。尝试额外保留 `localPosition` 与 `blockOffset`，复制材质 vertex shader 的变换，使用与原实例化相同的乘法顺序，目标是消除差异。每顶点额外 24 字节，内存收益不预设为正；视觉代理比较同相机像素、基准比较内存/帧。测试 `artifacts/performance/20261010-000547-round6/`，quick，DPR1：四场旋转 P95 16.8 ms，100,000 格 drawNow 总 CPU P95 11.70 ms。

| 场景 | 额外 attribute 前 | 尝试后 CPU 几何字节 | 增幅 |
| --- | ---: | ---: | ---: |
| 100,000 格混合城镇 | 160.65 MB | 232.32 MB | +71.67 MB / 44.6% |
| 教堂 | 51.00 MB | 78.78 MB | +27.78 MB |
| 城堡裁片 | 64.53 MB | 98.17 MB | +33.64 MB |
| 用户别墅投影 | 17.85 MB | 27.57 MB | +9.72 MB |

**决定回退**：18 张真实建筑的对比画面几乎没有像素收益，却显著增加内存与上传带宽。不保留该 shader/attribute；保留本轮代码哈希、原始结果和失败原因。透明原路径需要的精度机制与这次不透明尝试分别判断。

## 最终验收计划（实施前固定）

- 普通工作台画布 922×751，DPR1 与 DPR2；四场景全套每个旋转/近景阶段 6 秒、3 次重复，剖切后旋转 6 秒，连续 slider 往返 6 秒、12 轮急切取消；真实 UI 编辑100/1000格、撤销、全量状态与几何owner验证。每种 DPR 预计约 4–6 分钟，最终截图人工复核。
- 专注视图实际画布 1440×751，DPR2补测混合城镇与真实城堡裁片。测量条件独立记录，不能将较小画布的结果直接外推。
- 完整象牙城堡 `asset_ivory_castle_full_1156099.dwbench` 仅压力探索：1,156,099 格、701状态、125种材料，专用服务器 `--max-blocks 1500000`、空气体积预算12m，全部格正常加载，不能只加载105k裁片却称为百万格。压力结果与100k目标分开，异常或卡顿如实保留。
- 不将 longtask 全部消失当作“立即完成网格”，保留最终显示总延迟。正确性须同时证明数据全量、支持的外露格都有真实几何、切层后内部暴露完整、透明遮挡关系、真实拾取方块身份，以及已有格式/事务回归。

## 叶片改进前的候选完整基准：普通工作台

静态候选 `index-BPb3uqOY.js` SHA-256 `de9382cd84b605a3b74361070c565905b201be3f42b4ed9322590b7e3033f0b6`；CSS `index-CclQjmdj.css` SHA-256 `ce5c3c17d0e4441daf523a9ae4e229e1cf3edd6a2f7999e5d1b5f5ac3ce33753`。原始结果 `artifacts/performance/20261010-001315-final/results.json`，8 组场景×DPR，普通工作台实际画布922×751，DPR2像素1844×1502。各旋转与近景 **6秒×3次**，切层后旋转6秒、slider真实往返6秒、12轮急切5次输入，真实UI100/1000格修改与撤销。

这组数据保留用于过程比较；树叶实例化方案在之后采用，73n生命周期阶段另用 `final-leaves` 重新全测，不能将旧候选结果混作新静态包的结果。当前最终产品再采用实验09的CeI4透明复用，验收范围单独记录。

| 场景 | 格数 | draw calls | DPR1 各旋转/近景/剖切最差 P95 | DPR2 同口径 |
| --- | ---: | ---: | ---: | ---: |
| 混合城镇 | 100,000 | 177 | 16.9 ms | 16.8 ms |
| 杜鹃教堂 | 36,094 | 65–66 | 16.9 ms | 16.8 ms |
| 城堡连续上部裁片 | 105,102 | 190 | 16.9 ms | 16.8 ms |
| 用户别墅状态投影 | 46,281 | 48 | 16.8 ms | 16.8 ms |

全部旋转/近景样本无 >33.4ms 帧；真实连续剖切P95均16.8ms，100k DPR1最长33.2ms，其他场景小于18ms。8组全量坐标/完整状态、实际几何owner覆盖、真实点选全部通过；12轮急切前后几何对象、纹理对象及CPU几何字节保持一致。所有首次显示 longtask 记录为空。

唯一操作异常：100k DPR2的 **100格commit** 出现一次54ms主线程任务，UI整体完成579.6ms；该轮1000格commit566.2ms没有长任务。保留54ms，不宣称“绝无任何停顿”；追加带 rebuild/flushTransparency/drawNow 的5轮100格、3轮1000格连续编辑诊断确认原因。其余7组所有UI阶段无>50ms任务。

主基准早期100k DPR1可能与独立导出审计约10秒CPU工作重叠；旋转数值保留为原始证据，但会另跑同包相同参数补测，不能删掉存在干扰的样本。后续百万压力、专注宽视图和额外交互基准按串行排队，避免多浏览器/GPU争用。

首次导入/显示仍是较慢的一次性操作：100k城镇3.27秒（DPR1）/3.94秒（DPR2），城堡105k 5.72/5.85秒，其中含602万空气体积的正规蓝图读取；别墅直接打开渲染项目1.20/3.07秒。100/1000格修改到完整画面的总延迟约0.20–0.58秒，除上述54ms个例主线程保持响应；这些数字包含API/持久写入/刷新，不能与函数级缓存耗时混同。新剖切最终完成约0.10–0.52秒；急切回已有网格已避免完整重建。

## 额外交互与54ms个例诊断

`artifacts/performance/20261010-002534-interactions/results.json`，同候选BPb3包、普通工作台100,000格、DPR2。相机持续转动期间，通过实际GUI完成 stairs 搜索、下一页/上一页、oak_stairs 搜索、facing/half/shape三属性选择；5轮每轮100格楼梯填充和撤销，每轮比较修改前/当前画面；再做3轮1,000格填充/撤销。另3轮真实源面探针点击核对方块身份，包装 pick 计时。

- 持续相机测量1,129帧，P50/P95/P99=16.7/16.8/33.3ms，最长33.7ms；仅2帧超过33.4ms，无>50ms帧，无主线程长任务。drawNow总CPU P95=12.0ms。
- 24次真实拾取CPU P95=2.2ms、最长4.9ms，所有坐标符合预期。最后全量状态与geometry owner一致。
- 5轮100格修改总完成414–517ms，撤销360–444ms；3轮1,000格修改446–532ms，撤销364–509ms。before/current总完成约798–968ms，但相机帧继续流畅。完整几何重建尚有可见等待，不能描述为立即切换。
- 没有复现54ms长任务。每个patch都重做全局透明集合，flushTransparency实测12.5–26.8ms；最长单分块rebuild11.6ms、drawNow20.2ms。这个额外成本存在，但当前证据不支持将孤立54ms任务直接归因于某一个步骤。未来可优化透明集合未变化时复用，当前不凭推测修改并掩盖原样本。

## 实验 07：树叶恢复小批次实例化（B1）

视觉代理发现树叶恢复原实例化路径后像素差异减少，其他不透明/透明批次保留。这同时恢复了局部顶点变换与对象绘制顺序，证据只能说明差异与树叶合批有关，尚不能区分浮点舍入和共面绘制顺序；实验06仅恢复局部顶点没有明显收益，绘制顺序因此值得后续单独核查，但不是已证实的原因。

独立静态实验 `index-D18tLDSd.js`，真实别墅正面差异像素从1010降至183、等轴1345降至352，城堡等轴2152降至1545，具有画面收益。strict像素gate仍未完全满足，不能将局部改善宣称像素完全相同。结果 `artifacts/performance/20261010-002908-leaves-b1/results.json`，两场DPR2 quick4秒×2，画布922×751：城镇draw calls177→243、城堡190→1090；两场旋转/近景P95仍16.8ms，无>33.4ms旋转帧。真实连续剖切城镇有1帧49.9ms，P95仍16.8ms；无主线程>50ms任务，状态/geometry/raycast均通过。城堡CPU几何字节64.53→60.03MB，减少叶片重复数据。

**决定采用**：画面差异明显减少、性能目标保持。叶片实验静态包 SHA-256 `6aa1531f0dc2b0281b1e4f1dd8d485d795ae3080d20eb3675bffb05670194448`；后续最终验收全部切换此叶片方案。前述 `final` 标为采用树叶实例化前的候选结果，不混称最终产品结果。随后还修复叶片几何与预演实例缓冲的释放生命周期，最新静态包另有哈希，不能将 D18 当作最终发布包。

## 叶片方案生命周期修复前的宽视图补测

`artifacts/performance/20261010-003300-final-focus/results.json`，叶片候选 `index-D18tLDSd.js`，专注视图1440×751、DPR2（实际2880×1502像素），100,000格城镇和105,102格城堡裁片。旋转与近景各6秒×3次，切层后旋转与连续slider各6秒，12轮快速切层；这是视图补测，普通工作台全套另测编辑。最新生命周期包随后增加短补测，结果分开保存。

两场所有旋转/近景P95=16.8ms，无>33.4ms旋转帧。相机画面使用正常高像素密度，没有降低分辨率。全量状态、实际几何owner和真实点选通过；没有因为专注视图隐藏了UI面板而删掉场景内容。

## 完整百万格建筑压力探索

结果 `artifacts/performance/20261010-003548-million-stress/results.json`，叶片候选 D18、DPR1、922×751；quick 参数显式为每阶段4秒×2次、4轮急切，view-only，未测试百万格编辑。专用服务 `--max-blocks 1500000`、空气体积预算12m；原始完整城堡的1,156,099格、701状态、125种方块全部加载，既非裁片也非LOD。源坐标/完整状态全量一致，175,752个外露且支持的格均有实际几何，Y=73剖切的155,277格均有几何，恢复后175,752格核对通过；6类真实点击通过，无pageerror、无渲染缺失警告。

全景draw calls为3,677，两个旋转重复rAF P95均33.4ms（最长49.9/34.1ms），drawNow总CPU P95为33.37/25.42ms；近景两个重复P95均16.8ms，剖切后旋转P95为33.3ms。连续slider P95为33.4ms，最长50.0ms、7帧>33.4ms，无>50ms长任务。百万格全景没有达到60Hz目标，这项仅记录目标之外的容量边界，不能替代100k验收。

首次打开到完整显示26.84秒，首次主线程长任务116/267/578/59ms。两次save+refresh总耗时14.88/15.61秒；后端render缓存预算为500k格，百万格条目超出预算、立即被淘汰，因此不能获得小场景的热刷新收益。真剖切/恢复完成约345/548ms，4轮急切59–84ms。前端CPU几何attribute为116.39MB，首次JS heap约442MB；主动GC后约313MB（CDP used187MB、backing storage125MB，计量口径不同）。这不是显存占用量。

旧D18首次几何对象1,089，剖切/点选后1,274，4轮急切内部稳定不增长；CPU几何字节增加80,664、scene对象增加1，包含选框/模型缓存影响。后续叶片geometry clone/dispose补丁针对生命周期，73n阶段另测，不能用D18这段短循环证明长期无泄漏。

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label million-stress --no-fixture --quick --seconds 4 --repeats 2 --dpr 1 --view-only --max-blocks 1500000 --static-dir artifacts/performance/leaves-instancing-experiment/static --project .local/performance/data/projects/asset_ivory_castle_full_1156099.dwbench
```

## 实验 08：叶片与预演缓冲生命周期修复

历史源码提交 `3491880`：叶片实例按分块clone cached geometry并标记归属，使分块释放时能够dispose；ghost InstancedMesh释放实例缓冲。该轮包 `index-73nDMOvT.js` SHA-256 `33a5cabadc3761988c3a56894fdc4e1cd9db4da488e713f7046af68983d46309`，随后实验09更新为CeI4，73n并非当前最终产品。clone会增加真实CPU几何数据，runner按geometry对象Set去重计数，不能把增加解释为重复计算；本轮结果实测其代价。

73n阶段完整基准使用 `artifacts/performance/20261010-005007-final-leaves/` 内的固定静态快照，工程验证与GPU/CPU测量串行，避免并行任务污染数据；下表是73n独立完整8组，CeI4最终回归见实验09之后。

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label final-leaves --dpr 1 2 --seconds 6 --repeats 3 --asset .local/imports/azalea-church.litematic --asset .local/imports/mcblock-ivory-castle-upper-y51-105102.litematic --project .local/performance/data/projects/asset_villa_46281.dwbench
```

`final-leaves` 已完成8组。56个旋转/近景/剖切阶段（各组orbit3、near3、cut1）rAF P95全部16.8ms，所有阶段最长帧17.6ms，没有>33.4ms旋转帧；8场真实连续slider P95全部16.8ms，100k DPR2有1帧33.4ms（原始浮点值略超阈值、计数1），其余最长17.5ms。源状态/坐标全部相等、全景/剖切/恢复所有外露支持格都有geometry owner、实际画布点击方块身份全部通过，无pageerror。

| 73n完整验收场景 | 非空气格 | draw calls | DPR1 / DPR2各阶段最差P95 | drawNow总CPU最差P95（两DPR） | CPU几何attribute |
| --- | ---: | ---: | ---: | ---: | ---: |
| 混合城镇 | 100,000 | 243 | 16.8 / 16.8ms | 13.50ms | 160.57MB |
| 杜鹃教堂 | 36,094 | 66 | 16.8 / 16.8ms | 0.70ms | 51.00MB |
| 城堡连续上部裁片 | 105,102 | 1,090 | 16.8 / 16.8ms | 9.80ms | 61.04MB |
| 用户别墅状态投影 | 46,281 | 306 | 16.8 / 16.8ms | 2.70ms | 16.95MB |

12轮急切各轮geometry对象、texture对象、CPU几何bytes完全不变。初始与最后各场scene CPU字节增加144、geometry增加1来自后续点选框；教堂字牌texture从2到10/12，为切层产生和复用的字牌缓存，12轮内部数量稳定。不能把这个短循环称为长期无泄漏。leaf geometry clone实际使100k相较D18增加102,960 bytes，城堡增加1,013,496 bytes；换取每个分块几何确定释放。虽然树叶实例化让castle调用从190增至1,090，画面质量改善后帧目标仍满足。

100k首次导入完整显示3.11/3.62秒，城堡5.75–6.07秒，别墅直接项目打开1.20/3.33秒。8场save+refresh总耗时93–112ms；100/1000格修改到完整显示196–545ms，撤销161–480ms；新剖切完成83–235ms、恢复114–514ms。100k急切5次输入完成40–63ms（12轮）。这些是端到端UI完成时间，不能声称编辑即时完成，也不同于0.2ms后端函数热缓存数字。

保留两个异常：城堡DPR1初载出现53ms主线程任务；100k DPR2的100格commit出现52ms长任务，完整画面529ms，其1,000格commit545ms无长任务，其他UI操作没有>50ms任务。52ms任务区间内flushTransparency为24.8ms，但区间包含其他工作，未完全确认因果。此前BPb3候选的54ms同类个例也保留；针对opaque修改仍全量重建透明网格的问题，下一轮在隔离副本尝试透明部件相等时复用并做连续编辑对照。

人工直接查看本轮100k城镇、105k城堡和46k别墅的全景/剖切6张PNG：屋顶/高塔切除与层数一致，内部露出完整，楼梯/薄片/树叶轮廓连贯，玻璃可见内部；别墅已有4chest警告仍明确显示。人工检查的证据边界见后文像素核验。

73n宽视图短补测 `artifacts/performance/20261010-010119-final-leaves-focus/results.json`：混合城镇和105k城堡、CSS1440×751、DPR2实际2880×1502像素，每阶段2秒×1、4轮急切、view-only。两场orbit/near/cut和slider P95全部16.8ms，最长17.3ms，无>33.4ms帧/主线程长任务；drawNow总CPU最差P95分别12.79/9.29ms，state/geometry/rays全部通过。前述D18另有6秒×3完整宽图证据，本轮补测不宣称73n也跑了相同长度。

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label final-leaves-focus --quick --dpr 2 --seconds 2 --repeats 1 --focus --view-only --canvas-width 1440 --static-dir artifacts/performance/20261010-005007-final-leaves/static --asset .local/imports/mcblock-ivory-castle-upper-y51-105102.litematic
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label final-leaves-interactions --interactions-only --no-fixture --dpr 2 --static-dir artifacts/performance/20261010-005007-final-leaves/static --asset .local/performance/fixtures/mixed-town-100000-v1.litematic
```

73n同包连续GUI交互结果 `artifacts/performance/20261010-010311-final-leaves-interactions/results.json`：1,196相机帧P50/P95/P99=16.7/16.8/33.3ms，最大50.2ms、7帧>33.4ms、1帧>50ms，主线程长任务0；drawNow总CPU P95为14.2ms。24次pick P95为1.9ms、最大2.9ms，全部源坐标匹配，最后全量状态/geometry owner通过。100格修改403–548ms、1,000格修改481–562ms，before/current788–1052ms；修改/撤销/compare每次仍调用flushTransparency，14.8–28.9ms。首次导入另外记录51ms任务。保持P95流畅不等于没有孤立慢帧，50.2ms帧与此前52ms操作任务都保留。

## 实验 09：透明部件未变化时复用全局批次

问题：opaque编辑不影响透明格，73n依然重做全局透明网格，连续诊断中每次增加约15–29ms。先在 `artifacts/performance/transparency-reuse-experiment/` 隔离副本编译验证，不影响正在进行的73n完整测量。候选 `index-CeI4Gm9A.js` SHA-256 `bdf7f0b2a29355bbf74f662a37a357e72dd57fbaaaaac68854efa532e3b34257`。重建后比较前后透明部件的geometry引用和每格全部6字段；任何几何面mask/坐标/state/group/protected变化使部件不同，必须刷新。存在新旧signText一律刷新以保留字牌文字与材质更新；不插入新的await/yield点。

同条件100k、普通工作台DPR2、相机持续、5×100与3×1,000格commit/undo、5轮before/current对照 `artifacts/performance/20261010-010520-transparency-reuse/results.json`：16次opaque commit/undo的flush全部为0，5次compare:before也为0，5次compare:current仍刷新15.9–24.9ms。1,197帧P50/P95/P99=16.7/16.8/33.4ms、最大50.1ms、5帧>33.4ms、1帧>50ms、没有主线程长任务；drawNow P95为14.92ms，24pick P95为2.17ms/最大4ms。全量state/geometry与真实点击通过、无pageerror。

100格修改350–514ms，1,000格修改385–561ms；端到端结果仍存在API/数据库/重建等等待，不能把跳过flush等同于所有编辑快15–29ms。单次相同硬件对照确认消除了重复CPU工作，但rAF最差帧、P99和drawNow P95没有一致改善，**不宣称此改动消除52ms长任务或显著提升稳定帧率**。主代理决定采用减少冗余的机制，随后补精准E2E与最终包差异回归并通过；73n完整结果与异常作为前一轮独立证据保留。

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label transparency-reuse --interactions-only --no-fixture --dpr 2 --static-dir artifacts/performance/transparency-reuse-experiment/static --asset .local/performance/fixtures/mixed-town-100000-v1.litematic
```

## 当前CeI4最终包差异回归

产品提交 `100afea` 已冻结，和实验09的CeI4候选逐字节一致，因此该候选的连续GUI交互是同一个最终静态包的证据，没有重复运行。最新回归依旧隔离服务、固定静态快照，工程进程全部退出后才使用GPU。

可审查提交链为 `193f8f1`（扩展计划基线）→ `0cd66fe`（保留并发UI工作）→ `6746de0`（后端缓存/局部编辑）→ `8f040fb`（渲染合批/异步剖切）→ `3491880`（叶片质量与缓冲生命周期）→ `1566f8a`（可复现性能/导出审计工具）→ `100afea`（不变透明批次复用）。历史各静态快照及JSON包含当时源码哈希与dirty状态；提交后的最终三次回归只用100afea源码和同一CeI4静态哈希。

`artifacts/performance/20261010-011313-final-100k/results.json` 完成100k城镇和36k教堂×DPR1/2共4组full，每组orbit/near各6秒×3、cut/slider6秒、12轮急切、真实UI100/1000预演/取消/commit/undo。命令未显式传asset时runner默认追加本地教堂，因此实际4组，与最初预计单100k两组不同；保留额外数据，后续真实quick不重复教堂。所有28个旋转/近景/剖切阶段及4场slider P95为16.8ms，全部稳定阶段和slider最长17.7ms（church DPR2 slider，100k自身最长17.5ms），无>33.4ms帧。全部源状态/全景-剖切-恢复geometry owner与真实点击通过，12轮geometry/texture/CPU bytes序列稳定，无pageerror。

| 最终CeI4的100k full | DPR1 | DPR2 |
| --- | ---: | ---: |
| draw calls | 243 | 243 |
| orbit/near/cut最差rAF P95 | 16.8ms | 16.8ms |
| drawNow总CPU最差P95 | 13.80ms | 13.20ms |
| 首次导入完整显示 | 3,303ms | 3,436ms |
| 新剖切 / 恢复总完成 | 220 / 462ms | 222 / 492ms |
| 100格commit / undo完整显示 | 330 / 311ms | 514 / 411ms |
| 1,000格commit / undo完整显示 | 448 / 446ms | 277 / 392ms |
| 5次急切单轮总完成（12轮范围） | 43.5–46.9ms | 40.9–48.8ms |

100k首次导入DPR1有一次54ms长任务、DPR2无；稳定帧和测试UI阶段无长任务，不能把后者写成整个过程绝无卡顿。两场100/1000格opaque commit/undo均没有全局透明flush；geometry bytes仍160,565,976，点选后增加144；GC后JS heap约193MB，口径和显存不同。教堂稳定帧P95同为16.8ms，drawNow最差P95为0.70ms，字体纹理缓存12轮内稳定。

原版 `baseline-fixed` 是2秒×1的quick，最终CeI4是6秒×3，采样长度不同。相同本机、DPR1/画布、完整100k内容下draw calls的29,596→243收益直接可查；原版rAF P95为183.4ms、最终16.8ms可支持瓶颈改善，但没有声称两者是相同持续时间的FPS统计，性能结论不外推其他GPU/浏览器。

最终两场真实建筑DPR2 quick `artifacts/performance/20261010-011750-final-real-regression/results.json`：castle105,102格与用户villa46,281格，每阶段2秒×1、4轮急切、100/1000格完整GUI编辑。各orbit/near/cut最差P95为16.9ms、最长17.4ms，slider P95为16.8ms，无>33.4ms帧/主线程长任务；drawNow最差P95为9.90/2.60ms。所有源state/坐标、实际geometry覆盖与真实点选通过，4轮memory序列稳定，无pageerror。villa保留4个chest警告和188NBT投影范围限制。教堂已有前述两DPR full，没有机械重复quick。CeI4没有重新跑castle/villa两DPR的6秒×3完整8组，73n历史包的8组不能冒充此包验收。

最终宽focus短补测 `artifacts/performance/20261010-011933-final-focus-reuse/results.json`：100k城镇+105k城堡，CSS1440×751、DPR2实际2880×1502像素，各阶段2秒×1、4轮急切、view-only；所有orbit/near/cut及slider P95均16.8ms、最长17.4ms，无>33.4ms帧/长任务，drawNow最差P95为12.09/9.29ms。数据、geometry owner、点选和短循环内存稳定均通过，没有降低分辨率。原D18宽图6秒×3属于历史独立包，本轮宽图补测明确为短测试。

最终CeI4的100k、castle和villa普通工作台DPR2 full/cut共6张PNG已直接人工查看：玻璃可见内部，屋顶/高塔按照层数切除、切面内部完整，楼梯/薄片/树叶和真实建筑轮廓连贯，没有明显漏建筑；villa4chest警告明确。该目视检查不替代strict像素gate，边界见下节。所有最终三份结果 `completed=true`、source提交/静态SHA对应100afea/CeI4，三次Chrome与隔离server进程均正常退出，记录与截图保留。

```powershell
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label final-100k --dpr 1 2 --seconds 6 --repeats 3
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label final-real-regression --no-fixture --quick --dpr 2 --seconds 2 --repeats 1 --static-dir artifacts/performance/20261010-011313-final-100k/static --asset .local/imports/mcblock-ivory-castle-upper-y51-105102.litematic --project .local/performance/data/projects/asset_villa_46281.dwbench
.venv/Scripts/python.exe scripts/benchmark_rendering.py --label final-focus-reuse --quick --dpr 2 --seconds 2 --repeats 1 --focus --view-only --canvas-width 1440 --static-dir artifacts/performance/20261010-011313-final-100k/static --asset .local/imports/mcblock-ivory-castle-upper-y51-105102.litematic
```

## 工程验证

73n阶段前端和后端已完成Windows pytest 63通过、1项Windows锁行为跳过，mypy 33文件、ruff/format 79文件及前端TypeScript/Prettier通过；uv locked check、源码构建与重新构建的wheel干净环境安装通过。wheel内渲染cache模块和73n文件逐字节校验。WSL Ubuntu22.04、Python3.12.15下locked依赖、54项core测试通过（10项环境相关测试未选取）、mypy/ruff、构建和干净wheel安装通过。首次误用旧wheel的检查不作为最终证据，随后已重建重测。

CeI4最终实现（源码对应提交 `100afea`）精准渲染E2E6项通过（包含新增2项透明复用/失效检查），前端构建后的CeI4与隔离候选逐字节相同；Windows最新wheel干净安装通过。WSL重新完成54项core通过、12项未选取、mypy33/ruff/构建与最新wheel干净安装，wheel内CeI4逐字节核验通过。GPU/CPU回归在所有工程进程结束后才开始。Linux未进行独立GPU帧率验收，性能数字只属于记录的Windows硬件环境。

## 独立导出与源NBT边界

`scripts/verify_performance_exports.py` 的独立litemapy全量解码结果保存在 `artifacts/performance/asset-export-crosscheck.json`。100k夹具与105,102格原生城堡裁片的所有非空气状态及世界坐标逐项一致；裁片的26个block entity/NBT、区域原标签、无关metadata与根unknown tags保留，源文件测试前后SHA相同。没有对原始下载或源项目进行覆盖。

用户别墅46,281格所有状态和坐标在1.20.1投影及导出中一致，但原Version5/DataVersion3578仍拒绝原生导入。原始bytes SHA-256 `fb057ff168d9703d5ba098d389c2807ad4d7521a94b7aa3478208c63fa87b8e4` 在 `benchmark_original_litematic` provenance附件中逐字节保存、188处保护位置保留。renderer没有从provenance取出NBT，字牌文字未显示；188个源block entity及NBT也不在新state-only v6/3465导出中。独立审计因此明确 `full_source_scope_passed=false`，`all_state_projection_exports_verified=true` 只代表状态投影。4个chest的既有special渲染warning是另外的模型支持限制，不能用这4格概括188个NBT的边界。

## 像素核验与可见正确性的边界

固定相机/矩阵、固定清屏和grid颜色、相同后端与数据库比较结果在 `artifacts/performance/visual-leaves-b1/report.json`：5场景×6视图共30张、叶片D18候选。**每通道容差3的strict gate未通过**。3个真实建筑的差异均位于1px边缘邻域，建筑内部差异为0；透明probe内部仍有最高8级通道差异（带文字与无文字两个probe均存在）。叶片方案让别墅六视图超容差像素总数5,602→1,002（减少82.1%），城堡7,150→4,322（减少39.6%）；教堂3,096未变化。像素边缘差异最大可到118，不能描述成严格像素一致、或所有变化都小于容差。

73n和最终CeI4静态包另有全量数据/实际geometry owner/真实点选和全景剖切截图检查；生命周期/透明复用修复没有重新进行30张exact-camera像素比较，D18像素结论不得冒充73n或CeI4独立strict通过。截图人工复核仅支持这些视角下没有明显漏建筑、透明玻璃可见内部和切层有效，不证明任意视角与Minecraft原版光照/像素完全相同。差异与合批、叶片绘制有关，局部浮点变换与共面对象排序的具体因果尚未拆分验证。

## 实验记录模板

每次优化填写：问题与假设、改动文件与关键机制、Git 提交/源码哈希、固定条件与测试命令、原始结果路径、前后指标、正确性检查、代价/局限、保留或回退决定。失败尝试同样记录原因，不能删去不利样本或将 quick 结果包装成完整验收。

## 性能测量文件清单

| 文件 | 类型 | 内容 |
| --- | --- | --- |
| `scripts/benchmark_rendering.py` | 新增、纳入版本控制 | 隔离服务、确定性夹具、真实 UI 操作、逐格校验、帧/提交/长任务/内存测量、原始结果与截图 |
| `docs/RENDERING_OPTIMIZATION_LOG.md` | 新增、纳入版本控制 | 本次及后续优化实验的目标、方法、失败/成功结果和边界 |
| `artifacts/performance/` | 本地生成、Git 忽略 | 原始 JSON、静态包快照、隔离数据库、服务日志、全景和剖切截图 |
| `.local/performance/fixtures/` | 本地生成、Git 忽略 | 可由脚本重建的确定性 100,000 格蓝图 |
