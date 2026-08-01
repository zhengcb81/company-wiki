# 故障排除指南

> 最后更新: 2026-04-17

## 常见问题

### 配置问题

#### Q1: 配置验证失败

**错误信息**:
```
ValueError: 配置验证失败:
  - 缺少 LLM API Key (设置 MINIMAX_API_KEY 环境变量)
  - 缺少搜索 API Key (设置 TAVILY_API_KEY 环境变量)
```

**解决方案**:

1. 设置环境变量:
```bash
export MINIMAX_API_KEY="your_key_here"
export TAVILY_API_KEY="your_key_here"
```

2. 或创建 .env 文件:
```bash
cp .env.example .env
# 编辑 .env 文件
```

3. 验证配置:
```bash
python3 scripts/config.py
```

#### Q2: 配置文件不存在

**错误信息**:
```
WARNING: 配置文件不存在: ~/company-wiki/config.yaml
```

**解决方案**:
```bash
# 复制示例配置
cp config.yaml.example config.yaml

# 或使用默认配置
python3 scripts/config.py
```

---

### 下载问题

#### Q3: 文件下载到错误目录

**症状**: 文件下载到 `~/StockInfoDownloader/downloads/` 而不是 `~/company-wiki/companies/`

**原因**: StockInfoDownloader 的 config.json 中 save_dir 配置错误

**解决方案**:
```bash
# 检查配置
python3 scripts/download_reports_v2.py --check

# 修复配置
python3 -c "
import json
from pathlib import Path

config_path = Path.home() / 'StockInfoDownloader' / 'config.json'
with open(config_path) as f:
    config = json.load(f)

config['save_dir'] = str(Path.home() / 'company-wiki' / 'companies')

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
"
```

#### Q4: 下载超时

**错误信息**:
```
subprocess.TimeoutExpired: Command timed out
```

**解决方案**:

1. 增加超时时间:
```python
result = subprocess.run(..., timeout=1200)  # 20分钟
```

2. 检查网络连接:
```bash
curl -I https://www.cninfo.com.cn
```

3. 检查 StockInfoDownloader 是否正常:
```bash
cd ~/StockInfoDownloader
python3 main.py --help
```

#### Q5: 下载失败

**错误信息**:
```
Exit code: 1
ERROR: ...
```

**解决方案**:

1. 检查 StockInfoDownloader 日志:
```bash
ls ~/StockInfoDownloader/logs/
cat ~/StockInfoDownloader/logs/*.log
```

2. 检查股票代码是否正确:
```bash
python3 scripts/download_reports_v2.py --list | grep "公司名"
```

3. 手动测试下载:
```bash
cd ~/StockInfoDownloader
python3 main.py 688012  # 中微公司
```

---

### 文件分类问题

#### Q6: 文件没有被正确分类

**症状**: 文件在 raw 根目录，没有分类到子目录

**原因**: 分类规则不匹配

**解决方案**:

1. 检查分类规则:
```bash
cat config_rules.yaml | grep -A 10 "document_classification"
```

2. 手动分类:
```bash
python3 scripts/classify_documents.py
```

3. 添加新规则:
```yaml
# config_rules.yaml
document_classification:
  new_type:
    patterns:
      - "新模式1"
      - "新模式2"
    confidence: 0.9
    target_dir: "目标目录"
```

#### Q7: 投资者关系文档被错误分类到 research

**症状**: 投资者关系文档在 research 目录

**原因**: 分类优先级问题

**解决方案**:
```bash
# 移动文件
python3 -c "
import shutil
from pathlib import Path

for research_dir in Path('companies').rglob('raw/research'):
    for pdf_file in research_dir.glob('*.pdf'):
        if '投资者' in pdf_file.name:
            target_dir = research_dir.parent / 'investor_relations'
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pdf_file), str(target_dir / pdf_file.name))
"
```

---

### 数据处理问题

#### Q8: Ingest 失败

**错误信息**:
```
ERROR: ingest failed
```

**解决方案**:

1. 检查日志:
```bash
tail -100 ~/company-wiki/log.md
```

2. 使用 dry-run 模式:
```bash
python3 scripts/ingest.py --dry-run
```

3. 检查 graph.yaml:
```bash
python3 -c "
import yaml
with open('graph.yaml') as f:
    data = yaml.safe_load(f)
print(f'公司数: {len(data.get(\"companies\", {}))}')
print(f'行业数: {len(data.get(\"nodes\", {}))}')
"
```

#### Q9: 查询没有结果

**症状**: query.py 返回空结果

**解决方案**:

1. 检查 wiki 文件是否存在:
```bash
find companies -path "*/wiki/*.md" | wc -l
```

2. 检查搜索关键词:
```bash
python3 scripts/query.py --search "关键词"
```

3. 重建索引:
```bash
python3 scripts/generate_index.py
```

---

### 测试问题

#### Q10: 测试失败

**错误信息**:
```
FAILED tests/unit/test_xxx.py
```

**解决方案**:

1. 运行单个测试:
```bash
python3 -m pytest tests/unit/test_xxx.py::test_function -v
```

2. 检查依赖:
```bash
pip install -r requirements-test.txt
```

3. 清理缓存:
```bash
rm -rf .pytest_cache
rm -rf __pycache__
```

---

## 诊断工具

### 检查配置

```bash
python3 scripts/config.py
```

### 检查文档覆盖

```bash
python3 scripts/download_reports_v2.py --check
```

### 检查系统状态

