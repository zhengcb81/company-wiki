# company-wiki 重构实施计划

> 版本: 1.0
> 创建日期: 2026-04-17
> 目标: 将个人项目升级为生产级系统

## 核心原则

1. **测试驱动**: 每个模块完成前必须有100%端到端测试通过
2. **向后兼容**: 重构过程中系统必须持续可运行
3. **渐进式改进**: 避免大爆炸式重写，每次改动可验证
4. **安全第一**: 任何涉及密钥/凭证的改动优先处理

## 阶段划分

```
Phase 1: 安全加固 + 测试基础设施 (Week 1-2)
Phase 2: 核心模块重构 (Week 3-4)
Phase 3: 架构优化 (Week 5-6)
Phase 4: 监控与文档 (Week 7-8)
```

---

## Phase 1: 安全加固 + 测试基础设施

### 1.1 密钥管理重构

**问题**: config.yaml 硬编码 API 密钥

**实施步骤**:
```
1. 创建 .env.example 模板文件
2. 创建 scripts/config_loader.py 统一配置加载
3. 修改所有使用 config 的脚本
4. 添加 .env 到 .gitignore
5. 运行端到端测试验证
```

**文件变更**:
- 新建: `.env.example`
- 新建: `scripts/config_loader.py`
- 修改: `config.yaml` (移除密钥)
- 修改: `scripts/collect_news.py`
- 修改: `scripts/ingest.py`
- 修改: 所有使用 config 的脚本

**验收标准**:
- [ ] .env 文件不存在时，系统给出清晰错误提示
- [ ] 环境变量可以覆盖 config.yaml 中的任何配置
- [ ] 运行 `python3 scripts/collect_news.py --dry-run` 不报错
- [ ] 运行 `python3 scripts/ingest.py --check` 不报错

### 1.2 测试框架搭建

**目标**: 建立完整的测试基础设施

**实施步骤**:
```
1. 创建测试目录结构
2. 安装测试依赖 (pytest, pytest-cov, pytest-mock)
3. 创建测试配置文件 (conftest.py)
4. 创建测试 fixtures 和 helpers
5. 编写第一个端到端测试
```

**目录结构**:
```
tests/
├── __init__.py
├── conftest.py              # pytest 配置和 fixtures
├── fixtures/                # 测试数据
│   ├── sample_news.md
│   ├── sample_graph.yaml
│   └── sample_config.yaml
├── unit/                    # 单元测试
│   ├── test_config_loader.py
│   ├── test_graph.py
│   └── test_extract.py
├── integration/             # 集成测试
│   ├── test_collect_news.py
│   └── test_ingest.py
└── e2e/                     # 端到端测试
    ├── test_full_pipeline.py
    └── test_cli_commands.py
```

**验收标准**:
- [ ] `pytest tests/` 可以运行
- [ ] 测试覆盖率 > 0% (初始基线)
- [ ] CI 配置文件可以运行测试

### 1.3 端到端测试: 完整 Pipeline

**测试场景**: 从新闻采集到 wiki 生成的完整流程

```python
# tests/e2e/test_full_pipeline.py

def test_full_pipeline_with_mock(tmp_path):
    """
    端到端测试：模拟完整数据流
    1. 创建临时 graph.yaml
    2. Mock Tavily API 返回测试数据
    3. 运行 collect_news
    4. 运行 ingest
    5. 验证 wiki 文件生成
    6. 验证 log.md 记录
    """
    # 设置临时环境
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    
    # 复制测试 fixtures
    # Mock 外部 API
    # 运行 pipeline
    # 验证结果
```

**验收标准**:
- [ ] 测试在干净环境中100%通过
- [ ] 测试运行时间 < 30秒
- [ ] 测试不依赖外部网络

---

## Phase 2: 核心模块重构

### 2.1 配置管理统一

**目标**: 消除重复的 YAML 解析代码

**实施步骤**:
```
1. 创建 scripts/utils/config.py 模块
2. 实现 ConfigLoader 类
3. 添加配置验证逻辑
4. 迁移所有脚本使用新配置加载器
5. 删除重复代码
6. 运行端到端测试
```

