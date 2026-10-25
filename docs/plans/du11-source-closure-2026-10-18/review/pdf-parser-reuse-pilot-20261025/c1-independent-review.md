# PDF-C1 独立终审

日期：2026-10-25。状态：**C1 源码/定向边界测试终审通过，0 OPEN**。原五项实质问题已修复；不代表 C2/Docling 生产、正式摘要、cache/RF 或主线 CI 完成。

## 审查范围与方法

源码为新阅读 owner、AUTO select/formats/replay/verify/runtime/generation/batch/worker_factory，以及指定三份测试文件。使用只读源码/diff、内存独立复现和一个有界定向测试包；不修改产品、配置、其他 PWF 或作者工区。没有网络、收费、重模型或原件访问。精确文件 SHA 和 LF 规范化 SHA 均绑定在同名 JSON。

## 问题与修复

| 问题 | 根因与最终修复 | 结论 |
|---|---|---|
| C1-R1 / P1 | PDF recipe 延迟解析；未使用 PDF 的 handler/runtime 不要求可选 PyMuPDF。TXT 材料按真实输入 MIME 分派，不因 DocumentStructure 默认值触发 PDF。 | 已修复 |
| C1-R2 / P2 | 同一绝对 deadline 从既有 worker 组合传至完整 backend，owner 取更严上限，读取前后检查；不重置时间，不把 15 秒细捕获当冷启动总额度。 | 已修复 |
| C1-R3 / P2 | 阅读 owner 递归验证无秘密/物理路径、有限紧凑 JSON，返回 detached 配方并拒绝运行漂移。 | 已修复 |
| C1-R4 / P1 | 旧已完成 PDF manifest 缺 recipe 时，只对 gen1/filing/PDF 的 completed-history 比较副本归一；原 manifest 不补签。pending 或其他字段漂移拒绝，调用方仍核 terminal/delivered/visible。 | 已修复 |
| C1-R5 / P2 | 既有返回身份校验加入每个 unit.source_id，不能在正确 DocumentStructure 外壳内混入异源成员。 | 已修复 |

R1、R3、R4、R5 均有本独审的实际内存复现，已提前通知 ROOT；ROOT 修复而非放松旧断言。R4 独立复算确认新增 parser_components 曾是唯一差异；最终七例检查确认 completed 兼容、pending/源 SHA/模型/非 PDF/非 filing 漂移拒绝，且旧 manifest 不变。

## 独立最终验证

- 初审现有边界测试：9 passed / 8.06 秒；外层 14.492 秒。
- 修复后定向包：15 passed / 2.69 秒；外层 4.845 秒、最长 90 秒未超时。审过的 12 份源码/测试在该运行前后 SHA 稳定。
- 独立历史比较：7 cases passed，旧 manifest 无 mutation。
- 自有 c1-independent-* 临时根恢复不存在；pytest 自动短路径重定位收据 removed=true，没有测试原件遗留。

ROOT 最终 `c1-real-owner-final-receipt.json` 已只读核验：三源五页 25+19+15=59 spans，最终 owner LF SHA 与本终审绑定一致，原基线 selection hashes 已从压缩证据独立复算相同；收据记录 59/59 同 owner 原文回放、保护文件不变及 0 付费/下载/原件副本。独审没有重新打开原件/SDK，实际执行仍由该收据负责。它只证明 C1 有限页原生接缝，不证明 C2/摘要/cache/RF。较早 R5 前版本收据不代签最终代码；ROOT 其他大包/CI 由各自收据负责，不把尚在运行项目写成已通过。

## 架构与兼容结论

同一阅读 owner 负责 recipe/read、内部旧版本重读策略、材料核对与 canonical replay；AUTO 不按工具名或 parser 函数对象决定输入。现代 callback 明确承担完整 native 契约，未用签名探测或 TypeError 重试猜参数。组合根给 select/verify 同一 owner，worker 从既有绝对截止字段组合，不新增 timer 库。

generation 保存阅读 owner 的不透明 recipe；新 PDF 运行绑定实际 native 依赖，当前 recipe 漂移拒绝恢复，不通过塞回旧 recipe 冒充当前。旧已完成且无 recipe 的 PDF 只被当作未知历史读取，不当作具备当前 recipe，不修改持久 generation；老 canonical 文本/坐标仍精确重放。缺原 runtime 时如实报错。

当前实现仍只启 native。无关已安装 Docling/MinerU 版本不污染纯 native 依赖；recipe 没有部署路径/密钥。没有新逐材料许可、常驻服务、第二状态库/缓存。后续 C2 的按需路由、模型资源、exact-native-member 闭包、正式摘要与 cache/RF 需各自实施和真实大节点验收，本轮不代签。

