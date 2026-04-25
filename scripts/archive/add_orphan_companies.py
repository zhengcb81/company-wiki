#!/usr/bin/env python3
"""
Add all orphan companies (not in graph.yaml) to the tracking system.
Usage: python scripts/add_orphan_companies.py [--dry-run]
"""
import sys
import re
import yaml
import argparse
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

WIKI_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = WIKI_ROOT / "graph.yaml"


def get_exchange(ticker):
    if not ticker:
        return 'UNKNOWN'
    if ticker.endswith('.HK'):
        return 'HKEX'
    us_tickers = {'TAL', 'BIDU', 'AMD', 'NVDA', 'TSM', 'JD', 'PDD', 'NTES', 'BABA', 'SHEIN', 'BYTE'}
    if ticker in us_tickers or '.' in ticker:
        return 'NASDAQ'
    if ticker.startswith('688') or ticker.startswith('6'):
        return 'SSE'
    if ticker.startswith('0') or ticker.startswith('3') or ticker.startswith('002'):
        return 'SZSE'
    if ticker.startswith('8'):
        return 'BSE'
    return 'SSE'


def extract_tickers_from_filenames():
    """Extract ticker codes from PDF filenames for each orphan company."""
    ticker_map = {}
    for company_dir in sorted((WIKI_ROOT / "companies").iterdir()):
        if not company_dir.is_dir():
            continue
        files = list(company_dir.rglob('*.pdf'))
        if not files:
            continue
        ticker_counts = Counter()
        for f in files:
            name = f.stem
            for pat in [r'-(\d{6})-', r'-(\d{4}\.HK)-', r'-([A-Z]+\.[A-Z]+)-']:
                m = re.search(pat, name)
                if m:
                    ticker_counts[m.group(1)] += 1
        if ticker_counts:
            ticker_map[company_dir.name] = ticker_counts.most_common(1)[0][0]
    return ticker_map


# Manual ticker overrides for companies where auto-detection failed
MANUAL_TICKERS = {
    'SHEIN': 'SHEIN',
    '三联虹普': '300384',
    '中国巨石': '600176',
    '京东': '9618.HK',
    '华住酒店': '1179.HK',
    '华卓精科': '688152',
    '坤彩科技': '603826',
    '好未来': 'TAL',
    '字节跳动': 'BYTE',
    '时代新材': '600458',
    '航发科技': '600391',
    '药明康德': '603259',
    '设计总院': '603357',
    '长江证券': '000783',
}

# Directories that are not real companies
SKIP_DIRS = {'十论"复苏牛"', '_inbox', '未知'}

