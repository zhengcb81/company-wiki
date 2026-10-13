# DU-STRUCTURE — 跨页章节与语义单元

状态：READY，可与PROFILES/BENCH同时开工。

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/structure`
分支：`codex/du-structure-20261013`
仓库：company-wiki。

## 上下文和任务

读取AGENTS以及本计划README/design/INTERFACES/implementation。维护自己的`.planning/du-structure/{task_plan,findings,progress}.md`（PLAN_ID=du-structure，PWF_PLAN_ROOT=<本worktree>/.planning）。实现纯函数`build_structure`，把既有locator单位组织成章节/语义unit/关系；不改生产解析器、不重做PDF读取、不接LLM。现有W04句子/主体完整性不能破坏。

## 独占范围

- `src/company_wiki/document_understanding/structure/**`
- `tests/unit/document_understanding_structure/**`
- `tests/fixtures/document_understanding_structure/**`
- `.planning/du-structure/**`

不创建父包init、不修改profiles/benchmark、现有source_catalog或document_normalization。若现有parser缺heading/bbox/table字段，记录需ROOT补的适配，不越界修parser。无新增依赖，不动CI/安装副本。

## 实施步骤

1. 冻结du-input/1→du-structure/1示例并写RED：目录与正文同标题；page62末项目建设期续63；两项目相邻、一个项目多小节；双语双栏；题目在前页答案在后页；业务表单位/年份/脚注；扫描缺页。
2. 构建章节栈与正文序列，显式处理TOC/重复页眉、已有heading_level/DOM与PDF布局。跨页延续有上限，遇新同级章节停止；不因页换就清空项目上下文。
3. 构建六类语义单元及关系。项目按主体+属性形成可预算的小包，table行依赖表头/单位/期间，QA分离角色并保持完整条件与否定。普通段落语义不明时返回background/unknown，不编因果。
4. 处理左右栏语言lane；仅有真实排版/文本对应证据才输出language_parallel。不得把双语翻译成新文字，不能用语言对齐删掉source units。
5. 对超过max_group_members/工作预算/缺上文/缺页作partial及deferred。引用都必须存在、顺序稳定、无无限依赖环、无来源交叉。结构complete仅表示构建过程，不代表业务召回或正确判断。
6. 无需自己做经营指标选择/模型摘要。向ROOT提供语义关系，ROOT用profiles和现有budget选择。

## A/B/C节点与测试

- A：上述反例及wire RED；先锁住跨页/角色/单位完整性。
- B：集中unit通过，纯函数不修改input；规模夹具1k/10k units记录趋势，避免N²；人工构造bad layout不能硬标high。
- C：用计划中名创双栏、恒锋跨页、万润QA的少量真实规范化单位复核；保留来源locators与摘录≤8KiB/文档，不复制原件；交接范围检查。

命令：`python -X utf8 -m pytest tests/unit/document_understanding_structure -q`；本包ruff。基准耗时作为大节点诊断，不加脆弱毫秒级CI断言。缺原件不标PASS，用合成覆盖和UNAVAILABLE区分。

验收：跨页项目不丢主体、计划/实际未混写，QA中的管理层否定保留；双栏/表头不串；输出引用可由原source replay；没有新增文件读写、权限流程、任务库或模型调用。

## 交接

`.planning/du-structure/handoff.{md,json}`按INTERFACES第7节。列出布局依赖、partial条件、性能趋势、真实/合成覆盖、哪些属于ROOT adapter工作。实现commit留本分支；不合主线，不触碰其余作者在制目录。
