# 用 AI 创作和评审 MotionBase 镜头

MotionBase 将对话中的创作意图保存到作品工作区，再由 CLI 执行。两个项目级 Skills 与引擎一起维护，调用同一套契约和命令。

| Skill | 适用请求 | 主要产物 |
| --- | --- | --- |
| [`motionbase-direct`](../skills/motionbase-direct/SKILL.md) | 新建作品、设计镜头、安排已有动作 | brief、镜头计划、项目与镜头 JSON、版本锁、预览 |
| [`motionbase-review`](../skills/motionbase-review/SKILL.md) | 换画风、改局部动作、根据预览迭代 | 修改后的输入、前后对照、检查报告、评审记录 |

这些文件是仓库内的项目 Skills。支持读取项目 Skills 的 AI 工具可以使用它们；如果工具没有自动发现该目录，在请求中提供对应 `SKILL.md` 的路径并让 AI 先读取。仓库交付不代表已安装到某个客户端的个人技能目录。

## 1. 从一句创作描述开始

首次使用时，把引擎和资产取到同级目录。当前同一 GitHub 仓库的 `main` 与 `assets` 分支分别保存两套独立历史：

```bash
git clone https://github.com/h-yu-u/MotionBase.git
git clone --branch assets --single-branch https://github.com/h-yu-u/MotionBase.git motionbase-assets
cd MotionBase
```

`assets` 分支根目录就是独立资产工程。后续可以将它原样推到单独仓库，作品依然通过旁边的 `motionbase-assets/packs/` 使用资产。

例如：

> 读取 `skills/motionbase-direct/SKILL.md`。做一个 5 秒远景，角色跃起，最后收住，背景有纵深。使用已有资产，先生成预览。

导演流程先读资产包，再写作品 `brief.md` 和 `shots/010.json`。brief 保留已经确定的目标、节拍和不可改变项；镜头只使用当前清单中存在的资产。缺少的动作、模型或场景进入制作清单，并指出阻塞的镜头。

在 MotionBase 仓库根目录检查配套资产：

```bash
python3 -m motionbase assets --pack ../motionbase-assets/packs/fox-cliff/pack.json
python3 -m motionbase styles --pack ../motionbase-assets/packs/fox-cliff/pack.json
```

镜头字段以 [`shot-v1.schema.json`](../contracts/shot-v1.schema.json) 为准，作品选择以 [`project-v1.schema.json`](../contracts/project-v1.schema.json) 为准。角色骨名、Action 名和集合名来自实际资产，Skills 不维护另一份硬编码数据。

## 2. 固定输入并生成预览

以下命令使用仓库内的 `fox-study` 作品范例。先按主 README 准备配套资产和运行环境，再在仓库根目录执行：

```bash
python3 -m motionbase lock productions/fox-study/project.json
python3 -m motionbase compile productions/fox-study/project.json --shot 010 -o productions/fox-study/build/010.json
python3 -m motionbase check productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json
python3 -m motionbase build productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json -o productions/fox-study/build/010.blend
python3 -m motionbase render productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json -o productions/fox-study/build/010.mp4
```

`lock` 记录项目、镜头、引擎源码和资产内容的指纹，`compile` 验证锁并将资产 ID 解析为旧 v1 能执行的文件路径，同时输出相邻的 `.style.json`。三个执行命令继续接收 `shot.json + style`；编译后的两个文件应配套使用。引擎或输入变化后，先核对变化再接受新锁。

对既有作品，检查锁失败时先查明哪些输入发生变化。有意更新资产、镜头或风格后再重新生成锁，避免无意接纳共享资产改动。需要试验另一画风时，可以给 `compile` 加 `--style <包ID:风格ID>`；被引用的包必须已经包含在当前锁中。确定采用后，把选择写回项目并更新锁。

旧的、直接引用文件路径的 v1 镜头仍可使用 `check/build/render SHOT --style NAME_OR_PATH`。使用显式 `--blender /path/to/blender` 或 `BLENDER_BIN` 可以选择 Blender 可执行文件。

## 3. 根据预览继续修改

例如：

> 读取 `skills/motionbase-review/SKILL.md`。把 `fox-study / 010` 换成木刻风格，动作、构图和五秒时长全部保留。

评审流程先保存原镜头和基准 `.blend`，再修改项目风格、更新锁并重新执行。每轮把前后产物放入作品 `build/review-001/before/` 与 `after/` 等独立目录，避免覆盖比较依据。

当请求要求保持运动和构图时，运行：

```bash
python3 -m motionbase compare productions/fox-study/build/review-001/before/010.blend productions/fox-study/build/review-001/after/010.blend --report productions/fox-study/build/review-001/compare.json
```

`compare` 检查帧率、帧数、画幅、相机投影和逐帧相机及骨骼世界变换，退出码 `0` 为通过、`1` 为失败。它为保留运动和构图提供可复查依据；新画风是否清楚、是否符合创作意图，仍需观看预览判断。

另一个请求可能是：

> 起跳提前四帧，但落地时间和落地点保持。

此时应修改作品专用 Action 变体的起跳段，保留落地段，再重新构建相关拖尾。整体平移动作片段会同时改变落地时间。全帧运动比较出现局部差异符合本次意图，验收重点应转为落地边界与用户指定的保留项；当前工具未自动测量的条件需要在记录中写明。

## 4. 把每轮决定留在作品里

| 位置 | 保存内容 |
| --- | --- |
| `brief.md` | 已接受的创作目标、保留项、镜头节拍和待制作资产 |
| `project.json`、`shots/` | 项目资产选择、画风与可编辑镜头 |
| `project.lock.json` | 用于重现的版本与内容校验信息 |
| `reviews/` | 用户反馈、改动字段、帧段、检查结论和预览引用 |
| `build/` | 编译结果、Blender 工程、中间帧、视频和比较报告 |

作品专属动作、机位和美术变体先保留在作品内。需要复用于其他作品时，再形成共享资产包的新版本。引擎负责统一执行与检查；Skills 负责把创作沟通落实为这些已有能力的输入和评审结果。