# Comprehensive sector mapping
COMPANY_SECTORS = {
    # === SEMICONDUCTOR RELATED ===
    '德赛西威': {'sectors': ['GPU与AI芯片'], 'themes': ['AI产业链'], 'position': '智能座舱/自动驾驶芯片龙头'},
    '海康威视': {'sectors': ['GPU与AI芯片', 'AI应用'], 'themes': ['AI产业链'], 'position': '全球安防AI龙头'},
    '中颖电子': {'sectors': ['半导体代工'], 'themes': ['AI产业链'], 'position': 'MCU芯片设计'},
    '苏试试验': {'sectors': ['量检测设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '半导体可靠性试验设备'},
    '菲利华': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '石英玻璃材料龙头'},
    '石英股份': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '高纯石英砂龙头'},
    '三环集团': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '电子陶瓷材料龙头'},
    '杭氧股份': {'sectors': ['电子特气'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '工业气体龙头'},
    '盈建科': {'sectors': ['EDA与IP'], 'themes': ['AI产业链'], 'position': '建筑设计软件'},
    '奥普特': {'sectors': ['量检测设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '机器视觉核心部件'},
    '快克股份': {'sectors': ['半导体设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '精密焊接设备'},
    '联影医疗': {'sectors': ['GPU与AI芯片', 'AI应用'], 'themes': ['AI产业链'], 'position': '高端医疗影像AI龙头'},
    '京东方': {'sectors': ['半导体材料'], 'themes': ['AI产业链'], 'position': '全球显示面板龙头'},
    '至纯科技': {'sectors': ['半导体设备', '清洗设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '高纯工艺系统+清洗设备'},
    '优利德': {'sectors': ['量检测设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '电子测量仪器'},
    '时代电气': {'sectors': ['半导体设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '功率半导体器件+轨道交通'},
    '安博通': {'sectors': ['算力基建'], 'themes': ['AI产业链'], 'position': '网络安全+AI算力安全'},
    '安集科技': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': 'CMP抛光液龙头'},
    '山石网科': {'sectors': ['算力基建'], 'themes': ['AI产业链'], 'position': '网络安全+数据中心安全'},
    '拓斯达': {'sectors': ['半导体设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '工业机器人+注塑设备'},
    '方邦股份': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '电磁屏蔽膜龙头'},
    '鼎龙股份': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': 'CMP抛光垫+光电显示材料'},
    '中望软件': {'sectors': ['EDA与IP'], 'themes': ['AI产业链'], 'position': '国产CAD龙头'},
    '兆易创新': {'sectors': ['GPU与AI芯片'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '存储芯片+MCU龙头'},
    '奥来德': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': 'OLED有机材料龙头'},
    '飞凯材料': {'sectors': ['半导体材料'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '半导体湿电子化学品'},
    '禾信仪器': {'sectors': ['量检测设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '质谱仪国产替代'},
    '雅克科技': {'sectors': ['半导体材料', '电子特气'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '电子特气+光刻胶材料'},
    '华卓精科': {'sectors': ['半导体设备'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '光刻机双工件台国产突破'},
    '卓胜微': {'sectors': ['GPU与AI芯片'], 'themes': ['AI产业链', '半导体国产替代'], 'position': '射频芯片龙头'},
    '虹软科技': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': 'AI视觉算法龙头'},

    # === AI/TECH PLATFORMS ===
    '阿里巴巴': {'sectors': ['算力基建', 'AI应用'], 'themes': ['AI产业链'], 'position': '阿里云+通义大模型'},
    '腾讯': {'sectors': ['算力基建', 'AI应用'], 'themes': ['AI产业链'], 'position': '腾讯云+混元大模型'},
    '拼多多': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '跨境电商Temu+AI推荐'},
    '拓尔思': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': 'NLP/AI内容安全龙头'},
    '字节跳动': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '豆包大模型+TikTok全球AI'},
    '美团': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '本地生活AI+配送自动化'},
    '海天瑞声': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': 'AI训练数据服务龙头'},

    # === INTERNET/MEDIA ===
    '哔哩哔哩': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '视频社区+AI内容推荐'},
    '光线传媒': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '影视+AI影视制作'},
    '快手': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '短视频AI+可灵大模型'},
    '三七互娱': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '游戏+AI游戏开发'},
    '吉比特': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '精品游戏研发'},
    '好未来': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '教育AI龙头'},
    '完美世界': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '游戏+影视+AI'},
    '芒果超媒': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '流媒体+AI内容'},
    '网易': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '游戏+AI+有道大模型'},

    # === MILITARY/AEROSPACE ===
    '航天发展': {'sectors': [], 'themes': ['高端制造'], 'position': '航天防务电子'},
    '中航电测': {'sectors': [], 'themes': ['高端制造'], 'position': '航空测控+成飞集成重组'},
    '航发动力': {'sectors': [], 'themes': ['高端制造'], 'position': '航空发动机龙头'},
    '中航机电': {'sectors': [], 'themes': ['高端制造'], 'position': '航空机电系统'},
    '天马股份': {'sectors': [], 'themes': ['高端制造'], 'position': '通用航空'},
    '中航沈飞': {'sectors': [], 'themes': ['高端制造'], 'position': '战斗机龙头'},
    '七一二': {'sectors': [], 'themes': ['高端制造'], 'position': '军用无线通信'},
    '航发控制': {'sectors': [], 'themes': ['高端制造'], 'position': '航空发动机控制系统'},
    '三角防务': {'sectors': [], 'themes': ['高端制造'], 'position': '航空锻件'},
    '中航光电': {'sectors': [], 'themes': ['高端制造'], 'position': '军工连接器龙头'},
    '中直股份': {'sectors': [], 'themes': ['高端制造'], 'position': '直升机龙头'},
    '中航电子': {'sectors': [], 'themes': ['高端制造'], 'position': '航空电子系统'},
    '中航西飞': {'sectors': [], 'themes': ['高端制造'], 'position': '大飞机龙头'},
    '中航重机': {'sectors': [], 'themes': ['高端制造'], 'position': '航空锻铸造'},
    '派克新材': {'sectors': [], 'themes': ['高端制造'], 'position': '航空航天锻件'},
    '航发科技': {'sectors': [], 'themes': ['高端制造'], 'position': '航空发动机零部件'},

    # === FINANCE ===
    '中信建投': {'sectors': [], 'themes': [], 'position': '头部券商'},
    '中国平安': {'sectors': [], 'themes': [], 'position': '综合金融龙头'},
    '新华保险': {'sectors': [], 'themes': [], 'position': '寿险龙头'},
    '长江证券': {'sectors': [], 'themes': [], 'position': '中部券商'},

    # === MEDICAL/PHARMA ===
    '恩华药业': {'sectors': [], 'themes': [], 'position': '中枢神经系统用药龙头'},
    '迈瑞医疗': {'sectors': [], 'themes': ['高端制造'], 'position': '医疗器械龙头'},
    '药明生物': {'sectors': [], 'themes': [], 'position': '生物药CXO龙头'},
    '百济神州': {'sectors': [], 'themes': [], 'position': '创新药国际化龙头'},
    '中国生物制药': {'sectors': [], 'themes': [], 'position': '仿制药+创新药'},
    '信达生物': {'sectors': [], 'themes': [], 'position': '创新药龙头'},
    '时代天使': {'sectors': [], 'themes': [], 'position': '隐形正畸龙头'},
    '普门科技': {'sectors': [], 'themes': [], 'position': '体外诊断+康复设备'},
    '微创医疗': {'sectors': [], 'themes': [], 'position': '高端医疗器械'},
    '安杰思': {'sectors': [], 'themes': [], 'position': '消化内镜诊疗器械'},
    '康基医疗': {'sectors': [], 'themes': [], 'position': '微创外科手术器械'},
    '康拓医疗': {'sectors': [], 'themes': [], 'position': '神经外科植入物'},
    '惠泰医疗': {'sectors': [], 'themes': [], 'position': '电生理+血管介入'},
    '新产业': {'sectors': [], 'themes': [], 'position': '体外诊断化学发光'},
    '石药集团': {'sectors': [], 'themes': [], 'position': '创新药+仿制药'},
    '贝泰妮': {'sectors': [], 'themes': [], 'position': '功效护肤品龙头'},
    '药明康德': {'sectors': [], 'themes': [], 'position': '全球CXO龙头'},

    # === CHEMICAL/MATERIAL ===
    '密尔克卫': {'sectors': ['电子特气'], 'themes': ['AI产业链'], 'position': '化工供应链+电子特气分销'},
    '万华化学': {'sectors': [], 'themes': [], 'position': '全球MDI龙头'},
    '百傲化学': {'sectors': [], 'themes': [], 'position': '工业杀菌剂龙头'},
    '万润股份': {'sectors': [], 'themes': [], 'position': '功能性材料'},
    '国恩股份': {'sectors': [], 'themes': [], 'position': '高分子材料'},
    '德林海': {'sectors': [], 'themes': [], 'position': '蓝藻治理'},
    '三德科技': {'sectors': [], 'themes': [], 'position': '煤质检测仪器'},
    '溢多利': {'sectors': [], 'themes': [], 'position': '生物酶制剂'},
    '苏博特': {'sectors': [], 'themes': [], 'position': '混凝土外加剂龙头'},
    '道氏技术': {'sectors': [], 'themes': [], 'position': '陶瓷材料+新能源材料'},
    '阿拉丁': {'sectors': [], 'themes': [], 'position': '科研试剂龙头'},

    # === CONSUMER/RETAIL ===
    '分众传媒': {'sectors': [], 'themes': [], 'position': '梯媒龙头'},
    '小米集团': {'sectors': ['算力基建'], 'themes': ['AI产业链'], 'position': 'AIoT+小米汽车+大模型'},
    '周大生': {'sectors': [], 'themes': [], 'position': '珠宝连锁'},
    '海底捞': {'sectors': [], 'themes': [], 'position': '火锅连锁龙头'},
    '欧派家居': {'sectors': [], 'themes': [], 'position': '定制家居龙头'},
    '索菲亚': {'sectors': [], 'themes': [], 'position': '定制家居'},
    '尚品宅配': {'sectors': [], 'themes': [], 'position': '全屋定制'},
    '广州酒家': {'sectors': [], 'themes': [], 'position': '食品+餐饮'},
    '养元饮品': {'sectors': [], 'themes': [], 'position': '六个核桃'},
    '丸美股份': {'sectors': [], 'themes': [], 'position': '眼部护肤品'},
    '绝味食品': {'sectors': [], 'themes': [], 'position': '卤味连锁龙头'},
    '地素时尚': {'sectors': [], 'themes': [], 'position': '中高端女装'},
    '老凤祥': {'sectors': [], 'themes': [], 'position': '黄金珠宝龙头'},
    '飞亚达': {'sectors': [], 'themes': [], 'position': '手表龙头'},
    '歌力思': {'sectors': [], 'themes': [], 'position': '高级女装'},
    '洋河股份': {'sectors': [], 'themes': [], 'position': '白酒龙头'},
    '珀莱雅': {'sectors': [], 'themes': [], 'position': '化妆品龙头'},
    '三只松鼠': {'sectors': [], 'themes': [], 'position': '休闲食品电商'},
    '海澜之家': {'sectors': [], 'themes': [], 'position': '男装龙头'},
    '潮宏基': {'sectors': [], 'themes': [], 'position': '时尚珠宝'},
    '五芳斋': {'sectors': [], 'themes': [], 'position': '粽子龙头'},
    '古井贡酒': {'sectors': [], 'themes': [], 'position': '区域白酒龙头'},
    '桃李面包': {'sectors': [], 'themes': [], 'position': '短保面包龙头'},
    '洽洽食品': {'sectors': [], 'themes': [], 'position': '坚果炒货龙头'},
    '妙可蓝多': {'sectors': [], 'themes': [], 'position': '奶酪龙头'},

    # === FURNITURE/INDUSTRIAL ===
    '北新建材': {'sectors': [], 'themes': [], 'position': '石膏板龙头'},
    '东睦股份': {'sectors': [], 'themes': ['高端制造'], 'position': '粉末冶金龙头'},
    '博威合金': {'sectors': [], 'themes': [], 'position': '高端铜合金材料'},
    '华锐精密': {'sectors': [], 'themes': ['高端制造'], 'position': '数控刀具国产替代'},
    '开润股份': {'sectors': [], 'themes': [], 'position': '箱包代工'},
    '弘亚数控': {'sectors': [], 'themes': ['高端制造'], 'position': '板式家具机械龙头'},
    '东方雨虹': {'sectors': [], 'themes': [], 'position': '防水材料龙头'},
    '伟星新材': {'sectors': [], 'themes': [], 'position': 'PPR管材龙头'},
    '华利集团': {'sectors': [], 'themes': [], 'position': '运动鞋代工龙头'},
    '中大力德': {'sectors': [], 'themes': ['高端制造'], 'position': '精密减速器'},
    '共创草坪': {'sectors': [], 'themes': [], 'position': '人造草坪龙头'},
    '恒锋工具': {'sectors': [], 'themes': ['高端制造'], 'position': '精密复杂刀具'},
    '欧科亿': {'sectors': [], 'themes': ['高端制造'], 'position': '数控刀片龙头'},
    '双环传动': {'sectors': [], 'themes': ['高端制造'], 'position': '齿轮龙头'},
    '埃斯顿': {'sectors': [], 'themes': ['高端制造'], 'position': '工业机器人龙头'},

    # === ENERGY/UTILITIES ===
    '时代新材': {'sectors': [], 'themes': [], 'position': '高分子材料+风电叶片'},
    '玲珑轮胎': {'sectors': [], 'themes': [], 'position': '轮胎龙头'},
    '上峰水泥': {'sectors': [], 'themes': [], 'position': '水泥区域龙头'},
    '凯赛生物': {'sectors': [], 'themes': [], 'position': '生物基材料龙头'},
    '大全能源': {'sectors': [], 'themes': [], 'position': '多晶硅龙头'},
    '天宜上佳': {'sectors': [], 'themes': [], 'position': '高铁刹车片+碳碳复合材料'},
    '方大特钢': {'sectors': [], 'themes': [], 'position': '特钢龙头'},
    '赛轮轮胎': {'sectors': [], 'themes': [], 'position': '轮胎龙头'},
    '亿华通': {'sectors': [], 'themes': [], 'position': '氢燃料电池龙头'},
    '福斯特': {'sectors': [], 'themes': [], 'position': '光伏胶膜龙头'},

    # === OTHER ===
    '金禾实业': {'sectors': [], 'themes': [], 'position': '甜味剂龙头'},
    '视觉中国': {'sectors': ['AI应用'], 'themes': ['AI产业链'], 'position': '图片版权+AI生成'},
    '华铁应急': {'sectors': [], 'themes': [], 'position': '高空作业平台租赁'},
    '长安汽车': {'sectors': [], 'themes': [], 'position': '汽车+智能驾驶'},
    '锦江股份': {'sectors': [], 'themes': [], 'position': '酒店连锁龙头'},
    '世茂': {'sectors': [], 'themes': [], 'position': '房地产'},
    '广联达': {'sectors': ['EDA与IP'], 'themes': [], 'position': '建筑信息化龙头'},
    '东珠生态': {'sectors': [], 'themes': [], 'position': '生态修复'},
    '明源云': {'sectors': [], 'themes': [], 'position': '地产SaaS'},
    '雪榕生物': {'sectors': [], 'themes': [], 'position': '食用菌龙头'},
    '星网宇达': {'sectors': [], 'themes': ['高端制造'], 'position': '惯性导航+无人机'},
    '陆家嘴': {'sectors': [], 'themes': [], 'position': '商业地产'},
    '三联虹普': {'sectors': [], 'themes': [], 'position': '锦纶工程技术服务'},
    '伊利股份': {'sectors': [], 'themes': [], 'position': '乳制品龙头'},
    '绿茵生态': {'sectors': [], 'themes': [], 'position': '生态园林'},
    '设计总院': {'sectors': [], 'themes': [], 'position': '工程设计咨询'},
    '万科': {'sectors': [], 'themes': [], 'position': '房地产龙头'},
    '光明乳业': {'sectors': [], 'themes': [], 'position': '乳制品'},
    '八方股份': {'sectors': [], 'themes': [], 'position': '电机龙头'},
    '华住酒店': {'sectors': [], 'themes': [], 'position': '酒店连锁龙头'},
    '国检集团': {'sectors': ['量检测设备'], 'themes': [], 'position': '第三方检测龙头'},
    '坤彩科技': {'sectors': [], 'themes': [], 'position': '珠光材料龙头'},
    '沃尔德': {'sectors': [], 'themes': ['高端制造'], 'position': '超硬刀具材料'},
    'SHEIN': {'sectors': [], 'themes': [], 'position': '全球快时尚跨境电商'},
    '世华科技': {'sectors': [], 'themes': [], 'position': '复合功能性材料'},
    '春秋航空': {'sectors': [], 'themes': [], 'position': '低成本航空龙头'},
    '美凯龙': {'sectors': [], 'themes': [], 'position': '家居零售龙头'},
    '富森美': {'sectors': [], 'themes': [], 'position': '家居卖场'},
    '格力电器': {'sectors': [], 'themes': [], 'position': '家电龙头'},
    '梦百合': {'sectors': [], 'themes': [], 'position': '记忆棉床垫龙头'},
    '爱婴室': {'sectors': [], 'themes': [], 'position': '母婴连锁'},
    '玉禾田': {'sectors': [], 'themes': [], 'position': '环卫服务'},
    '祥源新材': {'sectors': [], 'themes': [], 'position': '聚烯烃发泡材料'},
    '科思科技': {'sectors': [], 'themes': [], 'position': '军工电子信息'},
    '京东': {'sectors': ['算力基建', 'AI应用'], 'themes': ['AI产业链'], 'position': '电商+京东云+AI'},
    '泽达易盛': {'sectors': [], 'themes': [], 'position': '信息技术服务'},
    '中国巨石': {'sectors': [], 'themes': [], 'position': '玻璃纤维龙头'},
}


def main():
    parser = argparse.ArgumentParser(description='Add orphan companies to graph.yaml')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()

    with open(GRAPH_PATH, 'r', encoding='utf-8') as f:
        graph = yaml.safe_load(f)

    tracked = set(graph.get('companies', {}).keys())
    print(f"Currently tracked: {len(tracked)} companies")

    # Build ticker map
    ticker_map = extract_tickers_from_filenames()
    ticker_map.update({k: v for k, v in MANUAL_TICKERS.items() if v})

    # Find orphan companies with files
    orphan_companies = []
    for company_dir in sorted((WIKI_ROOT / "companies").iterdir()):
        name = company_dir.name
        if not company_dir.is_dir() or name in tracked or name in SKIP_DIRS:
            continue
        files = [f for f in company_dir.rglob('*')
                 if f.is_file() and 'wiki' not in f.parts and '.ingested' not in f.parts]
        if files:
            orphan_companies.append((name, len(files)))

    print(f"Orphan companies with files: {len(orphan_companies)}")

    # Build new entries
    new_entries = {}
    for name, file_count in orphan_companies:
        ticker = ticker_map.get(name, '')
        info = COMPANY_SECTORS.get(name, {'sectors': [], 'themes': [], 'position': ''})

        entry = {
            'ticker': str(ticker) if ticker else '',
            'exchange': get_exchange(ticker),
            'sectors': info['sectors'],
            'themes': info['themes'],
            'news_queries': [f'{name} 最新消息'],
            'position': info['position'],
        }

        # Add ticker as alias for A-share
        if ticker and not any(c.isalpha() and c not in '.HK' for c in ticker):
            entry['aliases'] = [str(ticker)]

        new_entries[name] = entry

    # Statistics
    sector_count = Counter()
    for info in new_entries.values():
        for s in info['sectors']:
            sector_count[s] += 1

    print(f"\nNew companies to add: {len(new_entries)}")
    print("\nSector distribution:")
    for s, c in sector_count.most_common():
        print(f"  {s}: {c} companies")
    no_sector = sum(1 for v in new_entries.values() if not v['sectors'])
    print(f"  (no sector): {no_sector} companies")

    if args.dry_run:
        print("\n[DRY RUN] No changes written.")
        # Print sample entries
        print("\nSample entries:")
        for name in list(new_entries.keys())[:5]:
            import json
            print(f"  {name}: {json.dumps(new_entries[name], ensure_ascii=False)}")
        return

    # Add to graph.yaml
    graph['companies'].update(new_entries)

    with open(GRAPH_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(graph, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\nAdded {len(new_entries)} companies to graph.yaml")
    print(f"Total tracked companies: {len(graph['companies'])}")


if __name__ == '__main__':
    main()
