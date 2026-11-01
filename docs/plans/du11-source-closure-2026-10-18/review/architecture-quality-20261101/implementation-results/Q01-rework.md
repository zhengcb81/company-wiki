# Q01 独审返修 — READY，待 ROOT 独立复审

本线基线为 ROOT 的未提交 A 节点及 `independent-A.md` 的 A-01。只实施来源可读句法与其包内资源，不改主 PWF/Git 索引、原件、生产配置、封存或收费模型。当前 source/grammar 已冻结，ROOT 可安排集中复审。

## 根因与最终责任边界

原有限动词线索会漏未知行业，ROOT 第一轮“第一人称前缀＋长度”又把名词片段放行。它不是独立陈述语法，不能靠增加公司/行业词或词数阈值解决。

已完整撤回该 `_subject_led_statement`、人称词数/字数兜底和 ROOT 新增 CN aspect 正则。通用 fallback 现在调用独立 `document_understanding.statement_grammar` owner：

- 英文复用固定 NLTK Perceptron POS 模型，以 nominal subject→matrix finite predicate 判定，处理开头 proper-NP 的中性语法重标，防专名词形改变下一词标注；不替换原文或赋予 issuer 身份。介词期次、相对结构和标题式名字不借分词/法律后缀冒充独立谓词。
- 中文复用固定 jieba 的通用分词词典及 POS 标签，HMM=False，识别名词主体、动词/形容谓语、状语和定语/并列边界；复用既有 COMPOUND_HEAD 的名词化边界。没有公司名称、证券代码、业务领域或页码分支。
- 既有 typed relation/event/measurement proof 保留快速路径；新语法仅说明原话可读，不能升级上述 proof。更新的变形测试将 fact 与原 `project_reading_business_fact` 对照，避免“新函数和自己比较”。
- 原文、source IDs、locator、句子限定仍由现有 owner 保持。原 abstract argument owner 的通用模态/标点兼容沿用 ROOT 改动；未新增第二个业务词典。

## 实际文件

- 新 `src/company_wiki/document_understanding/statement_grammar/__init__.py` 及其 `resources/`。
- `narrative_source_passage.py` 接入语法 owner、保留 unavailable/scope-limit 未知原因；policy 为 `source-passage/4`。
- `narrative_business_policy.py` 的 assessment 和 `narrative_operating_relations.py::fact` 仅窄透传现有 `WorkBudget`。
- `test_source_readability_generalization.py` 44项；新 `test_statement_grammar_runtime.py` 11项。
- `pyproject.toml` / `requirements.txt` 固定依赖并声明 package-data，mypy 仅增加这两个无 stub 库的边界；`.gitattributes` 对资源目录 `-text`，防 Windows 换行破坏实际模型字节。

ROOT 已另将 `resource_identity()` 接入 reading recipe；本线不覆盖 ROOT 对 PDF 表格观测算法的修复。该函数计算实际四个资源 SHA＋实际安装的两个推理包版本＋grammar schema，独立于某家公司。

## 资源、许可证与环境

常驻项目资源新增 **10,775,669 B**：NLTK 三 JSON 共5,703,817 B，jieba词典5,071,852 B；加少量 manifest/MIT 许可/下载记录。它是每个安装一份的语言资源，不按公司、文档或 run 复制。

