# LLM 集成改进计划 (v2.0)

> 基于 Karpathy LLM Wiki 对比分析 + 项目现状深度审查
> 目标: 从 30% LLM 集成度提升到 90%+
> 最后更新: 2026-04-18

---

## 一、项目现状 vs Karpathy LLM Wiki 对比

### Karpathy 核心架构 (三层)

| 层次 | Karpathy 定义 | 本项目现状 | 完成度 |
|------|-------------|-----------|--------|
| Raw sources | 不可变原始文档 | ✅ `companies/{name}/raw/` + PDF | 90% |
| Wiki | LLM 拥有的 markdown 页面 | ✅ `companies/{name}/wiki/` | 60% |
| Schema | CLAUDE.md 指导 LLM 行为 | ✅ CLAUDE.md 存在 | 70% |

### Karpathy 核心操作

| 操作 | Karpathy 定义 | 本项目现状 | 完成度 |
|------|-------------|-----------|--------|
| **Ingest** | 读源→讨论→写摘要→更新实体/概念页→更新索引→记日志 | ingest.py 规则提取 + ingest_with_llm.py LLM提取, 但缺少跨页面更新 | 60% |
| **Query** | 搜索→读取→综合→可选存回wiki | query.py 纯关键词搜索, 无LLM, 无存回 | 20% |
| **Lint** | 矛盾/过时/孤儿/缺失/交叉引用检查 | lint.py 规则检查, contradiction_detector.py 模式匹配, 无LLM | 40% |

### 关键差距分析

| # | 差距 | 严重度 | 当前状态 |
|---|------|--------|---------|
| 1 | **无 wikilinks 交叉引用** | 🔴 关键 | wiki 页面间无 `[[链接]]`, 信息孤岛 |
| 2 | **LLM 客户端碎片化** | 🔴 关键 | 3个不同脚本各自调用 LLM (ingest_with_llm/refine/llm_ingest) |
| 3 | **Query 无 LLM 综合** | 🔴 关键 | query.py 纯规则搜索, 无智能答案生成 |
| 4 | **Query 答案不存回** | 🟡 重要 | Karpathy 核心理念: 好答案变成新wiki页面 |
| 5 | **Wiki 页面是文档堆砌** | 🟡 重要 | 时间线条目是原文摘录, 非LLM提炼的知识 |
| 6 | **综合评估全部空白** | 🟡 重要 | 所有页面评估="待积累数据后补充" |
| 7 | **核心问题未设定** | 🟡 重要 | 所有页面核心问题="(待设定)" |
| 8 | **Lint 无 LLM 能力** | 🟢 改进 | 语义矛盾/缺失概念需要 LLM |
| 9 | **无 Obsidian 优化** | 🟢 改进 | 缺少 Dataview 兼容 frontmatter, 图谱视图优化 |
| 10 | **无 Ingest 跨页更新** | 🟡 重要 | 一条新闻应同时更新公司wiki + 行业wiki + 主题wiki |

---

## 二、LLM 集成现状审计

### 当前 LLM 调用点

| 文件 | LLM 用途 | Provider | 问题 |
|------|---------|----------|------|
| `ingest_with_llm.py` | 内容提取+实体识别 | DeepSeek (OpenAI SDK) | 独立实现, 无统一客户端 |
| `refine.py` | 摘要精炼 | DeepSeek (urllib直接调用) | 硬编码 URL, 另一套实现 |
| `llm_ingest.py` | 完整分析+时间线生成 | DeepSeek (urllib直接调用) | 第三套实现, 功能重叠 |
| `query.py` | ❌ 无 LLM | - | 纯关键词搜索 |
| `lint.py` | ❌ 无 LLM | - | 纯规则检查 |
| `contradiction_detector.py` | ❌ 无 LLM | - | 纯模式匹配 |

### 问题总结

1. **3套独立的 LLM 调用代码**, 无共享客户端
2. **2种不同的 HTTP 调用方式** (OpenAI SDK vs urllib)
3. **无统一的重试/限流/错误处理**
4. **无统一的 prompt 管理**
5. **关键模块 (query/lint) 完全没有 LLM 能力**

---

## 三、详细实施计划

### Phase 1: 统一 LLM 客户端 (P0 - 基础设施)

**目标**: 创建统一 LLM 客户端, 消除碎片化

