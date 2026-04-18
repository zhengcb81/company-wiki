# 问题根本原因分析与修复

## 一、问题现象

从几天前到现在，下载的文件没有放到正确位置，导致：
1. 文件下载到了 `~/StockInfoDownloader/downloads` 而不是 `~/company-wiki/companies`
2. 需要手动从 Windows 目录同步文件
3. 分类脚本运行后，很多文档仍然缺失

## 二、根本原因

### 原因1：配置不一致

**config.yaml** (company-wiki):
```yaml
report_downloader:
  save_dir: "~/company-wiki/companies"  # 正确配置
```

**config.json** (StockInfoDownloader):
```json
{
  "save_dir": "downloads"  // ❌ 相对路径，实际保存到 ~/StockInfoDownloader/downloads
}
```

### 原因2：代码逻辑错误

**download_reports.py** 的问题：

```python
# 问题代码
def run_download(stock_code, company_name, page_suffix):
    # 1. 修改 config.json
    config["save_dir"] = str(WIKI_COMPANIES)
    
    # 2. 调用 StockInfoDownloader
    result = subprocess.run(...)
    
    # 3. 检查文件 - 但文件可能在错误位置！
    wiki_company_dir = WIKI_COMPANIES / company_name / "raw"
    if wiki_company_dir.exists():
        files = list(wiki_company_dir.rglob("*.pdf"))
```

**问题**：
1. 虽然修改了 config.json，但 StockInfoDownloader 可能不读取
2. 检查文件时，文件可能还没下载完
3. 文件实际下载到了 `~/StockInfoDownloader/downloads`

### 原因3：organize_files 函数永远不会被调用

```python
def main():
    files = run_download(...)
    if files:  # 如果 run_download 返回空列表
        organize_files(...)  # 这行永远不会执行
```

因为 `run_download()` 检查的是错误的目录，返回空列表。

## 三、修复方案

### 修复1：直接修改 StockInfoDownloader 的 config.json

```bash
# 将 save_dir 改为绝对路径
{
  "save_dir": "/home/zhengcb/company-wiki/companies"
}
```

### 修复2：重写下载流程

新的 `download_reports_v2.py` 实现：

```python
def run_download(stock_code, company_name, page_suffix):
    # 1. 更新配置并验证
    target_dir = update_config(stock_code, company_name, page_suffix)
    
    # 2. 运行下载
    result = subprocess.run(...)
    
    # 3. 检查多个可能的位置
    # 首先检查目标目录
    if target_dir.exists():
        files = list(target_dir.rglob("*.pdf"))
        if files:
            return files
    
    # 然后检查 Windows downloads 目录
    windows_dir = WINDOWS_DOWNLOADS / company_name
    if windows_dir.exists():
        files = list(windows_dir.glob("*.pdf"))
        if files:
            return files
    
    return []
```

### 修复3：添加同步功能

```python
def sync_from_windows(company_name):
    """从 Windows 目录同步文件到 wiki"""
    # 1. 查找 Windows 目录
    # 2. 分类文件
    # 3. 复制到正确的 wiki 子目录
```

## 四、预防措施

### 1. 配置验证

在每次下载前验证配置：
```python
def check_config():
    # 检查 save_dir 是否是绝对路径
    # 检查目录是否存在
    # 检查权限
```

### 2. 路径统一

所有路径使用绝对路径：
```python
DOWNLOADER_DIR = Path.home() / "StockInfoDownloader"
WIKI_COMPANIES = Path.home() / "company-wiki" / "companies"
WINDOWS_DOWNLOADS = Path("/mnt/c/Users/.../downloads")
```

### 3. 下载后验证

每次下载后验证文件位置：
```python
def verify_download(company_name, expected_files):
    # 检查文件是否在正确位置
    # 如果在错误位置，自动复制
```

### 4. 日志记录

详细记录每次操作：
```python
def log(message):
    # 记录到 log.md
    # 包含时间戳、操作类型、结果
```

## 五、使用方法

### 检查配置
```bash
python3 scripts/download_reports_v2.py --check
```

### 下载文档
```bash
# 下载所有公司
python3 scripts/download_reports_v2.py

# 下载指定公司
python3 scripts/download_reports_v2.py --company 中微公司

# 同步 Windows 目录的文件
python3 scripts/download_reports_v2.py --sync
```

## 六、测试验证

运行以下命令验证修复效果：

```bash
# 1. 检查配置
python3 scripts/download_reports_v2.py --check

# 2. 测试下载（单个公司）
python3 scripts/download_reports_v2.py --company 中微公司 --pages periodicReports

# 3. 验证文件位置
ls -la ~/company-wiki/companies/中微公司/raw/financial_reports/
```

## 七、总结

**根本原因**：
1. StockInfoDownloader 的 config.json 使用相对路径
2. download_reports.py 没有验证配置是否生效
3. 文件收集逻辑错误

**修复方案**：
1. 修改 config.json 为绝对路径
2. 重写下载流程，添加验证
3. 添加从 Windows 目录同步的功能

**预防措施**：
1. 配置验证
2. 路径统一
3. 下载后验证
4. 详细日志