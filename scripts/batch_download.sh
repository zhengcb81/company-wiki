#!/bin/bash
# 批量下载所有 A 股公司的财报和投资者关系文档
# 每家公司: 3年财报(3页≈90份) + 投资者关系(2页≈60份)
# 预计总耗时: 40家公司 × 2类型 × ~3分钟 = ~4小时

cd ~/StockInfoDownloader
WIKI=~/company-wiki
LOG="$WIKI/log.md"

# A 股公司列表（从 graph.yaml 提取）
COMPANIES=$(python3 -c "
import yaml
with open('$WIKI/graph.yaml') as f:
    g = yaml.safe_load(f)
a_share = {'SSE STAR', 'SSE', 'SZSE', 'BSE'}
for name, info in g['companies'].items():
    if info.get('exchange') in a_share:
        print(f\"{info['ticker']}|{name}\")
")

echo "$(date): Batch download started" >> "$LOG"

# 定期报告
echo "=== 定期报告 ==="
for entry in $COMPANIES; do
    CODE=$(echo "$entry" | cut -d'|' -f1)
    NAME=$(echo "$entry" | cut -d'|' -f2)
    
    # 跳过已有财报的公司
    EXISTING=$(ls "$WIKI/companies/$NAME/raw/reports/"*.pdf 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 5 ]; then
        echo "SKIP $NAME ($EXISTING reports exist)"
        continue
    fi
    
    echo "$(date): Downloading reports for $NAME ($CODE)" >> "$LOG"
    
    # 写配置
    python3 -c "
import json
with open('config.json') as f:
    c = json.load(f)
c['pages'] = [{'name':'定期报告','suffix':'periodicReports','max_pages':3}]
c['companies'] = [{'stock_code':'$CODE','company_name':'$NAME','enabled':True,'priority':1}]
with open('config.json','w') as f:
    json.dump(c, f, ensure_ascii=False, indent=2)
"
    # 清理旧下载
    rm -rf "downloads/$NAME"
    
    # 下载（10分钟超时）
    timeout 600 python3 main.py "$CODE" 2>/dev/null
    
    # 搬到 wiki
    if [ -d "downloads/$NAME" ]; then
        mkdir -p "$WIKI/companies/$NAME/raw/reports"
        cp downloads/$NAME/*.pdf "$WIKI/companies/$NAME/raw/reports/" 2>/dev/null
        COUNT=$(ls "$WIKI/companies/$NAME/raw/reports/"*.pdf 2>/dev/null | wc -l)
        echo "  $NAME: $COUNT reports"
    fi
    
    sleep 2
done

# 投资者关系
echo "=== 投资者关系 ==="
for entry in $COMPANIES; do
    CODE=$(echo "$entry" | cut -d'|' -f1)
    NAME=$(echo "$entry" | cut -d'|' -f2)
    
    EXISTING=$(ls "$WIKI/companies/$NAME/raw/research/"*.pdf 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 3 ]; then
        echo "SKIP $NAME ($EXISTING IR docs exist)"
        continue
    fi
    
    echo "$(date): Downloading IR for $NAME ($CODE)" >> "$LOG"
    
    python3 -c "
import json
with open('config.json') as f:
    c = json.load(f)
c['pages'] = [{'name':'投资者关系','suffix':'research','allowed_keywords':['投资者关系活动记录表','投资者关系管理信息'],'max_pages':2}]
c['companies'] = [{'stock_code':'$CODE','company_name':'$NAME','enabled':True,'priority':1}]
with open('config.json','w') as f:
    json.dump(c, f, ensure_ascii=False, indent=2)
"
    rm -rf "downloads/$NAME"
    timeout 600 python3 main.py "$CODE" 2>/dev/null
    
    if [ -d "downloads/$NAME" ]; then
        mkdir -p "$WIKI/companies/$NAME/raw/research"
        cp downloads/$NAME/*.pdf "$WIKI/companies/$NAME/raw/research/" 2>/dev/null
        COUNT=$(ls "$WIKI/companies/$NAME/raw/research/"*.pdf 2>/dev/null | wc -l)
        echo "  $NAME: $COUNT IR docs"
    fi
    
    sleep 2
done

echo "$(date): Batch download completed" >> "$LOG"
echo "DONE"
