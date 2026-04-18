# company-wiki 部署指南

> 版本: 1.0
> 最后更新: 2026-04-17

## 系统要求

- Python 3.10+
- 4GB+ RAM
- 10GB+ 磁盘空间
- Linux/macOS/Windows

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/company-wiki.git
cd company-wiki
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 4. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件
vim .env
```

填入以下配置：

```bash
# Tavily 搜索 API
TAVILY_API_KEY=your_tavily_api_key_here

# DeepSeek LLM API
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Wiki 根目录（可选）
# WIKI_ROOT=~/company-wiki
```

### 5. 初始化数据

```bash
# 创建目录结构
mkdir -p companies sectors themes

# 初始化 graph.yaml（如果不存在）
cp graph.yaml.example graph.yaml
```

## 配置详解

### config.yaml

```yaml
# 调度配置
schedule:
  news_collection: "daily"
  report_check: "weekly"
  lint: "weekly"

# LLM 配置
llm:
  provider: "deepseek"
  api_key: ""  # 使用环境变量 DEEPSEEK_API_KEY
  model: "deepseek-reasoner"
  base_url: "https://api.deepseek.com"
  max_tokens: 1024
  temperature: 0.3

# 搜索配置
search:
  engine: "tavily"
  tavily_api_key: ""  # 使用环境变量 TAVILY_API_KEY
  results_per_query: 8
  language: "zh"
  max_age_days: 7

# 路径配置
paths:
  wiki_root: "~/company-wiki"
```

### graph.yaml

graph.yaml 是系统的单一数据源，包含：

- **nodes**: 行业和主题
- **companies**: 公司信息
- **edges**: 实体关系
- **questions**: 跟踪问题

示例：

```yaml
nodes:
  半导体设备:
    type: sector
    description: 半导体制造设备
    tier: 5
    keywords:
    - 半导体设备
    - 芯片设备

companies:
  中微公司:
    ticker: '688012'
    exchange: SSE STAR
    sectors:
    - 半导体设备
    themes:
    - AI产业链
    position: 刻蚀设备龙头
    news_queries:
    - 中微公司 最新消息
    aliases:
    - '688012'
    - AMEC

edges:
  - from: 半导体设备
    to: 半导体代工
    type: upstream_of
    label: 设备是代工的上游

questions:
  半导体设备:
  - 各环节设备国产化率？
  - 先进制程设备进展？
```

## 运行系统

### 手动运行

```bash
# 采集新闻
python3 scripts/collect_news.py

# 整理数据
python3 scripts/ingest.py

# 查看产业链
python3 scripts/graph.py --overview
```

### 自动运行（Cron）

```bash
# 编辑 crontab
crontab -e

# 添加以下内容
# 每天 21:00 采集新闻
0 21 * * * cd ~/company-wiki && python3 scripts/collect_news.py >> log_cron.txt 2>&1

# 每天 21:30 整理数据
30 21 * * * cd ~/company-wiki && python3 scripts/ingest.py >> log_cron.txt 2>&1

# 每周日 10:00 下载报告
0 10 * * 0 cd ~/company-wiki && python3 scripts/run_download.sh >> log_cron.txt 2>&1
```

### 使用 systemd（Linux）

创建服务文件：

```bash
sudo vim /etc/systemd/system/company-wiki.service
```

内容：

```ini
[Unit]
Description=Company Wiki Service
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/home/your_username/company-wiki
ExecStart=/home/your_username/company-wiki/venv/bin/python3 scripts/collect_news.py
ExecStartPost=/home/your_username/company-wiki/venv/bin/python3 scripts/ingest.py

[Install]
WantedBy=multi-user.target
```

创建定时器：

```bash
sudo vim /etc/systemd/system/company-wiki.timer
```

内容：

```ini
[Unit]
Description=Company Wiki Timer

[Timer]
OnCalendar=*-*-* 21:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

启用定时器：

```bash
sudo systemctl enable company-wiki.timer
sudo systemctl start company-wiki.timer
```

## 监控

### 查看日志

```bash
# 查看 cron 日志
tail -f ~/company-wiki/log_cron.txt

# 查看操作日志
tail -f ~/company-wiki/log.md
```

### 健康检查

```bash
# 运行健康检查
python3 -c "
from monitoring import HealthChecker
checker = HealthChecker()
checker.run_all_checks()
print(checker.get_status_dict())
"
```

### 指标收集

```bash
# 查看指标
python3 -c "
from monitoring import MetricsCollector
metrics = MetricsCollector()
metrics.load()
for m in metrics.get_all_metrics():
    print(f'{m.name}: {m.value}')
"
```

## 备份与恢复

### 备份

```bash
# 备份数据库
python3 -c "
from storage import Database
db = Database()
db.backup('/path/to/backup.db')
"

# 备份 YAML
tar -czf company-wiki-backup-$(date +%Y%m%d).tar.gz \
  ~/company-wiki/graph.yaml \
  ~/company-wiki/companies \
  ~/company-wiki/sectors \
  ~/company-wiki/themes
```

### 恢复

```bash
# 恢复数据库
python3 -c "
from storage import Database
db = Database()
db.restore('/path/to/backup.db')
"

# 恢复 YAML
tar -xzf company-wiki-backup-20260417.tar.gz -C ~/
```

## 故障排除

### 常见问题

#### 1. API Key 错误

```
ERROR: No Tavily API key in config.yaml
```

**解决方案**: 检查 .env 文件中的 TAVILY_API_KEY 是否正确。

#### 2. 内存不足

```
MemoryError: Unable to allocate array
```

**解决方案**: 增加系统内存或减小 batch_size。

#### 3. 磁盘空间不足

```
OSError: [Errno 28] No space left on device
```

**解决方案**: 清理旧文件或增加磁盘空间。

#### 4. 网络连接问题

```
urllib.error.URLError: <urlopen error [Errno 110] Connection timed out>
```

**解决方案**: 检查网络连接或配置代理。

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python3 scripts/collect_news.py

# 使用 dry-run 模式
python3 scripts/ingest.py --dry-run
```

## 性能优化

### 1. 并发处理

```bash
# 使用异步处理
python3 scripts/ingest.py --use-pipeline
```

### 2. 数据库优化

```python
from storage import Database

db = Database()
db.vacuum()  # 优化数据库
```

### 3. 缓存

启用缓存可以减少 API 调用：

```yaml
# config.yaml
search:
  max_age_days: 7  # 缓存 7 天内的结果
```

## 安全建议

1. **不要提交密钥**: 确保 .env 在 .gitignore 中
2. **定期轮换密钥**: 定期更新 API Key
3. **限制访问权限**: 使用最小权限原则
4. **监控异常**: 关注日志中的异常行为

## 更新

### 更新代码

```bash
cd ~/company-wiki
git pull origin main
pip install -r requirements.txt
```

### 迁移数据

```python
from storage import DataMigrator, Database

db = Database()
migrator = DataMigrator(db, wiki_root)
stats = migrator.migrate_from_yaml()
print(stats)
```

## 更多信息

- [API 文档](API.md)
- [故障排除](TROUBLESHOOTING.md)
- [重构计划](../REFACTORING_PLAN.md)