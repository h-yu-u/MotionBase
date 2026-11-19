# MotionBase Assets

独立维护的 MotionBase 美术资产与制作源码。引擎负责解释契约、装配和渲染；本仓库负责可供多部作品复用的角色、舞台、动作、画风和声音。

## 资产包

| 包 | 内容 | 入口 |
| --- | --- | --- |
| `fox-cliff` · `1.0.0` | 原创狐面角色、山崖舞台、五秒腾跃动作、两种画风和合成音轨 | [pack.json](packs/fox-cliff/pack.json) |

阅读 [fox-cliff 的兼容性与制作说明](packs/fox-cliff/README.md)。二进制资产与生成源码一起维护，日常渲染直接消费 `.blend`、`.json` 与 `.wav` 文件。

## 与引擎一起使用

当前引擎和资产使用两条独立 Git 历史，暂时托管在同一个 GitHub 仓库：`main` 分支保存引擎，`assets` 分支保存本资产仓库的根目录。分别克隆到同一个父目录下：

```sh
git clone --branch main --single-branch https://github.com/h-yu-u/MotionBase.git MotionBase
git clone --branch assets --single-branch https://github.com/h-yu-u/MotionBase.git motionbase-assets
```

引擎中的 `productions/fox-study/project.json` 通过相对路径引用本仓库的 `pack.json`；更换安装位置时更新作品中的包路径，再重新生成版本锁。资产仓本地的检出分支为 `assets`，资产修改提交到这条分支。

以后建立独立的 `motionbase-assets` 远端时，可以把当前资产历史直接推送为该仓库的 `main` 分支。保持本地目录名 `motionbase-assets` 即可继续使用现有作品路径。

资产包没有引擎源码依赖。源生成器只依赖 Blender Python API 或 Python 标准库。资产集成回归会加载 MotionBase，因此需要提供引擎源码路径或在 Blender 的 Python 环境中安装引擎。

## 版本边界

`pack.json` 中的 `revision` 标识资产包发布版本，`rig_id` 声明角色与动作的骨架兼容关系。作品锁文件负责保存实际内容摘要，避免相同版本号的资产在制作中途被替换。

单部作品需要修改起跳段、角色造型或材质时，先在作品工作区建立变体。确认需要跨作品复用后，再发布资产包新版本。

## 素材来源

本仓库承接原 MotionBase 演示工程中的代码生成素材。狐面剪影、山崖舞台、骨骼动作和声音均保留对应源码，见 [来源记录](NOTICE.md)。
