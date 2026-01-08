#!/usr/bin/env python3
"""
RedLens 数据工厂 - 数据融合模块
将英超官方赛程与咪咕视频链接融合
"""

import json
import logging
from typing import List, Dict

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 文件路径
OFFICIAL_FILE = "matches.json"          # 英超官方赛程
MIGU_FILE = "migu_videos_complete.json" # 咪咕视频数据
OUTPUT_FILE = "matches_with_videos.json" # 最终融合数据
MAPPING_FILE = "team_name_mapping.json" # 队名翻译映射表


def merge_data() -> List[Dict]:
    """
    数据融合：将咪咕录像链接添加到官方赛程中
    
    匹配策略：日期 + 对手名称（支持中英文翻译）
    """
    logger.info("🔄 开始数据融合...")
    
    # 读取数据
    with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
        official_matches = json.load(f)
    
    with open(MIGU_FILE, 'r', encoding='utf-8') as f:
        migu_matches = json.load(f)
    
    # 读取队名翻译映射表
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        team_mapping = json.load(f)
    
    logger.info(f"📊 官方赛程: {len(official_matches)} 场")
    logger.info(f"📹 咪咕视频: {len(migu_matches)} 场")
    
    # 建立咪咕数据的快速查找索引
    migu_index = {}
    for migu_match in migu_matches:
        # 使用日期作为键
        date = migu_match['date']
        if date not in migu_index:
            migu_index[date] = []
        migu_index[date].append(migu_match)
    
    # 融合数据
    merged_matches = []
    match_count = 0
    
    for official in official_matches:
        date = official['date']
        opponent = official['opponent']
        
        # 创建融合后的数据（基于官方赛程）
        merged = official.copy()
        
        # 尝试匹配咪咕数据
        if date in migu_index:
            # 将英文队名翻译为中文
            opponent_cn = team_mapping.get(opponent, opponent)
            
            # 在同一天的咪咕数据中查找对手匹配的比赛
            for migu in migu_index[date]:
                migu_opponent = migu['opponent']
                
                # 对手名称匹配（支持中英文）
                if (opponent_cn == migu_opponent or 
                    opponent == migu_opponent or
                    opponent_cn in migu_opponent or 
                    migu_opponent in opponent_cn):
                    # 添加录像信息
                    merged['migu_pid'] = migu.get('pid', '')
                    merged['migu_detail_url'] = migu.get('detail_url', '')
                    merged['migu_live_url'] = migu.get('live_url', '')
                    match_count += 1
                    logger.info(f"✅ 匹配: {date} vs {opponent} ({opponent_cn}) -> PID: {migu.get('pid', '')}")
                    break
        
        # 如果没有匹配到，设置为空字符串
        if 'migu_pid' not in merged:
            merged['migu_pid'] = ''
            merged['migu_detail_url'] = ''
            merged['migu_live_url'] = ''
        
        merged_matches.append(merged)
    
    logger.info(f"\n📊 融合结果:")
    logger.info(f"   总场次: {len(merged_matches)} 场")
    logger.info(f"   成功匹配: {match_count} 场")
    logger.info(f"   未匹配: {len(merged_matches) - match_count} 场")
    
    return merged_matches


def save_merged_data(matches: List[Dict]):
    """保存融合后的数据"""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 融合数据已保存至 {OUTPUT_FILE}")
        
        # 统计
        with_video = sum(1 for m in matches if m.get('migu_pid'))
        finished = sum(1 for m in matches if m.get('status') == 'C')
        upcoming = len(matches) - finished
        
        logger.info(f"📊 数据统计:")
        logger.info(f"   已完赛: {finished} 场")
        logger.info(f"   未完赛: {upcoming} 场")
        logger.info(f"   有录像: {with_video} 场")
        
        if with_video > 0:
            logger.info(f"\n📹 录像链接示例（前3场）:")
            count = 0
            for m in matches:
                if m.get('migu_detail_url'):
                    logger.info(f"   {m['date']} {m['time']} {'主场' if m['is_home'] else '客场'} vs {m['opponent']}")
                    logger.info(f"      {m['migu_detail_url']}")
                    count += 1
                    if count >= 3:
                        break
        
    except Exception as e:
        logger.error(f"❌ 保存文件失败: {str(e)}")
        raise


def main():
    """主函数"""
    try:
        merged_matches = merge_data()
        save_merged_data(merged_matches)
        logger.info("\n✅ 数据融合完成!")
        
    except FileNotFoundError as e:
        logger.error(f"\n❌ 文件不存在: {str(e)}")
        logger.error("请先运行:")
        logger.error("  1. python3 fetch_fixtures.py  # 获取官方赛程")
        logger.error("  2. python3 fetch_all_migu_videos.py  # 获取咪咕视频")
    except Exception as e:
        logger.error(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