#### Step 1.1: 创建 `scripts/llm_client.py`

```python
# 统一 LLM 客户端设计
class LLMClient:
    """统一 LLM 客户端, 从 config.yaml 读取配置"""

    def __init__(self, config_path="config.yaml"): ...

    # 核心方法
    def chat(self, system: str, user: str, json_mode: bool = False) -> str
    def chat_with_retry(self, system: str, user: str, max_retries: int = 3) -> str

    # 业务方法 (封装常用 prompt)
    def analyze_content(self, content: str, entity: str) -> dict
    def generate_summary(self, content: str, topic: str) -> str
    def detect_contradictions(self, page1: str, page2: str) -> list
    def generate_wikilinks(self, content: str, available_pages: list) -> list
    def synthesize_assessment(self, timeline_entries: list, topic: str) -> str
    def generate_core_questions(self, entity: str, sector: str) -> list
    def answer_query(self, query: str, relevant_pages: list) -> str
    def lint_page(self, page_content: str, all_pages_index: str) -> list
```

**配置** (config.yaml 扩展):
```yaml
llm:
  provider: "deepseek"         # deepseek / openai / anthropic
  api_key_env: "DEEPSEEK_API_KEY"
  model: "deepseek-reasoner"
  base_url: "https://api.deepseek.com"
  max_tokens: 2048
  temperature: 0.3
  rate_limit_rpm: 30           # 每分钟请求限制
  retry:
    max_retries: 3
    backoff_base: 2            # 指数退避基数(秒)
    timeout: 60
```

**验收标准**:
- [ ] 统一 LLM 客户端文件创建
- [ ] 支持 DeepSeek/OpenAI/Anthropic 三种 provider
- [ ] 重试 + 限流 + 超时错误处理
- [ ] config.yaml 读取配置
- [ ] 所有现有 LLM 调用迁移到统一客户端

#### Step 1.2: 迁移现有 LLM 调用

| 原文件 | 迁移动作 |
|--------|---------|
| `ingest_with_llm.py` | `_extract_with_llm()` → `llm.analyze_content()` |
| `refine.py` | `call_deepseek()` → `llm.generate_summary()` |
| `llm_ingest.py` | `analyze_with_llm()` → `llm.analyze_content()` + `llm.generate_summary()` |

**验收标准**:
- [ ] 3个文件的 LLM 调用都改为使用 llm_client
- [ ] 功能不变, 但代码更简洁
- [ ] 错误处理统一

---

### Phase 2: Wikilinks 交叉引用系统 (P0 - 核心理念)

**目标**: 实现 Karpathy 核心理念 - 知识是互连的

#### Step 2.1: 创建 `scripts/wikilinks.py`

```python
class WikilinkEngine:
    """管理 wiki 页面间的交叉引用"""

    def __init__(self, graph_path="graph.yaml"): ...

    def get_related_pages(self, entity: str, topic: str) -> list[str]
    # 基于知识图谱: 公司→同行业公司, 公司→行业, 公司→主题

    def generate_wikilinks(self, content: str, current_page: str) -> list[str]
    # LLM + 规则混合: 识别内容中提及的实体, 匹配到已有wiki页面

    def inject_wikilinks(self, content: str, links: dict[str, str]) -> str
    # 将 [[wikilink]] 注入到内容中: 实体名 → [[实体名|显示文本]]

    def build_backlinks_index(self) -> dict[str, list[str]]
    # 构建反向链接索引: 被哪些页面引用
```

**wikilink 规则**:
1. 同行业公司互相链接 (例: `[[寒武纪]]` 出现在中微公司的页面)
2. 公司页面链接到所属行业页面 (例: `[[GPU与AI芯片]]`)
3. 公司页面链接到所属主题页面 (例: `[[半导体国产替代]]`)
4. 时间线条目中提及的实体链接到对应页面
5. 综合评估中引用其他页面的结论

#### Step 2.2: 在 Ingest 中集成 wikilinks

修改 `ingest.py` / `ingest_with_llm.py`:
- 每次更新一个 wiki 页面后, 自动生成相关 wikilinks
- 更新所有被引用页面的 "相关动态" 部分

#### Step 2.3: 回填现有页面的 wikilinks

