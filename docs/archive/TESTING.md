# company-wiki 测试指南

## 快速开始

### 1. 安装测试依赖

```bash
pip install -r requirements-test.txt
```

### 2. 运行测试

```bash
# 运行所有测试
./scripts/run_tests.sh

# 运行特定类型测试
./scripts/run_tests.sh unit      # 单元测试
./scripts/run_tests.sh integration  # 集成测试
./scripts/run_tests.sh e2e       # 端到端测试

# 运行测试并生成覆盖率报告
./scripts/run_tests.sh coverage

# 运行快速测试（排除慢速测试）
./scripts/run_tests.sh quick
```

### 3. 验证 Phase 1 完成

```bash
# 运行 Phase 1 验收测试
python3 -m pytest tests/e2e/test_phase1_validation.py -v -s
```

## 测试结构

```
tests/
├── __init__.py
├── conftest.py              # pytest 配置和 fixtures
├── fixtures/                # 测试数据
│   └── sample_news.md
├── unit/                    # 单元测试
│   └── test_first.py
├── integration/             # 集成测试
└── e2e/                     # 端到端测试
    ├── test_first_e2e.py
    ├── test_config_loading.py
    └── test_phase1_validation.py
```

## 测试类型说明

### 单元测试 (Unit Tests)

- 测试单个函数或类
- 不依赖外部系统（文件系统、网络、数据库）
- 运行速度快（< 1秒）
- 使用 mock 隔离依赖

### 集成测试 (Integration Tests)

- 测试模块间交互
- 可能依赖文件系统
- 运行速度中等（1-10秒）
- 验证接口契约

### 端到端测试 (E2E Tests)

- 测试完整工作流
- 模拟真实使用场景
- 运行速度较慢（10-30秒）
- 验证系统行为

## 测试标记

使用 pytest 标记来分类测试：

```python
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_integration():
    pass

@pytest.mark.e2e
def test_e2e():
    pass

@pytest.mark.slow
def test_slow():
    pass
```

运行特定标记的测试：

```bash
# 只运行单元测试
python3 -m pytest -m unit

# 排除慢速测试
python3 -m pytest -m "not slow"

# 运行端到端测试
python3 -m pytest -m e2e
```

## Fixtures

测试 fixtures 在 `conftest.py` 中定义：

- `wiki_root`: 临时 wiki 根目录
- `sample_graph_yaml`: 示例 graph.yaml 内容
- `sample_config_yaml`: 示例 config.yaml 内容
- `sample_news_content`: 示例新闻内容
- `temp_wiki_structure`: 临时 wiki 目录结构
- `mock_env_vars`: 模拟环境变量

使用示例：

```python
def test_with_fixtures(temp_wiki_structure, mock_env_vars):
    wiki_root = temp_wiki_structure
    # 测试逻辑
```

## 覆盖率

### 生成覆盖率报告

```bash
# 生成 HTML 报告
python3 -m pytest tests/ --cov=scripts --cov-report=html

# 在终端显示报告
python3 -m pytest tests/ --cov=scripts --cov-report=term

# 生成 XML 报告（用于 CI）
python3 -m pytest tests/ --cov=scripts --cov-report=xml
```

### 查看 HTML 报告

```bash
# 打开浏览器查看
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| config_loader | 95% |
| graph | 90% |
| ingest | 85% |
| collect_news | 85% |
| extract | 85% |
| **整体** | **88%** |

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python3 -m pytest tests/ --cov=scripts --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 调试测试

### 运行单个测试

```python
# 运行单个测试函数
python3 -m pytest tests/unit/test_first.py::test_framework_works -v

# 运行单个测试类
python3 -m pytest tests/e2e/test_config_loading.py::TestConfigLoading -v
```

### 显示打印输出

```bash
# 显示 print 输出
python3 -m pytest tests/ -s

# 显示详细输出
python3 -m pytest tests/ -v

# 显示最详细的输出
python3 -m pytest tests/ -vv
```

### 使用 pdb 调试

```python
def test_something():
    import pdb; pdb.set_trace()
    # 测试逻辑
```

### 使用 pytest.set_trace()

```python
def test_something():
    pytest.set_trace()
    # 测试逻辑
```

## 常见问题

### 测试找不到模块

```bash
# 确保 scripts 目录在 Python 路径中
export PYTHONPATH="${PYTHONPATH}:$(pwd)/scripts"

# 或者在测试中添加
import sys
sys.path.insert(0, "scripts")
```

### 环境变量问题

```bash
# 设置测试环境变量
export TAVILY_API_KEY="test-key"
export DEEPSEEK_API_KEY="test-key"

# 或者使用 pytest-env 插件
pip install pytest-env
```

### 临时目录问题

```python
# 使用 pytest 的 tmp_path fixture
def test_with_temp(tmp_path):
    temp_file = tmp_path / "test.txt"
    temp_file.write_text("test")
    # 测试逻辑
```

## 最佳实践

### 1. 测试命名

```python
# 好
def test_config_loads_from_file():
    pass

# 不好
def test_config():
    pass
```

### 2. 测试隔离

```python
# 好：每个测试独立
def test_1(tmp_path):
    # 使用临时目录
    pass

def test_2(tmp_path):
    # 使用不同的临时目录
    pass

# 不好：测试共享状态
shared_data = {}
def test_1():
    shared_data["key"] = "value"

def test_2():
    assert shared_data["key"] == "value"  # 依赖 test_1
```

### 3. 使用 fixtures

```python
# 好：使用 fixtures
def test_with_fixture(sample_config):
    # 使用共享的 fixture
    pass

# 不好：重复创建测试数据
def test_without_fixture():
    config = {
        "llm": {"provider": "deepseek", ...},
        "search": {"engine": "tavily", ...},
        # 重复的配置...
    }
```

### 4. 测试错误情况

```python
def test_invalid_input():
    with pytest.raises(ValueError) as exc_info:
        function_under_test(invalid_input)
    
    assert "expected error message" in str(exc_info.value)
```

### 5. 使用 mock

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    with patch('module.external_api') as mock_api:
        mock_api.return_value = {"result": "success"}
        
        result = function_under_test()
        
        assert result == "success"
        mock_api.assert_called_once()
```

## Phase 验证

### Phase 1 验证

运行以下命令验证 Phase 1 完成：

```bash
# 1. 验证安全加固
python3 -m pytest tests/e2e/test_phase1_validation.py::TestPhase1Security -v

# 2. 验证测试基础设施
python3 -m pytest tests/e2e/test_phase1_validation.py::TestPhase1Testing -v

# 3. 验证集成
python3 -m pytest tests/e2e/test_phase1_validation.py::TestPhase1Integration -v

# 4. 运行完整验收测试
python3 -m pytest tests/e2e/test_phase1_validation.py::test_phase1_acceptance_criteria -v -s
```

### 验收标准

- [ ] .env.example 文件存在
- [ ] config.yaml 中没有硬编码密钥
- [ ] config_loader.py 可以导入
- [ ] 测试框架可以运行
- [ ] 环境变量可以覆盖配置
- [ ] 错误提示清晰有用

## 下一步

Phase 1 完成后，进入 Phase 2：核心模块重构。

详见 [REFACTORING_PLAN.md](REFACTORING_PLAN.md)