**新模块设计**:
```python
# scripts/utils/config.py

from dataclasses import dataclass
from typing import Optional
import os
import yaml
from pathlib import Path

@dataclass
class LLMConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    max_tokens: int = 1024
    temperature: float = 0.3

@dataclass
class SearchConfig:
    engine: str
    api_key: str
    results_per_query: int = 8
    language: str = "zh"
    max_age_days: int = 7

@dataclass
class Config:
    llm: LLMConfig
    search: SearchConfig
    wiki_root: Path
    
    @classmethod
    def load(cls, config_path: Path = None) -> 'Config':
        """加载配置，支持环境变量覆盖"""
        config_path = config_path or Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        
        # 环境变量覆盖
        if os.getenv("TAVILY_API_KEY"):
            raw["search"]["tavily_api_key"] = os.getenv("TAVILY_API_KEY")
        if os.getenv("DEEPSEEK_API_KEY"):
            raw["llm"]["api_key"] = os.getenv("DEEPSEEK_API_KEY")
        
        return cls(
            llm=LLMConfig(**raw["llm"]),
            search=SearchConfig(**raw["search"]),
            wiki_root=Path(raw.get("paths", {}).get("wiki_root", "~/company-wiki")).expanduser()
        )
```

**验收标准**:
- [ ] 所有脚本使用统一的配置加载
- [ ] 无重复的 YAML 解析代码
- [ ] 配置验证可以捕获格式错误
- [ ] 端到端测试通过

### 2.2 Graph 模块重构

**目标**: 拆分职责，提高可测试性

**实施步骤**:
```
1. 创建 scripts/models/ 目录
2. 拆分 graph.py 为多个模块:
   - models/graph_data.py: 数据模型
   - models/graph_loader.py: 数据加载
   - models/graph_queries.py: 查询接口
   - graph.py: 保持向后兼容的 facade
3. 添加数据验证
4. 编写单元测试
5. 运行端到端测试
```

**新模块结构**:
```
scripts/
├── models/
│   ├── __init__.py
│   ├── graph_data.py      # 数据类定义
│   ├── graph_loader.py    # YAML 加载和保存
│   └── graph_queries.py   # 查询方法
├── utils/
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   └── logger.py          # 日志工具
└── graph.py               # 向后兼容 facade
```

**验收标准**:
- [ ] 原有 CLI 命令全部正常工作
- [ ] 新模块有100%单元测试覆盖
- [ ] 查询性能无明显下降
- [ ] 支持增量更新（不重新加载整个文件）

### 2.3 Ingest 流水线重构

**目标**: 提高健壮性和可测试性

**实施步骤**:
```
1. 创建 IngestPipeline 类
2. 实现错误恢复机制
3. 添加处理进度追踪
4. 分离关注点（文件扫描、内容提取、wiki 更新）
5. 编写集成测试
6. 运行端到端测试
```

**新架构**:
```python
# scripts/ingest/pipeline.py

class IngestPipeline:
    """可测试、可恢复的 Ingest 流水线"""
    
    def __init__(self, config: Config, graph: Graph):
        self.config = config
        self.graph = graph
        self.scanner = FileScanner()
        self.extractor = ContentExtractor()
        self.updater = WikiUpdater()
    
    def run(self, company: str = None, dry_run: bool = False) -> PipelineResult:
        """执行完整流水线"""
        pending = self.scanner.scan(self.graph, company)
        results = PipelineResult()
        
        for file_path, entity, entity_type in pending:
            try:
                meta = self.extractor.extract(file_path)
                if not self._should_process(meta):
                    results.skipped.append(file_path)
                    continue
                
                topics = self._determine_relevance(meta)
                for topic in topics:
                    if not dry_run:
                        self.updater.update(topic, meta)
                    results.updated.append((file_path, topic))
                
                if not dry_run:
                    self._mark_ingested(file_path)
                    
            except Exception as e:
                results.errors.append((file_path, str(e)))
                logger.error(f"Failed to process {file_path}: {e}")
                continue  # 继续处理下一个文件
        
        return results
```

**验收标准**:
- [ ] 单个文件失败不影响其他文件处理
- [ ] 支持断点续传（已处理的文件不重复处理）
- [ ] 处理进度实时输出
- [ ] 错误日志包含足够诊断信息
- [ ] 端到端测试通过

### 2.4 端到端测试: 重构验证

**测试场景**: 验证重构后的系统与原系统行为一致

```python
# tests/e2e/test_refactoring_validation.py

def test_refactoring_preserves_behavior():
    """
    验证重构后系统行为与原系统一致
    1. 使用相同的测试数据
    2. 分别运行新旧系统
    3. 对比输出结果
    """
    # 准备测试数据
    test_data = load_test_fixtures()
    
    # 运行原系统（备份版本）
    old_results = run_original_system(test_data)
    
    # 运行新系统
    new_results = run_refactored_system(test_data)
    
    # 验证结果一致
    assert old_results.wiki_files == new_results.wiki_files
    assert old_results.log_entries == new_results.log_entries
    assert old_results.errors == new_results.errors
```