- 官方 NLTK [模型元数据](https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/taggers/averaged_perceptron_tagger_eng.xml) 明确 MIT；实际公开 ZIP 1,539,115 B，ZIP SHA 和文件 SHA 在包内 observation/manifest，ZIP 只在内存解压，未落盘。
- [NLTK 上游 API](https://www.nltk.org/api/nltk.tag.perceptron.html) 支持 `load=False` 加显式 JSON；本线始终读取包内 JSON，不调用 `nltk.download` 或系统 NLTK 数据目录。
- [jieba 上游](https://github.com/fxsjy/jieba)及 [MIT 许可](https://raw.githubusercontent.com/fxsjy/jieba/master/LICENSE)；本地 bundled 词典随 wheel 发布。使用公开 Tokenizer，从包内词典在内存建频率表，不调用其临时词典 cache、不加载未使用的 HMM/Paddle。
- 先按官方 API 对照窄装 NLTK3.9.2 时发现宿主原为3.10.3，已按 ROOT 指令恢复原 **3.10.3**；同一 JSON 在该原版本通过。项目固定 `nltk==3.10.3`、`jieba==0.42.1`，不依赖“本机碰巧有”。全局 pip cache 保留；无 ACL/标签改动。

NLTK/jieba 都不接触用户网络资料；本线无用户材料外发、LLM POST、token/费用账改变。

## 有界与成本

- 实际 fallback 前在同一 WorkBudget 预扣 `32 * len(clause) + 1`；32是明确的保守逻辑系数，不宣称等于 CPU 指令数。已知语法/typed proof 不运行 POS、不重复收费。
- grammar 观察上限 **4096字符 / 1024 tokens**。超界返回明确 `unknown / statement_grammar_scope_limit`，不截短材料或伪称支持；缺依赖/缺资源/manifest异常为 `unknown / statement_grammar_unavailable`。
- `WorkBudgetExceeded` 由原 SourceOperatingSession catch 转 partial，预算耗尽前不执行模型；重复访问不重新扫描、收费或构造无预算 fallback。原 **16M/112** 配置上限未变；真实 source select 可能更早 partial，必须由 C 节点观察，不能调高额度补齐。
- 普通 fresh 进程首用两语种 **7.13s**；warm 两短句 median **0.558ms**、max **1.614ms**。RSS 从61.5MB到334.4MB，delta272.9MB，包含库 imports、Python词典和权重对象，**不隐瞒常驻内存成本**。固定冷装开销归现有 worker 进程/时间边界；该测量是诊断，不设抖动时间门。
- 先前 tracemalloc 内存探针显著拖慢初始化到37.68s，不能冒充正常冷装时间。正式 RSS/时间收据见 `Q01-runtime.json`。

## RED / GREEN 与清理

1. 首先补独审人称/专名/名词片段及其他跨行业变形：原不足方案 **10F/28P**。
2. 初次 POS 组合 **125P/5F**，共同问题为名词化/列举、期次介词、标题式名字、中文持续＋形容谓语。修通用边界后 **130P/11.69s**（不是公司补丁）。
3. 最终语法/预算/离线组 **55P/26.10s**；final旧passage/binding/runtime/dependency组 **100P/18.08s**，两组runtime11有重叠；Fact 对照改成旧 owner 后，仅相应15项复验 **15P/7.98s**。不把这些相加成唯一测试数。
4. Ruff通过，mypy四个源模块通过，dependency parity通过。未跑整仓、模型摘要或实际RF新attempt；本线自测不替集中独审。
5. `q01_packaging_probe.py` 只复制代码到独占短目录，offline构建 wheel、核四资源 SHA/两 MIT、移位 fresh Python 英中推理通过。最终 wheel5,197,050 B，收据 `Q01-wheel.json`；整个独占临时树恢复 absent。首个临时构建仅 pip 日志 OEM/UTF-8 解码警告，资源和真实入口仍通过；最终脚本显式UTF-8重跑，无该警告。没复制财报/DB/完整备份，也没执行恢复备份演练。
6. 现有 jieba/pkg_resources 发出两条弃用警告，未当成测试失败或静默隐藏；库已有无 pkg_resources 的 fallback，未为它增加额外 setuptools 门禁。

可复跑（CWP cwd，宿主Python，PYTHONPATH=src;tests）：

```text
python -B -X utf8 -m pytest -p pytest_asyncio.plugin tests/unit/du11_production/test_source_readability_generalization.py tests/unit/du11_production/test_statement_grammar_runtime.py -q -p no:cacheprovider
python -B -X utf8 -m pytest -p pytest_asyncio.plugin tests/unit/du11_production/test_source_passage_admission.py tests/unit/du11_production/test_source_information_binding.py tests/unit/du11_production/test_statement_grammar_runtime.py tests/unit/test_runtime_dependencies.py -q -p no:cacheprovider
python -B -X utf8 docs/plans/du11-source-closure-2026-10-18/review/architecture-quality-20261101/implementation-results/q01_packaging_probe.py
```

## 验收边界

POS＋句法包络不是完整依存解析器，不保证任意语言/复杂省略句完美分类；未知保持未知。它解决独审中的明确名词片段/同义人称问题，并保留现有负例，不以训练词典存在证明业务事实。本线没有完成真实全年报/摘要/RF采用验收，也不证明当前原公司三个目标已实际全部入选——目前只证明真实三 unit 经过新 prepared owner 可读且 bounded。ROOT 应独审这份最终实现，再在 C 节点用原材料/预算和真实缓存入口检查。
