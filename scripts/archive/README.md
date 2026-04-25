# 归档脚本

本目录存放已废弃的旧版脚本和一次性工具，仅供参考。

## v1 脚本（已被 v2 替代）

| 脚本 | 替代 | 说明 |
|------|------|------|
| `extract.py` | `extract_v2.py` | 旧版文档提取 |
| `ingest.py` | `ingest_v2.py` | 旧版 ingest，存在交叉污染问题 |
| `ingest_with_llm.py` | `ingest_v2.py` | LLM ingest 实验版 |
| `pdf_extract.py` | `pdf_extract_v2.py` | 旧版 PDF 提取 |

## 一次性工具

| 脚本 | 用途 |
|------|------|
| `add_orphan_companies.py` | 将孤儿公司加入 graph.yaml |
| `backfill_metadata.py` | 回填 wiki 页面元数据 |
| `backfill_wikilinks.py` | 回填 wiki 链接 |
| `clean_sector_contamination.py` | 清理行业页面交叉污染 |
| `clean_sectors.py` | 清理行业数据 |
| `cleanup_contamination.py` | 污染清理（可执行版） |
| `download_missing_docs.py` | 下载缺失文档 |
| `fix_duplicates.py` | 修复重复条目 |
| `fix_encoding.py` | 修复文件编码 |
| `fix_wiki_encoding.py` | 修复 wiki 编码 |
| `import_frameworks.py` | 导入分析框架 |
| `import_from_dropbox.py` | 从 Dropbox 导入数据 |
| `organize_files.py` | 文件组织整理 |
| `reclassify_frameworks.py` | 框架重分类 |
| `remove_report_titles.py` | 移除报告标题 |
| `remove_title_dumps.py` | 移除标题转储 |
| `retry_parse_errors.py` | 重试解析错误 |
