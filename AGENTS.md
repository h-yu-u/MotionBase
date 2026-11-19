# Working on MotionBase

Read `README.md` and `docs/architecture.zh-CN.md` before changing the execution boundary.

## Ownership

- Keep `motionbase/` reusable. It owns contracts, asset resolution, project locks, Blender orchestration and generic checks.
- Keep reusable art and its generators in the independent asset checkout, normally `../motionbase-assets/`. The `assets` branch of this repository currently hosts that checkout.
- Keep accepted creative intent, shot timing, selected styles, local variants and review history in the production workspace.
- Keep project Skills in `skills/`, alongside the engine version whose CLI they call. A repository skill is not automatically installed in a user's client.

## Implementation

- Preserve the existing `check/build/render SHOT --style STYLE` interface for file-based v1 inputs. Project compilation emits that contract.
- Do not import `bpy` from the CLI, configuration, project or asset modules. Run Blender in an isolated process with scripts disabled by default.
- Resolve paths relative to the document that owns them. Packs are self-contained; do not depend on the current working directory or silently search another pack.
- Reject incompatible rig identifiers, unknown fields and stale locks explicitly. Use observed asset names and schema fields.
- Keep deterministic checks in code, creative judgment in Skills, and asset-specific checks with their asset pack.
- Update the schema, documentation and meaningful boundary tests together when changing a contract. Update the sample lock after an intentional engine/input change.
- Preserve motion and framing when changing only a look. Use `compare` and inspect a preview; these prove different things.

## Validation

Run `python3 -m unittest discover -s tests -v` for configuration/compiler/CLI changes. For Blender runtime changes, also run the generic integration fixture in `tests/integration/runtime_contract.py` using Blender 4.5 LTS. Render changes additionally require the small `tests/render_smoke.py` end-to-end test with FFmpeg/FFprobe. Run the external pack's own tests when changing its files.

Keep generated frames, Blender projects, videos, reports and logs in ignored `build/` directories. Commit source and intentionally reviewed records. Do not rewrite unrelated branches or overwrite asset inputs with generated outputs.
