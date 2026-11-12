# MB-CWP 进度

工区 `C:/Users/郑曾波/Projects/mb11-cwp`，分支 `codex/mb11-cwp`，基线 `08dfe8bf1`。

## 提交序列（2026-11-12）

| Commit | 内容 | 关键证据 |
|---|---|---|
| `0956148bd` | CWP-01/02/03：source_contract 直连、normalization 注入（撤 `from_reader` 反查）、work budget 工厂注入 | `test_module_owner_isolation` 9、`test_work_budget_injection` 7、`test_transport_normalization_injection` 4 |
| `f32fbabf8` | CWP-04 安装验收（wheel→venv→13 入口→包内资源→site-packages 身份）+ 中立模型 owned/borrowed 快照 + T-READ stream CLI | `test_installed_public_entrypoints` 6、`test_source_stream_cli` 6、identity +2 |
| `be85d9ddc` | T-CONFIG 严格类型 8 反例 + T-B34 诊断/IPO 封面 33 测试 + cn_primary_issuer 12 测试 | 72 + 33 + 12 |
| `eda1f4f9b` | T-CANON canonical browser 全套 + document browser 3 个 typed-port 有界枚举 | 101（60+9+20+12） |
| `566f4cc23` | T-B33 readiness/link/recovery 六模块 + owner 级 pair 精确读取（4 处）+ exact_history 9 测试 | 118 + 45 + 259/119/82 回归 |

diff 规模：61 文件，+10247 / −47（对基线 `08dfe8bf1`）。

## A0 六子项

全部关闭，处置与证据见 findings.md「A0 逐项处置」表；非 primary 读取的 owner 级根因与四处改动见同文件专节。

## 未执行/移交

- 真实多文种本地组合（E01–E09）：ROOT 承担，按卡不属本卡。
- 完整 CI 远端核验：ROOT 在集成后执行。
- `tests/integration/test_source_processing_handler_wire.py` 基线既有失败（`_versions` 未定义名）：非本卡写集合，列给 ROOT（见 findings「其他发现」）。
- 提交钩子 Mimosa L3 对基线文件的拦截：以正式封印扫描（3 次，均 137 项与基线一致、本卡 diff 零新增）+ 证据说明放行；未改写命令。
