# MotionBase

用 Python 编排 Blender 的本地动画执行基座。把创作对话整理成镜头描述，再使用可复用的角色、舞台、Action 和画风生成可编辑的 `.blend` 与 MP4。

**引擎、资产与作品分开维护，Skills 与引擎一起演进。** 当前可运行范例是原创狐面角色的五秒腾跃镜头，青绿赛璐璐和朱砂木刻两种画风共用动作、相机、音轨和拖尾轨迹。

## 仓库与目录

当前在同一个 GitHub 仓库内分别维护两条分支，检出为同级的两个独立工作目录：

| 位置 | 内容 |
| --- | --- |
| [`main`](https://github.com/h-yu-u/MotionBase/tree/main) → `MotionBase/` | Python 引擎、数据契约、项目 Skills、通用测试和作品范例 |
| [`assets`](https://github.com/h-yu-u/MotionBase/tree/assets) → `motionbase-assets/` | 独立资产工程，包含 `packs/fox-cliff` 的模型、动作、背景、声音、画风及制作源码 |
| `MotionBase/productions/fox-study/` | 作品 brief、镜头计划、资产选择、版本锁和评审记录 |

资产分支的根目录本身就是完整的资产工程，可以直接迁移到独立仓库；引擎通过 `pack.json` 路径消费资产，与 Git 托管位置无关。详见[架构与边界](docs/architecture.zh-CN.md)。

## 快速开始

需要 Python 3.10+、Blender 4.5 LTS；生成视频还需要支持 `libx264` / AAC 的 FFmpeg。默认在 PATH 和 macOS 标准应用目录寻找 Blender；CLI 本身无第三方 Python 依赖。

```bash
git clone https://github.com/h-yu-u/MotionBase.git
git clone --branch assets --single-branch https://github.com/h-yu-u/MotionBase.git motionbase-assets
cd MotionBase
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows 可用 `.venv\Scripts\activate` 激活，并使用 `python`。macOS 使用非标准 Blender 安装位置、PATH 中有旧版 Blender，或者希望固定运行版本时，设置环境变量：

```bash
export BLENDER_BIN=/Applications/Blender.app/Contents/MacOS/Blender
```

也可以在 `check/build/render/compare` 中指定 `--blender /path/to/blender`。当前实际验证的版本为 Blender 4.5.0；低于 4.5 会给出明确错误。已有支持的 `bpy` Python 环境在没有 Blender 可执行文件时也可作为后端。

### 1. 查看资产与画风

```bash
motionbase assets --pack ../motionbase-assets/packs/fox-cliff/pack.json
motionbase styles --pack ../motionbase-assets/packs/fox-cliff/pack.json
```

### 2. 编译并检查示例镜头

随仓库提供的 `project.lock.json` 固定了引擎源码、项目、镜头和资产文件的指纹。先直接编译即可验证这份锁：

```bash
motionbase compile productions/fox-study/project.json --shot 010 -o productions/fox-study/build/010.json
motionbase check productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json
```

`compile` 输出配套的 `<名称>.json` 与 `<名称>.style.json`。编译产物使用本机绝对路径，保存在忽略的 `build/` 中；可移植的源文件是项目、资产包和版本锁。

新建作品或有意更新输入后，用 `motionbase lock productions/fox-study/project.json` 接受新的指纹。若旧作品提示锁已过期，先核对变更原因，再更新锁。

### 3. 构建可编辑工程和视频

```bash
motionbase build productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json -o productions/fox-study/build/010.blend
motionbase render productions/fox-study/build/010.json --style productions/fox-study/build/010.style.json -o productions/fox-study/build/010.mp4
```

默认镜头为 960 × 540、30 fps、150 帧，即 5 秒。渲染使用 CPU Cycles，临时 PNG 序列完成后由 FFmpeg 编码为 H.264。只有整条执行成功才替换目标文件。可以在作品源 JSON 中调整 `size` 和 `samples`，再重新锁定、编译。

### 4. 只换画风并比较

```bash
motionbase compile productions/fox-study/project.json --shot 010 --style fox-cliff:look.woodblock -o productions/fox-study/build/010-woodblock.json
motionbase build productions/fox-study/build/010-woodblock.json --style productions/fox-study/build/010-woodblock.style.json -o productions/fox-study/build/010-woodblock.blend
motionbase compare productions/fox-study/build/010.blend productions/fox-study/build/010-woodblock.blend --report productions/fox-study/build/compare.json
```

临时画风选择只能来自已锁定的资产包。确认采用后，把风格写回 `project.json`，再更新锁。`compare` 检查相机与骨骼运动、相机投影、焦距/正交缩放、画幅、裁切和时间，成功返回 `0`，差异返回 `1`，并提供 JSON 报告。它不判断画风是否好看，也不检测接地滑步。

## 和 AI 一起创作

读取仓库内的项目 Skills：

- [`motionbase-direct`](skills/motionbase-direct/SKILL.md)：把描述变成 brief、镜头计划、资产选择和可执行输入。
- [`motionbase-review`](skills/motionbase-review/SKILL.md)：根据预览反馈进行局部修改，保存基准并验证保留项。

例如：

> 读取 skills/motionbase-direct/SKILL.md。用现有资产制作一个五秒腾跃镜头，先生成预览。

> 读取 skills/motionbase-review/SKILL.md。把 010 镜头换成木刻，保留动作、构图和时长。

Skills 随仓库交付；若 AI 客户端没有自动发现 `skills/`，直接提供 `SKILL.md` 路径。完整流程见[创作与评审指南](docs/creative-workflow.zh-CN.md)。

## 接口与兼容性

| 命令 | 职责 |
| --- | --- |
| `assets --pack PACK` | 验证并查看资产清单 |
| `styles [--pack PACK] [--directory DIR]` | 查看内置兼容预设和外部画风 |
| `lock PROJECT` | 固定引擎、项目、镜头和资产文件指纹 |
| `compile PROJECT --shot ID -o FILE` | 验证锁、检查骨架兼容性、将资产 ID 编译为 v1 文件路径 |
| `check SHOT --style STYLE` | 验证 JSON、加载实际 Blender 集合/骨架/Action/材质并检查绑定 |
| `build SHOT --style STYLE -o FILE.blend` | 生成可编辑 Blender 工程 |
| `render SHOT --style STYLE -o FILE.mp4` | 渲染帧序列并编码视频 |
| `compare A.blend B.blend --report FILE.json` | 检查需要保留的运动、构图和时间 |

原有 v1 文件镜头无需项目编译即可继续使用：

```bash
motionbase check productions/fox-study/shots/010.legacy.json --style moon-cel
motionbase build productions/fox-study/shots/010.legacy.json --style woodblock -o productions/fox-study/build/legacy.blend
```

`moon-cel` / `woodblock` 两个名称作为兼容预设随 Python 包提供；完整的示例美术源码和权威资产位于独立资产工程。外部画风可使用 JSON 路径，也可通过 `--style-dir DIR` 按名称查找。自定义材质库通过风格的 `materials.file` 与 `roles` 映射接入。

字段与路径规则见 [`contracts/`](contracts/) 和[数据契约](docs/contracts.zh-CN.md)。不会自动重定向不兼容骨架。当前 v1 使用舞台相机，镜头级相机覆盖、多镜头转场编排和接地约束检测仍属于后续扩展；当前范例是适合侧拍的 2.5D 角色。

## 验证与开发

引擎的测试素材在临时目录中程序生成，独立于狐面资产包：

```bash
python3 -m unittest discover -s tests -v
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P tests/integration/runtime_contract.py
python3 tests/render_smoke.py --blender /path/to/blender
```

最后一个命令还要求 FFmpeg 和 FFprobe，检查实际输出的视频与音轨。资产工程有自己的角色专属回归：

```bash
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P ../motionbase-assets/packs/fox-cliff/tests/asset_contract.py -- --engine-root .
```

GitHub Actions 执行纯 Python 测试、安装包检查、Blender 集成测试和小尺寸视频编码测试。实际迁移验收与范围见[验证记录](docs/verification.zh-CN.md)。
