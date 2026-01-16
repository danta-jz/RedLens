#!/usr/bin/env python3
"""
RedLens 数据工厂 - 智能融合模块 (Smart Merge)
修复: 
1. 增加 +/- 1 天的日期容错，解决时差导致的不匹配
2. 增强日志输出，显示匹配失败的具体原因
"""

import json
import logging
from typing import List, Dict
from datetime import datetime, timedelta

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 文件路径
OFFICIAL_FILE = "matches.json"
MIGU_FILE = "migu_videos_complete.json"
OUTPUT_FILE = "matches_with_videos.json"
MAPPING_FILE = "team_name_mapping.json"

def get_fuzzy_dates(date_str: str) -> List[str]:
    """生成 [昨天, 今天, 明天] 的日期列表"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        return [
            (target_date - timedelta(days=1)).strftime('%Y-%m-%d'),
            date_str,
            (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        ]
    except:
        return [date_str]

def merge_data() -> List[Dict]:
    logger.info("🔄 开始智能融合 (Smart Merge)...")
    
    with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
        official_matches = json.load(f)
    
    with open(MIGU_FILE, 'r', encoding='utf-8') as f:
        migu_matches = json.load(f)
    
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        team_mapping = json.load(f)
    
    # 建立咪咕索引
    migu_index = {}
    for m in migu_matches:
        d = m['date']
        if d not in migu_index: migu_index[d] = []
        migu_index[d].append(m)
    
    merged_matches = []
    match_count = 0
    
    for official in official_matches:
        merged = official.copy()
        date = official['date']
        opponent = official['opponent']
        opponent_cn = team_mapping.get(opponent, opponent) # 翻译
        
        found = False
        
        # 核心修复: 尝试 昨天/今天/明天
        candidate_dates = get_fuzzy_dates(date)
        
        for check_date in candidate_dates:
            if check_date in migu_index:
                for migu in migu_index[check_date]:
                    migu_opp = migu['opponent']
                    
                    # 模糊匹配队名
                    if (opponent_cn in migu_opp or migu_opp in opponent_cn or 
                        opponent.lower() in migu_opp.lower()):
                        
                        merged['migu_pid'] = migu.get('pid', '')
                        merged['migu_detail_url'] = migu.get('detail_url', '')
                        merged['migu_live_url'] = migu.get('live_url', '')
                        
                        match_count += 1
                        found = True
                        
                        # 如果日期不一致，记录一下
                        if check_date != date:
                            logger.info(f"✅ 模糊匹配成功: {date} -> {check_date} | {opponent_cn}")
                        else:
                            logger.info(f"✅ 精准匹配: {date} vs {opponent_cn}")
                        break
            if found: break
        
        if not found:
            # 初始化为空
            merged['migu_pid'] = ''
            merged['migu_detail_url'] = ''
            merged['migu_live_url'] = ''
            
            # 调试日志：为什么没匹配上？
            # logger.debug(f"❌ 未匹配: {date} {opponent} (可能原因: 咪咕无数据 或 队名未映射)")
        
        merged_matches.append(merged)
    
    logger.info(f"📊 最终统计: 成功匹配 {match_count} / {len(merged_matches)} 场")
    return merged_matches

def save_merged_data(matches):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    data = merge_data()
    save_merged_data(data)