## 终审绑定

- `src/company_wiki/source_catalog/narrative_pdf_reading.py`：SHA-256 `0cca6da98f1eacd151880ffcdbded4b29b529b25c89508ca4f8635b826ff5ce1`；LF SHA `35c1685105d3196fbc16c6a53300d97eaa77e6e663d883785b7b3b132ff5ad9d`。
- `src/company_wiki/automation/narrative_select.py`：SHA-256 `2d94047d0c0ef25f7fdd5ac2609f7ff5f049812431121596cc6ca73819da958e`；LF SHA `d061f3da73b86fff38718021d6be7578b27eb0eb0de1376fbd96117fcb7b8bd3`。
- `src/company_wiki/automation/narrative_formats.py`：SHA-256 `867112ca0727b70606090e220e70094e920458ac72918ff7e2271817a4e8ed23`；LF SHA `343ed1a234462d74fbf8adad77371561efadc20591f9faee5504be7406cbd5bb`。
- `src/company_wiki/automation/narrative_replay.py`：SHA-256 `cc04b5fd590a6d4869e561e6a2392070d261fe4f0b6697d9774816207e0f6188`；LF SHA `860a20a2b972493c382e99634734fc5ec5229100bdc316034566e9bdabc2fcd5`。
- `src/company_wiki/automation/narrative_verify.py`：SHA-256 `40b567cbb82fc0c45dc2fb6613cf9832ee93848e43c0f3fca4ac7cae2498fc72`；LF SHA `8261e6612cb2f09c0d3897dbb23b1f7e4cc47716ab786760eeb36b18ff50a282`。
- `src/company_wiki/automation/narrative_runtime.py`：SHA-256 `3e57cad260b4380c1ba0d1e3e1e6a7b07c4c8f607a8c2d80c80da99061e80241`；LF SHA `10a83e5c1abadd4f99548a037222e2df097e080bb027e4a6217e70109bc514a1`。
- `src/company_wiki/automation/narrative_generation.py`：SHA-256 `814da224b82a042bf6b387116ac47b87831ee07a8cce6b26a152021786e5d466`；LF SHA `7f094cd1603b7f71032d54c08f97cd3e40d329bf0cdd1530a1f175c16f2133a1`。
- `src/company_wiki/automation/narrative_batch.py`：SHA-256 `773ccb3e3b0f3b6139ab79ed2fefaddf5fe1eda85eaa50cb325029f17918e7af`；LF SHA `97d319c20a4658bdc2edd4d12c22381e6b5791a311727d7ba3d1167ec72998d4`。
- `src/company_wiki/automation/narrative_worker_factory.py`：SHA-256 `4681407f24674f78c4f5af0740cc05b06c5636652adcb7979fc80b9ea2885b7d`；LF SHA `af27f2b2cd12fc8e73987d935ac609eb392b0063ffe58786f4338f36487e6b50`。
- `tests/unit/test_pdf_reading_boundary.py`：SHA-256 `486fa592456095dc61fd6ba88d25b25acb4dc41e672218befb2e56902d888a54`；LF SHA `8c619e9ba6fcd634a53742cd4db8f2311272f2a212967c1abee8c52a28605d26`。
- `tests/unit/du11_production/test_pdf_production.py`：SHA-256 `98d8a42d40b1de2ecaf3670ae213053dde353734ef3c38347449661c143f739e`；LF SHA `ea0dae614692273fd88318ef0833ddfe4968cd4dcb08603b55691065ac7e355f`。
- `tests/unit/test_shared_reading_pdf_layout.py`：SHA-256 `16ae4d21649fe2b5f1acda8139bc6c8805b7c5b09d823012f603bdf5f4c8e717`；LF SHA `a7035a5ed5faddcd02064b5f70924c380b5c4181738d0c0040583ffc9a2dbe61`。

## 发布前测试夹具可移植性补正

只读核对正常 pre-commit 发现的 host 路径夹具修正：`test_owner_rejects_secret_and_physical_location_recipe_fields` 接收 pytest `tmp_path`，`model_path` 改为 `str(tmp_path / "model")`；原 ValueError 拒绝断言及其他 case 不变。这使真实绝对测试路径由运行环境生成，不在代码写死 Windows 主机路径。全部产品源码绑定均未变，只有该测试 SHA 已刷新；ROOT 报告 host-neutral 定向 15 passed / 3.08 秒，独审按要求没有重跑全工程。此补正审查 **0 OPEN**。