**验收标准**:
- [ ] 新旧系统输出完全一致
- [ ] 性能无明显下降（< 10%）
- [ ] 所有原有 CLI 命令正常工作

---

## Phase 3: 架构优化

### 3.1 存储层改进

**目标**: 支持更大规模数据

**实施步骤**:
```
1. 设计 SQLite 数据库 schema
2. 实现数据迁移脚本（YAML → SQLite）
3. 创建 Repository 模式的数据访问层
4. 保持 YAML 导出功能（向后兼容）
5. 编写迁移测试
6. 运行端到端测试
```

**数据库 Schema**:
```sql
-- companies 表
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    ticker TEXT,
    exchange TEXT,
    position TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- sectors 表
CREATE TABLE sectors (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT CHECK(type IN ('sector', 'subsector')),
    description TEXT,
    tier INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- wiki_entries 表
CREATE TABLE wiki_entries (
    id INTEGER PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    content TEXT,
    last_updated DATE,
    sources_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_name, entity_type, topic_name)
);

-- ingested_files 表
CREATE TABLE ingested_files (
    id INTEGER PRIMARY KEY,
    file_hash TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**验收标准**:
- [ ] 支持1000+公司数据无性能问题
- [ ] 可以导出为原有 YAML 格式
- [ ] 支持并发读取
- [ ] 数据库损坏可以自动恢复
- [ ] 端到端测试通过

### 3.2 异步处理

**目标**: 提高处理吞吐量

**实施步骤**:
```
1. 引入 asyncio 支持
2. 实现并发文件扫描
3. 实现并发 API 调用（限制并发数）
4. 添加进度条显示
5. 编写并发测试
6. 运行端到端测试
```

**验收标准**:
- [ ] 处理速度提升 3x+
- [ ] 内存使用稳定（无泄漏）
- [ ] 可以取消正在进行的任务
- [ ] 端到端测试通过

### 3.3 错误处理和重试

**目标**: 提高系统健壮性

**实施步骤**:
```
1. 定义错误分类（临时性/永久性）
2. 实现重试策略（指数退避）
3. 添加熔断器模式
4. 实现死信队列（失败任务记录）
5. 编写错误场景测试
6. 运行端到端测试
```

**验收标准**:
- [ ] API 临时故障自动重试成功
- [ ] 永久性错误立即失败并记录
- [ ] 死信队列可以手动重试
- [ ] 端到端测试通过

### 3.4 端到端测试: 架构验证

**测试场景**: 验证架构改进的实际效果

```python
# tests/e2e/test_architecture_validation.py

def test_performance_improvement():
    """验证性能提升"""
    # 准备大数据集（100个文件）
    large_dataset = generate_large_dataset(100)
    
    # 测试原系统
    old_time = time_original_system(large_dataset)
    
    # 测试新系统
    new_time = time_refactored_system(large_dataset)
    
    # 验证性能提升
    assert new_time < old_time * 0.5  # 至少提升2倍

def test_error_resilience():
    """验证错误恢复能力"""
    # 模拟各种故障
    with mock_api_failures():
        results = run_pipeline_with_failures()
    
    # 验证部分成功
    assert results.success_rate > 0.8
    assert results.can_retry_failed()
```

**验收标准**:
- [ ] 性能提升达到预期目标
- [ ] 错误恢复能力显著提高
- [ ] 系统可以处理更大规模数据

---

## Phase 4: 监控与文档

### 4.1 监控系统

**实施步骤**:
```
1. 添加结构化日志（JSON格式）
2. 实现指标收集（处理数量、错误率、延迟）
3. 创建健康检查端点
4. 添加告警机制
5. 编写监控测试
6. 运行端到端测试
```

**验收标准**:
- [ ] 日志可以被 ELK/Loki 等系统解析
- [ ] 关键指标实时可见
- [ ] 异常情况自动告警
- [ ] 端到端测试通过

### 4.2 文档完善

**实施步骤**:
```
1. 创建 API 文档（使用 Sphinx）
2. 编写部署指南
3. 创建故障排除手册
4. 添加架构决策记录（ADR）
5. 运行文档测试
```

**验收标准**:
- [ ] 所有公共 API 有文档字符串
- [ ] 部署指南可以无脑跟随
- [ ] 常见问题有解决方案
- [ ] 文档与代码同步更新

### 4.3 最终端到端测试

**测试场景**: 完整系统验证

```python
# tests/e2e/test_final_validation.py