创建 `scripts/backfill_wikilinks.py`:
- 扫描所有现有 wiki 页面
- 基于 graph.yaml 的关系图谱, 注入 wikilinks
- 在每个 wiki 页面底部添加 "相关页面" 部分

**验收标准**:
- [ ] wikilinks.py 引擎创建
- [ ] ingest 流程自动添加 wikilinks
- [ ] 现有 119 个 wiki 页面回填 wikilinks
- [ ] Obsidian 图谱视图显示实体间关系

---

### Phase 3: Wiki 内容质量提升 (P0 - 从文档堆砌到知识合成)

**目标**: 将 wiki 从"文档仓库"升级为"复合知识体"

#### Step 3.1: 核心 Questions 自动生成

创建功能: 为每个 topic 自动生成追踪问题

```python
def generate_core_questions(entity, sector, existing_data):
    """基于实体信息和已有数据, 生成 3-5 个核心追踪问题"""
    # 例: 中微公司/GPU与AI芯片 →
    # - 刻蚀设备市占率变化趋势？
    # - 与泛林半导体/东京电子的技术差距？
    # - 下游客户结构变化？
    # - 先进制程设备验证进展？
```

#### Step 3.2: 综合评估自动生成

创建功能: 基于时间线条目, 生成阶段性综合评估

```python
def synthesize_assessment(timeline_entries, core_questions, entity):
    """分析时间线条目, 回答核心问题, 生成评估"""
    # 不再是"待积累数据后补充", 而是:
    # > 中微公司作为国内刻蚀设备龙头, 2025年在CCP刻蚀领域...
    # > 核心判断: 国产替代进入深水区, 公司从跟随者转向并跑者...
```

#### Step 3.3: Ingest 后自动更新评估

修改 ingest 流程:
1. 新条目插入时间线后
2. 如果该页面积累 >= 5 条时间线条目
3. 调用 LLM 重新生成综合评估
4. 对比新旧评估, 如果判断变化则标注

**验收标准**:
- [ ] 所有 wiki 页面有具体的核心问题 (非"待设定")
- [ ] 积累 >= 5 条的页面有 LLM 生成的综合评估
- [ ] 评估随新条目动态更新

---

### Phase 4: Query → Wiki 反馈循环 (P1 - 知识积累)

**目标**: 实现 "好答案变成新页面"

#### Step 4.1: 升级 query.py

```python
class LLMAssistedQuery:
    def search(self, query: str) -> list[dict]:
        """1. 关键词搜索找相关页面"""
        ...

    def synthesize(self, query: str, pages: list) -> str:
        """2. LLM 综合多个页面内容生成答案"""
        ...

    def should_persist(self, answer: str) -> bool:
        """3. 判断答案是否有长期价值"""
        ...

    def persist_as_wiki_page(self, query: str, answer: str):
        """4. 将好答案保存为新 wiki 页面"""
        ...
```

#### Step 4.2: 答案持久化

当用户查询产生有价值分析时:
1. 生成 markdown 页面
2. 保存到 `companies/{entity}/wiki/分析_{topic}.md`
3. 更新 index.md
4. 记录到 log.md

**验收标准**:
- [ ] query.py 使用 LLM 综合答案
- [ ] 有价值的答案自动/手动存回 wiki
- [ ] 存回的页面有正确的 frontmatter 和 wikilinks

---

### Phase 5: LLM 驱动的 Lint (P2 - 质量保障)

**目标**: 从规则检查升级到语义理解

#### Step 5.1: 升级 lint.py

新增 LLM 驱动的检查项:

```python
class LLMLinter:
    def check_semantic_contradictions(self, pages: list) -> list:
        """语义矛盾检测: 超越模式匹配"""

    def check_claim_freshness(self, page: str) -> list:
        """判断哪些结论可能已过时"""

    def discover_missing_concepts(self, page: str, index: str) -> list:
        """发现提及但未建页的概念"""

    def check_cross_reference_coverage(self) -> list:
        """交叉引用完整度检查"""

    def suggest_new_sources(self, gaps: list) -> list:
        """建议应搜索的新信息源"""
```

#### Step 5.2: 增强 contradiction_detector.py

用 LLM 替换规则匹配:
- 数值矛盾 (LLM 理解上下文)
- 时间矛盾 (LLM 理解时效性)
- 观点矛盾 (LLM 理解立场)