```bash
python3 -c "
from pathlib import Path

# 检查文件数量
companies_dir = Path('companies')
pdf_count = len(list(companies_dir.rglob('*.pdf')))
md_count = len(list(companies_dir.rglob('*.md')))

print(f'PDF 文件: {pdf_count}')
print(f'Markdown 文件: {md_count}')

# 检查目录结构
for company_dir in companies_dir.iterdir():
    if company_dir.is_dir():
        raw_dir = company_dir / 'raw'
        wiki_dir = company_dir / 'wiki'
        if raw_dir.exists():
            raw_count = len(list(raw_dir.rglob('*')))
            wiki_count = len(list(wiki_dir.glob('*.md'))) if wiki_dir.exists() else 0
            print(f'{company_dir.name}: raw={raw_count}, wiki={wiki_count}')
"
```

### 检查测试覆盖

```bash
python3 -m pytest tests/ --cov=scripts --cov-report=term
```

---

## 日志分析

### 查看最近日志

```bash
tail -100 ~/company-wiki/log.md
```

### 查看错误日志

```bash
grep -i "error\|failed\|exception" ~/company-wiki/log.md | tail -50
```

### 查看下载日志

```bash
grep "download" ~/company-wiki/log.md | tail -20
```

### 查看 ingest 日志

```bash
grep "ingest" ~/company-wiki/log.md | tail -20
```

---

## Source Catalog 后台吞吐与等待状态

### backlog 很大但 worker 显示 waiting

`waiting` 只表示当前循环正在等待，不表示没有待处理资料。先运行：

```powershell
& '.\scripts\source_catalog_control.ps1' -Action status -PythonExe 'C:\Miniconda\python.exe'
```

schema 1.2 的控制中心会显示 `Next wake`：

- `productive_cycle`：上一轮实际完成了 Markdown 或 LLM 摘要，默认2秒后继续；
- `no_output`：没有产生新结果，按普通30秒轮询；
- `on_battery` / `user_active`：电源或兼容空闲门控阻止处理；
- `llm_deferred` / `llm_global_failure`：provider级退避，禁止通过缩短间隔绕过；
- `cycle_failed`：调度周期异常，保留普通轮询并检查 Last error。

如果配置已经是schema 1.2但看不到`Next wake`，通常是旧worker进程尚未加载新代码。先完成合同测试，再通过控制中心执行 Stop（保留ENABLED）和Start；不要手改`worker_runtime.json`、`worker_state.json`或SQLite。

### LLM 显示 401 或 `llm_deferred`

先查看控制中心的 `Last error`、`LLM retry` 和 `Next wake`。provider 全局失败会进入有界退避；不要缩短间隔、循环 Start，也不要手改 `worker_state.json` 来绕过。

MiniMax/MiMo 的托管凭据以项目根目录 `.env` 为权威来源。Windows 用户环境可能仍保留旧值，但 worker 必须在每次新进程启动时让项目 `.env` 覆盖它。配置和代码修复通过合同测试后，在 worker 为 `waiting` 且活动文档为 0 时执行一次 Stop/Start；Stop 保留 ENABLED 和登录自启动，原有 retry deadline 也会保留。deadline 到期后的新错误会带实际 `provider/model` route，便于判断主模型还是 fallback，但不会显示 key。

诊断时只核对 key 是否存在、来源是否一致以及最小 health request 是否成功；不要把 key、前后缀、请求头、可逆编码或 provider 原始响应复制到终端、Markdown、日志或工单。若项目 `.env` 的两个 provider 健康而旧进程仍报 401，通常是旧 worker 尚未加载修复；若新进程在 deadline 后仍对同一 route 报认证失败，再由 owner 在既有安全配置位置更新凭据。

### active模式占用资源过高

先确认进程仍为Idle/低优先级、batch仍为1且没有provider重复调用。需要立即回滚时，把`config/source_catalog_worker.yaml`中的`active_poll_interval_seconds`改为30，运行配置/worker合同测试后优雅Stop/Start。回滚不需要也不允许清空数据库、删除派生文件或移动原件。

### Pause/Stop偶发 WinError 5

控制JSON的原子替换会对瞬时`PermissionError`做最多6次短暂重试；若仍失败，说明不是瞬时共享冲突。保留控制中心错误与`.source_catalog/worker_console.log`，检查安全软件/同步软件占用和目录权限。不要循环强杀Python，也不要删除lock/runtime文件绕过身份校验。

---

## 性能优化

### 1. 减少 API 调用

```python
# 使用缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_function(arg):
    # 昂贵的计算
    pass
```

### 2. 并发处理

```python
from async_utils import AsyncExecutor

executor = AsyncExecutor(max_workers=10)
results = await executor.run_tasks(tasks)
```

### 3. 批量处理

```python
# 批量文件操作
files = list(Path('.').rglob('*.pdf'))
for batch in chunks(files, 100):
    process_batch(batch)
```

---

## 恢复操作

### 从备份恢复

```bash
# 恢复 graph.yaml
cp graph.yaml.backup graph.yaml

# 恢复公司数据
rsync -av backup/companies/ companies/
```

### 重新下载

```bash
# 重新下载指定公司
python3 scripts/download_reports_v2.py --company 中微公司

# 从 Windows 同步
python3 scripts/download_reports_v2.py --sync
```

### 重新处理

```bash
# 删除 .ingested 标记
rm -rf .ingested

# 重新 ingest
python3 scripts/ingest.py
```

---

## 联系支持

如果以上方法都无法解决问题：

1. 检查 GitHub Issues
2. 查看文档
3. 联系维护者
