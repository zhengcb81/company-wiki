# DOCX 标题解析共因包实施交接

封存时间：2026-10-11T02:19:35.496604+00:00。实施源/测试已停止写入；ROOT 接统一公共验收、独立补充复核及正常发布。

## 变更与责任

DOCX 默认 parser_version 为 `1.1.0`，`normalization_identity`、单位身份及 NarrativeNormalization identity/normalize/replay 使用所属格式版本。显式 `1.0.0` 仍走原解析路径，不读取 styles，也不加入标题 metadata。HTML 只允许 `1.0.0`；PPTX 仍维持原 `1.0.0`/`1.1.0`/OCR `2.0.0` 集合。

`word/styles.xml` 经既有 ZIP/XML 资源限制和禁止外部关系路径读取；真实 paragraph style 的 `basedOn`、默认 paragraph style、document defaults 及 `w:pPr/w:outlineLvl` 按层级解析。显式 outline `9` 覆盖继承并输出正文。继承最多 128 层，有 deadline 检查及循环诊断；有限 style metadata 最多 256 字符，异常导致显式 extraction diagnostics。仅真实 outline `0..8` 输出 `docx_heading`，`heading_level=outline+1`，标题文案/字体不用于推断。

标题仍保留物理 `p` 原定位，正文和 table 物理遍历不重排；table 内标题 style 保持 `docx_table_cell`。Q/A、source_role、原文、旧字节 SHA 校验及 replay 的完整 metadata/locator 比较保留。ROOT 已拥有 generic strict `0.7.1` heading barrier，本 agent 未写其两源码或 native/public 既有测试。

## 先 RED 后 GREEN

- 实现前 `red.log`：新真实 DOCX 17 项，11 FAIL / 6 PASS；涵盖 builtin Heading 1、继承、direct outline/body override、styles diagnostics、新默认版本及跨标题 group 负控。旧 `1.0.0` 指纹/replay 已 PASS。源码 before SHA 在 `before.json`。初次日志路径编码说明见 `after.json`；pytest 的真实 exit 为 1，未重跑 RED。
- 集中 `green-focused.log`：104 PASS / 3.32s。新 DOCX 17、既有 DOCX 20、MAIN OCR identity/replay 43、OCR composition 24，未调用 provider/model。
- 补类型后的最终 DOCX `green-final-docx.log`：37 PASS / 0.58s，真实源码 SHA 对应下表。只重复改动责任项。
- `ruff-final.log`：六文件全部 PASS。`mypy-final.log`：四源码 PASS；命令显式排除 `import-untyped`，环境缺 `lxml-stubs`，没有安装或忽略本体类型错误。原始 mypy 失败日志保留。
- 独立审查原反例 `../independent-review/docx_heading_minimal.docx` SHA `c29c7c0d1a40da78cdf6215bb9675f27773b461af49d71f8e1877136d944702c`，现实际默认输出 `docx_heading`、style `Heading1`、heading_level 1、定位 `cwp-docx-body/1|p=1`，全部单位 exact replay，strict `0.7.1` 未再加入该标题 context。结果在 `after.json`。
- 新真实继承/override 组合 `style-inheritance-override.docx` SHA `f98f852a2e497073effdcef7da41241e53b3ab7a2700c4134ff56e91a5cdb5c2`，输出 heading + body。伪造 heading metadata 的 replay 拒绝也记录在 `after.json`。

## 冻结旧解析与字节定位

`legacy-original.docx` SHA `d428ad041147fb650671ee805c38a03539b4f28529a5516bce325cc3a8541761`；完整 document/单位字段、metadata、identity、kind、角色和 locator 的旧指纹 `a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4`，before 与 after JSON 严格相等，6 个单位全部 exact replay。新 `1.1.0` 的 6 单位同样全部 exact replay，指纹 `584394a3f8bc6f5d2067d9fdfecc968beb4edd29cf62e51445cefd81bf1684ed`，new/old unit IDs 全部分离。saved `document_id` 的 old pin 仍为 `1.0.0`。

## 最终源码与测试 SHA256

| 文件 | SHA256 |
|---|---|
| `src/company_wiki/document_normalization/docx_parser.py` | `319b6108d27cdde262ab272f2c7b34965c2ca55228ce01d11a3bbb13fea01fbe` |
| `src/company_wiki/document_normalization/units.py` | `f7b88241228dffd689aec0f1a00184ccdf5a6cd4636a641f423856366f4299d9` |
| `src/company_wiki/document_normalization/__init__.py` | `1eb702537c9d5d18959325fff4a3a3d139084caa6de9ef6b50c7af2083db42cf` |
| `src/company_wiki/source_catalog/narrative_normalization.py` | `69f0e220cbb860863ab790d137dec532096b85652ad93420f66dbcb4d844d114` |
| `tests/document_normalization/test_docx.py` | `e69b0c6d276d1eb8279c5f8e6fce0f3082ab3d516f7fe8dbfe7f8b999a2ee0b6` |
| `tests/unit/test_docx_heading_normalization.py` | `ea74c6439ecba14f798a743b0748ed75f47659d52077ae84b6322bd0d217e888` |

## ROOT 余下门槛

ROOT 负责最终统一 native/public pipeline、真实 batch generation/cache 新旧隔离及公共重放集中节点；ROOT 已知 native_pipeline current DOCX 断言需改为真实常量。`automation/narrative_replay.py:129` 实际只验证 parser_name，version 经 parser_component → NarrativeNormalization.identity，因此本次新 DOCX 合法接线自然贯通，不需要额外放宽 literal validator。

独立补充复核最小原反例和新继承/override 组合后，ROOT 执行正常发布与精确新 HEAD CI。本交接不声称已完成这三个门槛。0 provider / 0 model / 0 新费；未改生产 config、三次真实 executor seal、原运行预算、Dayu、邻仓；未 commit/push。

CodeGraph 已先查，canonical 旧索引只返回 parser CLI，没有本责任新模块；按已确认缺口回到具体源阅读，没有初始化索引。收尾只读 Git status 显示本责任五个 tracked 修改及一个新测试，`config/source_catalog.yaml` 无变更。Git 在 workspace sandbox 的只读命令报 worktree 不可用；授权外部 tree 的 require_escalated 只读检查成功，diff 和 status 未发现超范围责任编辑。