**验收标准**:
- [ ] lint.py 有 LLM 检查模式
- [ ] 能发现语义级矛盾
- [ ] 能建议缺失的概念页面
- [ ] lint 报告更丰富

---

### Phase 6: Ingest 跨页更新 (P1 - 双向更新)

**目标**: 一条新闻更新所有相关页面

#### Step 6.1: 跨实体更新引擎

```
一条新闻 "中微公司获得长存新订单" 应更新:
1. companies/中微公司/wiki/公司动态.md     (直接相关)
2. companies/中微公司/wiki/相关动态.md     (行业动态)
3. sectors/半导体设备/wiki/行业动态.md      (所属行业)
4. themes/半导体国产替代/wiki/进展.md       (所属主题)
5. companies/北方华创/wiki/相关动态.md      (同行业竞争者)
```

#### Step 6.2: 更新流程设计

```python
class CrossPageUpdater:
    def find_affected_pages(self, entity: str, content: str) -> list[str]:
        """基于知识图谱 + LLM 判断, 找到所有应更新的页面"""

    def update_page(self, page_path: str, new_entry: dict):
        """在目标页面添加时间线条目"""

    def run_cross_update(self, source_entity: str, content: str, entry: dict):
        """执行完整跨页更新"""
```

**验收标准**:
- [ ] 一条新闻自动更新 3-5 个相关页面
- [ ] 跨实体更新有日志记录
- [ ] 不产生重复条目

---

## 四、实施顺序和依赖关系

```
Phase 1 (统一LLM客户端)
    │
    ├── Phase 2 (Wikilinks) ─── Phase 6 (跨页更新)
    │
    ├── Phase 3 (内容质量)
    │
    ├── Phase 4 (Query反馈)
    │
    └── Phase 5 (LLM Lint)
```

**并行可能性**: Phase 2-6 在 Phase 1 完成后可以并行

## 五、技术规范

### LLM 调用原则
1. **始终有 fallback**: LLM 失败时降级到规则处理
2. **批量处理**: 合并小请求, 减少API调用
3. **成本控制**: 摘要用小模型, 分析用大模型
4. **缓存结果**: 相同输入不重复调用

### 配置管理
- 所有 LLM 设置在 `config.yaml` 的 `llm:` 段
- API Key 通过环境变量, 不写入代码
- Provider 可切换, 代码不绑定特定 API

### 错误处理
- API 调用失败 → 降级到规则处理
- 超时 → 重试 3 次 (指数退避)
- 限流 → 自动等待
- JSON 解析失败 → 正则提取

---

## 六、文件清单

| 文件 | 操作 | Phase |
|------|------|-------|
| `scripts/llm_client.py` | 新建 | 1 |
| `scripts/ingest_with_llm.py` | 修改 (使用统一客户端) | 1 |
| `scripts/refine.py` | 修改 (使用统一客户端) | 1 |
| `scripts/llm_ingest.py` | 修改 (使用统一客户端) | 1 |
| `config.yaml` | 修改 (扩展 llm 配置) | 1 |
| `scripts/wikilinks.py` | 新建 | 2 |
| `scripts/backfill_wikilinks.py` | 新建 | 2 |
| `scripts/ingest.py` | 修改 (集成 wikilinks) | 2 |
| `scripts/query.py` | 修改 (LLM + 存回) | 4 |
| `scripts/lint.py` | 修改 (LLM 检查) | 5 |
| `scripts/contradiction_detector.py` | 修改 (LLM 语义检测) | 5 |
| `scripts/cross_page_updater.py` | 新建 | 6 |

---

## 七、成功指标

| 指标 | 当前 | Phase 1 后 | 全部完成后 |
|------|------|-----------|-----------|
| LLM 调用统一性 | 3套独立代码 | 1套统一客户端 | 1套统一客户端 |
| Wiki 页面 wikilinks | 0 | 0 | 平均每页 5+ 个 |
| 综合评估填充率 | ~0% | ~0% | >= 80% |
| 核心问题设定率 | ~0% | ~0% | 100% |
| Query 能力 | 关键词搜索 | 关键词搜索 | LLM 综合答案 + 存回 |
| Lint 能力 | 规则检查 | 规则检查 | LLM 语义检查 |
| 跨页更新 | 无 | 无 | 自动 3-5 页面/条新闻 |
