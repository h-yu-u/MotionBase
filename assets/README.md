# MotionBase Assets

MotionBase 仓库内的共享美术资产模块。引擎、资产和作品统一在 `main` 分支维护，分别放在 `motionbase/`、`assets/` 和 `productions/`，一次克隆即可运行示例。

## 资产包

| 包 | 内容 | 入口 |
| --- | --- | --- |
| `fox-cliff` · `1.0.0` | 原创狐面角色、山崖舞台、五秒腾跃动作、两种画风和合成音轨 | [pack.json](packs/fox-cliff/pack.json) |

阅读 [fox-cliff 的兼容性与制作说明](packs/fox-cliff/README.md)。二进制资产与生成源码一起维护，日常渲染直接消费 `.blend`、`.json` 和 `.wav`。

## 使用

在仓库根目录运行：

```sh
python3 -m motionbase assets --pack assets/packs/fox-cliff/pack.json
python3 -m motionbase compile productions/fox-study/project.json --shot 010 -o productions/fox-study/build/010.json
```

作品通过包清单路径和资产 ID 选择素材。每个包内部的文件路径都相对 `pack.json`，因此可以整体搬迁；引擎仍然支持仓库外的包，当前范例统一引用仓库内的资产。

## 模块与版本边界

资产生成器仅依赖 Blender Python API 或 Python 标准库，不导入引擎源码。资产专属回归依赖引擎公共接口，通用引擎测试则自行生成最小素材。Python 安装包仅分发执行引擎与兼容预设。

`pack.json` 的 `revision` 标识资产修订，`rig_id` 声明角色与动作的骨架兼容关系。作品锁保存文件内容摘要。一次涉及契约、资产和镜头的变更可在 `main` 的同一提交中更新并验证，避免跨分支版本配对。

单部作品的动作或材质变体先保存在作品工作区；需要跨作品复用时再提升为共享资产包。未来若资产需要独立发布或管理大型文件，可以调整包的存放与发布方式，继续沿用当前清单接口。

## 素材来源

本模块承接原 MotionBase 演示工程中的代码生成素材。狐面剪影、山崖舞台、骨骼动作与声音均保留对应源码，见 [来源记录](NOTICE.md)。