def test_production_readiness():
    """生产就绪验证"""
    
    # 1. 安全测试
    assert no_hardcoded_secrets()
    assert env_vars_work_correctly()
    
    # 2. 功能测试
    assert full_pipeline_works()
    assert all_cli_commands_work()
    
    # 3. 性能测试
    assert meets_performance_targets()
    
    # 4. 可靠性测试
    assert handles_errors_gracefully()
    assert recovers_from_failures()
    
    # 5. 可观测性测试
    assert logging_works()
    assert metrics_collected()
    
    # 6. 文档测试
    assert docs_are_complete()
    assert examples_work()
```

**验收标准**:
- [ ] 所有测试100%通过
- [ ] 无安全漏洞
- [ ] 性能达到目标
- [ ] 文档完整准确

---

## 测试策略总结

### 测试金字塔

```
         /\
        /  \        E2E Tests (10%)
       /    \       - 完整 pipeline 验证
      /      \      - CLI 命令测试
     /--------\     - 端到端场景
    /          \    Integration Tests (30%)
   /            \   - 模块间交互
  /              \  - API 调用测试
 /----------------\ - 文件系统操作
/                  \Unit Tests (60%)
/                   - 纯函数测试
/                    - 数据模型测试
/                    - 工具函数测试
```

### 测试覆盖率目标

| 模块 | 单元测试 | 集成测试 | E2E测试 | 总覆盖率 |
|------|---------|---------|---------|----------|
| config_loader | 100% | 80% | 100% | 95% |
| graph | 90% | 80% | 100% | 90% |
| ingest | 80% | 90% | 100% | 85% |
| collect_news | 80% | 80% | 100% | 85% |
| extract | 90% | 70% | 100% | 85% |
| **整体** | **85%** | **80%** | **100%** | **88%** |

### 测试运行频率

- **每次提交**: 单元测试 + 快速集成测试
- **每天**: 完整集成测试
- **每周**: 完整 E2E 测试 + 性能测试
- **发布前**: 全部测试 + 安全扫描

---

## 实施检查清单

### Phase 1 完成检查

- [ ] .env.example 文件存在
- [ ] config_loader.py 实现完成
- [ ] 所有脚本使用新配置加载
- [ ] 测试框架搭建完成
- [ ] 第一个 E2E 测试通过
- [ ] 安全扫描无硬编码密钥

### Phase 2 完成检查

- [ ] 无重复 YAML 解析代码
- [ ] Graph 模块拆分完成
- [ ] Ingest 流水线重构完成
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 行为验证测试通过

### Phase 3 完成检查

- [ ] SQLite 存储层实现
- [ ] 异步处理支持
- [ ] 错误处理完善
- [ ] 性能测试通过
- [ ] 并发测试通过
- [ ] 压力测试通过

### Phase 4 完成检查

- [ ] 监控系统就绪
- [ ] 文档完整
- [ ] 最终 E2E 测试100%通过
- [ ] 安全审计通过
- [ ] 性能达标
- [ ] 可以安全部署

---

## 风险与缓解

### 技术风险

1. **数据迁移失败**
   - 缓解: 保留原 YAML 文件，支持回滚
   
2. **性能退化**
   - 缓解: 每个阶段都有性能测试
   
3. **兼容性问题**
   - 缓解: 保持 CLI 接口不变

### 时间风险

1. **测试编写耗时**
   - 缓解: 先写关键路径测试
   
2. **重构范围扩大**
   - 缓解: 严格遵循阶段划分

### 质量风险

1. **测试覆盖率不足**
   - 缓解: 强制覆盖率检查
   
2. **文档滞后**
   - 缓解: 文档与代码同步更新

---

## 成功标准

### 定量指标

- 测试覆盖率: > 88%
- 性能提升: > 2x
- 错误率: < 1%
- 文档完整性: 100%

### 定性指标

- 新开发者可以30分钟内上手
- 系统可以无人值守运行
- 故障可以快速定位和修复
- 代码可以安全重构

---

## 时间表

```
Week 1: Phase 1.1 (安全加固)
Week 2: Phase 1.2 + 1.3 (测试基础设施)
Week 3: Phase 2.1 + 2.2 (配置和Graph重构)
Week 4: Phase 2.3 + 2.4 (Ingest重构)
Week 5: Phase 3.1 + 3.2 (存储和异步)
Week 6: Phase 3.3 + 3.4 (错误处理)
Week 7: Phase 4.1 + 4.2 (监控和文档)
Week 8: Phase 4.3 (最终验证)
```

每个阶段结束时，运行该阶段的端到端测试，确保100%通过后再进入下一阶段。