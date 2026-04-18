#!/bin/bash
# 每日新闻采集 + ingest
cd ~/company-wiki
echo "=== $(date) collect_news ===" >> log_cron.txt
python3 scripts/collect_news.py >> log_cron.txt 2>&1
echo "=== $(date) ingest ===" >> log_cron.txt
python3 scripts/ingest.py >> log_cron.txt 2>&1
echo "=== $(date) done ===" >> log_cron.txt
