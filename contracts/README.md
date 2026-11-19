# MotionBase v1 数据契约

这里的五份 JSON Schema 使用 **Draft 2020-12**，均可独立加载，没有联网解析依赖。它们用于编辑器补全、宿主表单和静态输入校验。MotionBase 运行时使用标准库校验，安装 CLI 无需 `jsonschema`。

| Schema | 对象 | 使用位置 |
| --- | --- | --- |
| `shot-v1.schema.json` | 单镜头 | `shots/010.json` 或编译后的镜头 JSON |
| `style-v1.schema.json` | 画风、色板和可选材质库 | `--style` 或资产包的 style 项 |
| `pack-v1.schema.json` | 可复用资产及其稳定 ID | 资产包根目录的 `pack.json` |
| `project-v1.schema.json` | 作品使用的资产包、镜头和默认画风 | 作品根目录的 `project.json` |
| `project-lock-v1.schema.json` | 引擎和输入内容的精确指纹 | `motionbase lock` 生成的 `project.lock.json` |

## 镜头的两种输入

`shot-v1.schema.json` 的两个分支互斥，单个镜头必须采用完整的一种格式：

- **文件引用格式**：舞台包含 `file / collection / camera`，角色包含 `file / collection / rig`，Action 包含 `file / action`，音频为文件路径字符串。`check / build / render` 直接消费此格式，保留原 v1 镜头兼容性。
- **资产 ID 格式**：舞台、角色、Action、音频通过 `asset: "包ID:资产ID"` 引用。先锁定作品，再通过 `compile` 解析为文件引用格式。禁止在同一镜头混用两种格式。

镜头时序、画幅、角色实例 ID 和拖尾参数仍属于作品。`rig_id` 属于资产清单，用于判断角色和 Action 的绑定兼容性；它与 Blender 对象定位使用的 `motionbase_id` 职责不同。

## Schema 与运行时各自检查什么

Schema 检查字段形状、必需项、未知字段、字符串格式、常量、数组长度、数值范围和各资产种类所需的字段。它也约束输出画幅为正偶数，并排除零光照方向。

运行时额外检查这些依赖上下文的条件：

- 文件是否存在，包内路径及符号链接是否逃出资产包，镜头文件是否仍位于作品目录内。
- 资产 ID 是否存在、种类是否匹配、角色和 Action 的 `rig_id` 是否兼容。
- 角色实例 ID 是否重复，片段是否顺序排列、重叠或越过镜头边界，拖尾是否引用已声明角色。
- 作品锁与引擎源码、资产清单、镜头、画风、音频、`.blend` 文件及画风引用的材质库内容是否一致。
- 编译输出或其伴随的 `.style.json` 是否覆盖输入。
- Blender 集合、骨架、骨骼、Action 槽位及材质是否实际存在，并可按约定装配。

JSON Schema 的 `integer` 按数值语义判断，可能接受 JSON 字面量 `1.0`；运行时对版本、帧数、帧率等要求严格整数。同时，JSON 解析器拒绝重复键和 `NaN / Infinity`。通过 Schema 不代表镜头已经完成运行时检查，执行前仍需运行 `check`。

## 锁的含义

锁由工具生成。`project_sha256` 固定作品配置；`engine` 记录引擎版本和源码摘要；每个 `packs` 项固定清单和全部声明资产的摘要；`shots` 固定镜头内容和默认画风。资产包中的画风材质库即使没有单独声明为资产，也会纳入文件摘要。

`compile --style 包ID:画风ID` 允许使用已经锁定的资产包中的另一种画风。它不会改写作品镜头或锁，编译回执返回实际 `style_id`。新增或修改资产、镜头、引擎后，旧锁会明确失效；检查变更后重新运行 `lock` 接受新输入。

哈希用于检测输入漂移，不是签名或信任认证。外部资产的纹理等依赖应打包进 `.blend`，以便资产作为完整文件发布。
