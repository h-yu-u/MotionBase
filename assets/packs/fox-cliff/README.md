# Fox Cliff

原创狐面角色的五秒腾跃演示资产包，版本 `1.0.0`。

## 清单

| 资产 ID | 种类 | 文件 | Blender 数据块 |
| --- | --- | --- | --- |
| `character.fox` | `character` | `characters/fox.blend` | 集合 `Performer`，骨架 `PerformerRig` |
| `stage.cliff` | `stage` | `stages/cliff.blend` | 集合 `Cliff`，相机 `ShotCamera` |
| `action.leap` | `action` | `actions/leap.blend` | Action `Leap and sweep` |
| `look.moon-cel` | `style` | `looks/moon-cel.json` | 青绿赛璐璐 |
| `look.woodblock` | `style` | `looks/woodblock.json` | 朱砂木刻 |
| `audio.leap` | `audio` | `audio/leap.wav` | 五秒单声道合成音轨 |

作品通过 `fox-cliff:character.fox` 等完整 ID 引用资产。清单中的文件路径相对于 `pack.json`。`props/` 记录当前随角色发布的刀具；当前清单没有独立道具项。

## 兼容性

- 使用 Blender 4.5 LTS。原始工程记录的验证环境为 Blender 4.5.16；资产采用单对象槽位 Action。
- 角色和动作共用 `rig_id: fox-humanoid-v1`。这表示相同骨名、静止姿势和尺寸契约，不等于自动骨骼重定向。
- 角色由 2.5D 剪纸网格构成，适合当前正交侧视机位。环绕拍摄需要制作完整三维角色。
- 舞台相机保留原有 150 帧运镜；当前镜头使用该舞台相机。
- `prop` 骨骼驱动刀具。拖尾采样端点由作品镜头提供，坐标位于骨骼局部空间。
- 两种画风覆盖同一套语义材质用途，支持复用相同动作、相机、音轨和拖尾轨迹。
- 源动作通过分段插值保持支撑脚目标位置，但当前包没有自动滑步质量判定；审片仍需检查接地效果。

## 从源码重新制作

在 MotionBase 仓库根目录执行：

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python assets/packs/fox-cliff/source/make_assets.py
python3 assets/packs/fox-cliff/source/sound.py
```

`make_assets.py` 分别写入 `characters/fox.blend`、`actions/leap.blend` 和 `stages/cliff.blend`；`sound.py` 写入 `audio/leap.wav`。这些命令会替换包内对应资产；画风 JSON 和包版本由创作者维护。

要为作品制作局部变体，可以输出到其他目录：

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python assets/packs/fox-cliff/source/make_assets.py -- --output /path/to/production/assets/fox-variant
python3 assets/packs/fox-cliff/source/sound.py --output /path/to/production/assets/fox-variant/audio/leap.wav
```

`source/choreography.py` 的 `POSES` 决定动作节奏，生成器读取 `character.py` 中的肢体尺寸。要“起跳提前四帧、落地时刻不变”，应修改动作源的起跳段并重新制作作品变体。整体移动或缩放 NLA 片段会同时影响后续时序。

## 包级回归

在 MotionBase 仓库根目录执行：

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python assets/packs/fox-cliff/tests/asset_contract.py -- --engine-root .
```

该回归使用包内 `tests/shot.json`，覆盖角色重复实例、缩短动作后末姿态一致、自定义材质替换和材质色板映射。它依赖引擎的公共装配接口，独立于任何具体作品的 `project.json`。
