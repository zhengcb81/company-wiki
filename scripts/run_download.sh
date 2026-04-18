#!/bin/bash
# 每周财报下载 + ingest
cd ~/company-wiki
echo "=== $(date) download ===" >> log_cron.txt
python3 scripts/batch_download.py >> log_cron.txt 2>&1
echo "=== $(date) ingest ===" >> log_cron.txt
python3 scripts/ingest.py >> log_cron.txt 2>&1
echo "=== $(date) done ===" >> log_cron.txt
