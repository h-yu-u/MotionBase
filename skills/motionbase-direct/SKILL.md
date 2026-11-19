---
name: motionbase-direct
description: 将创作描述、分镜要求和现有资产转成 MotionBase 作品 brief、镜头计划、版本锁和可执行镜头。用于新建作品、设计镜头、安排已有动作或生成预览；修改既有预览时使用 motionbase-review。
---

# MotionBase 导演

从用户的创作意图生成作品输入，通过 MotionBase 执行检查、构建与渲染。

## 读取创作上下文

1. 定位 MotionBase 仓库和目标作品目录；阅读仓库 `AGENTS.md`、作品 `brief.md`、`project.json`、镜头及最近评审记录。对新作品读取 `productions/fox-study/` 作为可执行范例。
2. 阅读 [创作记录](references/creative-brief.md)，记录时长、画幅、节奏、风格及用户要求保留的内容。采用已有偏好和明确授权；仅在缺失信息实质改变方案时追问。
3. 使用仓库根目录的 `python3 -m motionbase --help` 核对当前版本的入口。需要可执行路径时使用 `--blender` 或 `BLENDER_BIN`。
4. 阅读 `contracts/project-v1.schema.json`、`contracts/shot-v1.schema.json`、`contracts/style-v1.schema.json` 和实际样例。以契约及资产清单为准填写字段，不猜字段、集合名、骨名或 Action 名。

## 选择资产并安排镜头

1. 对作品使用的每个资产包运行 `python3 -m motionbase assets --pack <pack.json>`，用 `python3 -m motionbase styles --pack <pack.json>` 查看画风。读清单中的类型、集合、Action、兼容信息和适用视角。
2. 选择清单中确实存在的角色、舞台、动作和风格；将缺失资产写入 brief 的制作清单，说明它阻塞哪些镜头。
3. 将跨作品可复用内容放入资产包；将本片的构图、时序、局部覆盖和变体放入作品工作区。保持引擎独立于具体角色和色板。
4. 把描述转换为有明确帧范围的镜头计划，按 `frames / fps` 核对时长。确认动作片段有序、在镜头范围内且不重叠；按源动作实际能力设计节奏。
5. 编写 `project.json` 与 `shots/<镜头号>.json`。按当前项目契约填写资产 ID 和路径；路径相对规则从契约、范例及 CLI 读取。

## 执行镜头

在仓库根目录执行。以下以已配置好的 `fox-study / 010` 为例：

```bash
python3 -m motionbase lock productions/fox-study/project.json
python3 -m motionbase compile productions/fox-study/project.json --shot 010 -o productions/fox-study/build/010.json
python3 -m motionbase check productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json
python3 -m motionbase build productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json -o productions/fox-study/build/010.blend
python3 -m motionbase render productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json -o productions/fox-study/build/010.mp4
```

- 首次创建作品或有意更新所选资产后生成锁。对既有作品先验证现有锁；遇到资产内容漂移时定位原因，不以重新锁定掩盖意外变动。
- 将编译结果及同名 `.style.json` 一起交给 `check/build/render`。以作品源文件为编辑入口；修改后重新编译。
- 保留可复现输入和有价值的评审基准；把中间帧、编译 JSON、`.blend` 和 MP4 放在作品 `build/` 下。
- 对原 v1 路径镜头，直接使用 `check/build/render SHOT --style NAME_OR_PATH`；无需为兼容旧输入增加虚构的项目参数。

## 交付与继续沟通

记录作品、镜头号、输入文件、风格、锁版本、执行命令及结果。观看生成的预览，说明画面是否符合 brief；将审美判断与程序检查结果分开。没有执行渲染时明确标明尚无成片，不把构建成功写成视觉验收通过。

对后续“换风格”“落地更稳”等反馈，沿用同一作品和镜头号，交由 `motionbase-review` 定位并修改。
