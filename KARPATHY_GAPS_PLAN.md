# Karpathy 差距改进实施计划

> 创建日期: 2026-04-17
> 目标: 缩小与 Karpathy LLM Wiki 概念的差距

## 核心差距

### Gap 1: LLM 集成 (30/100) - 最大差距
**Karpathy**: LLM 读取来源，自动整合到 wiki
**我们**: 脚本自动处理，无 LLM 参与

### Gap 2: Query 答案存回 (60/100)
**Karpathy**: 好答案可以存回 wiki
**我们**: 有基础实现但不完善

### Gap 3: 矛盾检测 (75/100)
**Karpathy**: LLM 自动标记矛盾
**我们**: 脚本基础实现

---

## 实施计划

### Phase 1: LLM 集成 (1-2天)

#### Step 1.1: 创建 LLM 客户端
- [ ] 创建 `scripts/llm_client.py`
- [ ] 支持 DeepSeek API
- [ ] 支持 OpenAI API (可选)
- [ ] 添加错误处理和重试

#### Step 1.2: 创建 LLM Ingest 模块
- [ ] 创建 `scripts/llm_ingest.py`
- [ ] LLM 读取来源内容
- [ ] LLM 提取关键信息
- [ ] LLM 判断相关性
- [ ] LLM 生成时间线条目

#### Step 1.3: 集成到现有流程
- [ ] 修改 `ingest.py` 支持 LLM 模式
- [ ] 添加 `--use-llm` 参数
- [ ] 保持向后兼容

### Phase 2: Query 答案存回 (1天)

#### Step 2.1: 增强 Query 模块
- [ ] 改进 `query.py` 的答案综合
- [ ] 使用 LLM 生成更好的答案
- [ ] 改进答案存回逻辑

#### Step 2.2: 添加答案质量评估
- [ ] 评估答案质量
- [ ] 决定是否存回
- [ ] 生成合适的 wiki 页面

### Phase 3: 矛盾检测增强 (1天)

#### Step 3.1: LLM 矛盾检测
- [ ] 增强 `contradiction_detector.py`
- [ ] 使用 LLM 判断矛盾
- [ ] 生成矛盾解释

#### Step 3.2: 集成到 Ingest 流程
- [ ] Ingest 时自动检查矛盾
- [ ] 标记矛盾页面
- [ ] 生成矛盾报告

---

## 开始实施

### Phase 1: LLM 集成