# DU4-FORM：源观察的表单事实与发言轮次信号

状态 READY，2026-10-15。范围是纯信号组件；主线负责把它接入一次原生解析与唯一 router。

## 开工入口与独占范围

- 工作目录：`C:/Users/郑曾波/Projects/company-wiki-du4-form`。
- 分支：`codex/du4-form-20261015`；基线 `8206e78d4087531b1d7ed57c45a73c942cc702e3`。
- PWF：`docs/plans/du4-form-2026-10-15/`，阅读本卡、INTERFACES.md 和 references/source_form_route_implementation.md。
- **只写** `src/company_wiki/document_understanding/source_signals/**`、`tests/unit/du4_source_signals/**`、本 PWF。
- 不修改 HTML parser、document/normalization adapter、source_contract、profiles、router、vocabulary、pipeline、模型/缓存或总 PWF。旧参考里的直接跨层施工由 ROOT 做，**本卡目录边界优先**。不得在新包里复制现有 router。

## 实际错误与素材

真实 VRSK SEC 10-Q 含可见 `FORM 10-Q` 和 `dei:DocumentType`，但是短表单载体未进入有界 probe；财务表 `Revenues:` 又被当作 speaker，最终误判 earnings_call。已保存的反事实路由能改成 sec_10q，但把 cover fallback IDs 当表单证据，仍不是真正 provenance 修复。

本 PWF 真实保存夹具：

- `fixtures/us-10q-observation.json`：以前真实 parse/select 的来源指纹、旧错误路由、原 DEI 字节节选等。并非完整 native corpus。
- `fixtures/adapter-identity-observation.json`：原 `Revenues:` unit 身份重算匹配，native kind/table locator、company_filing role，及旧 router 丢失的字段观察。
- 其他 named prose、attributed table turns、8-K 附件等用例是**合成控制**，不得冒充原件。

## 实施目标

按公共 `collect_source_signals` 实现 bounded pure collector：

1. 输入已经观察到的 native carrier，不读取文件、不 parse DOM、不扫描全文、不访问 provider。DOM 层后续由 ROOT 在现有一次遍历产生该 carrier。
2. 可见 DEI/自身 FORM heading 的字面值与真实 unit refs 成为 scoped form evidence；保留原始值。声明性 form_type、文件名、source.title 只可冲突诊断，不能造 observed。
3. 保留 parent/attachment scope：子附件表单不能覆盖主文件，8-K 容器与 10-K/电话会附件不能揉成同一个事实。未知、冲突、截断真实报告。
4. 原生 speaker/turn association 是正证据；冒号/大写形状只是候选。任意财务标签或 caption 不能凭正则进入 turn evidence；真实 table-shaped 逐人发言也不能被 blanket table filter 排除。
5. 输出 reserved_unit_ids，供 ROOT 在原 200 units/64000 chars 内预留载体；本组件不提高预算、不执行第二次 router、不绕过不足诊断。小于载体所需预算时 partial，不假称读到。

不需增加权限、人工 review receipt、签收状态或公司身份重查。raw source identity/locators 已由所属层负责，本组件只验证自身收到的 refs/parent/载体关系。

## A：反例与 RED

至少覆盖：

- 真实九字符 FORM、可见 inline DEI；合成 fourth-unit/大量前导普通单元，输出真实 carrier refs 而非封面候补。
- 10-Q/10-Q/A、10-K、20-F、40-F、8-K、6-K、S-1/F-1 等字面值；**观察不是 family 分类**，未见格式保留未知事实与诊断，不堆公司条件。
- 同 owner inline 包裹、分属不同 owner 的分词不能随意串接；hidden/excluded/external linked DEI 不伪装成可见事实。
- 声明 quarterly、正文无 observed carrier；声明与真实值冲突；多个同/不同 parent 值冲突；不存在的 carrier 不能借 cover IDs。
- `Revenues:`、`Headcount:`、`Utilization:` 等任意标签负控，禁止词黑名单；真实具正文的 CFO/operator/analyst turn、原生 attributed table turns 正控。
- prepared remarks 不伪造 Q/A；修辞问句不自动当 investor question；跨 parent/turn_id 不配对。
- refs 越界、输入不变、零/少预算、重复载体、确定性、大数据计费。

保存模块具备接口骨架之后的真实语义 RED，而非只有 import 失败。

## B：集中验证

单测/契约测试、Ruff、mypy。真实观察 fixture→组件输出保留精确 native IDs 与位置。构建一个小的合成 carrier 流装配测试，验证输入到信号完整过程；明确这不是 native parser/生产 route 端到端验收。

特别检查：没有隐藏全文扫描、没有第二家族路由、没有正则 colon 即 speaker 的退路、没有压倒真实父子范围的 metadata 优先规则。已观察 carrier 数量/字符/work 都诚实报告。

## C：交付与 ROOT 后续

按公共 handoff 提交分支、测试结果、接口实例及未测范围，STOP。列出 ROOT 所需最小 glue：一次 HTML walk 采集 carrier → surviving native structure → adapter → 本组件 → 现有 profile 的预算内预留与唯一 arbitration；剥离 transient reading metadata，保持旧 durable spans/ID/wire。

ROOT 负责真正的 normalize→structure→router→selector E2E，以及 VRSK 原件与另一家公司/真实 transcript/8-K 附件 holdout。缺真实材料就写 NOT_EVALUATED，不用合成绿冒充。不要越界编辑这些既有文件来提前接线。
