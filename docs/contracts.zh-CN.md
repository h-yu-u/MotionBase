# 数据契约与路径规则

静态 JSON Schema 在 [`contracts/`](../contracts/)。命令行还检查文件存在、引用、片段顺序、骨架兼容和内容指纹；Blender 检查实际集合、骨架、Action 数据路径及材质。

## 资产包

`pack.json` 使用 `version: 1`，声明 `id`、人可读修订 `revision`、制作版本 `blender`，以及以资产 ID 为键的 `assets` 对象。完整可运行清单在同一仓库的 [`assets/packs/fox-cliff/pack.json`](../assets/packs/fox-cliff/pack.json)。引用格式为 `<包ID>:<资产ID>`，例如 `fox-cliff:character.fox`。

| kind | 类型专属字段 |
| --- | --- |
| `character` | `collection`、`rig`、`rig_id` |
| `stage` | `collection`、`camera` |
| `action` | `action`、`rig_id` |
| `style` | 风格 JSON 文件；风格字段由文件提供 |
| `audio` | 可由 FFmpeg 解码的声音文件 |
| `prop` | `collection`；清单可描述，当前 v1 没有独立道具实例字段 |
| `material` | `material`；清单可描述，渲染通过风格 `materials.roles` 使用 |

每项都有 `kind`、`file`。`file` 必须相对包清单，解析后不得逃出包根目录，包括符号链接。Blender 资产使用 `.blend`，Style 使用 JSON。Style 引用的材质库也必须在同一包内；贴图等依赖应由作者打包进 `.blend`。

`blender` 记录资产制作版本。执行器当前统一要求 Blender 4.5+，没有根据此字段自动下载或选择版本。Action 的 `rig_id` 必须与角色一致，骨骼与比例的兼容性由资产作者声明；实际动画数据路径随后由 Blender 校验。

## 作品与 ID 镜头

```json
{
  "version": 1,
  "id": "fox-study",
  "packs": {"fox-cliff": "../../assets/packs/fox-cliff/pack.json"},
  "shots": {"010": {"file": "shots/010.json", "style": "fox-cliff:look.moon-cel"}}
}
```

包清单路径与镜头路径相对 `project.json`。也能解析绝对路径，但相对路径便于整体搬迁。镜头必须位于当前作品目录内。作品专用变体可建立本地包，通过作品清单引用。

```json
{
  "version": 1, "fps": 30, "frames": 150, "size": [960, 540],
  "stage": {"asset": "fox-cliff:stage.cliff"},
  "actors": [{
    "id": "fox", "asset": "fox-cliff:character.fox", "position": [0, 0, 0],
    "clips": [{"asset": "fox-cliff:action.leap", "start": 1, "end": 150}]
  }],
  "audio": {"asset": "fox-cliff:audio.leap"}
}
```

`compile` 消费完整 ID 引用镜头。完整显式路径镜头由 `check/build/render` 直接执行；同一镜头不混用两种引用形式。实例 ID、位置、片段时间由作品拥有；集合名、骨架名、Action 名来自资产清单。

## 版本锁

`lock PROJECT` 写入邻近 `project.lock.json`，记录引擎版本和分发源码摘要、项目与镜头摘要、包清单路径/修订/摘要、包的所有发布文件及风格材质库摘要，以及镜头默认风格。摘要使用 SHA-256。

锁对原始字节计算摘要，文本换行变化也会触发；仓库通过 `.gitattributes` 固定 LF。`compile` 发现漂移时失败并提示差异类别，不自动接纳。核对有意变更后再运行 `lock`。

临时 `compile --style <ID>` 可切换已锁定包中的画风，包文件已在锁内。CLI JSON 输出同时返回 `style_id` 与 `lock_sha256`，评审应与生成的两个 JSON 文件一起保存。

## 渲染 v1 与路径

文件型 v1 保留 `stage.file/collection/camera`、`actors[].file/collection/rig/clips`、`trails`、`audio`、`fps/frames/size/samples`。直接镜头的文件相对镜头 JSON，风格材质库相对风格 JSON；编译器输出本机绝对路径，避免工作目录变化影响执行。当前 `productions/fox-study/shots/010.legacy.json` 使用 `../../../assets/packs/fox-cliff/` 引用同仓资产。

帧从 1 开始，首尾均包含。片段须有序、位于镜头区间内且不重叠，完整源 Action 根据目标区间缩放。画幅必须为两个正偶数；`fps`、`frames`、`samples` 为正整数。空角色数组可表达环境镜头。

给相机与骨架设置稳定 `motionbase_id`，避免重复载入时名称后缀影响定位。引擎为实例写入 `motionbase_actor_id`，用于跨工程比较。材质用 `motionbase_role` 标记语义用途。

## 错误与比较报告

CLI 成功为 `0`，配置、执行、比较失败为 `1`，参数用法错误为 `2`。`compile` 成功只证明 Python 层契约与锁检查完成；`check` 会真正加载 Blender 资产。

`compare` 输出 `passed`、`frames_compared`、`max_matrix_delta`、`max_camera_delta`、`mismatch_count` 和最多 50 条 `mismatches`；`mismatches_truncated` 表示明细截断。报告包含前后路径、容差和帧定位。比较失败也写报告，调用方必须检查退出码或 `passed`。
