#!/usr/bin/env python3
"""
RedLens Deep Link Generator (修复版)
功能: 
1. 为已完赛且有录像的比赛生成 VOD Scheme (WORLDCUP_DETAIL + PID)
2. 为未完赛的比赛生成 Live Scheme (WORLDCUP_DETAIL + MgdbID)
3. 修复: 直播 Scheme 采用与 H5 抓包一致的 WORLDCUP_DETAIL 结构
"""

import json
import logging
import urllib.parse
import re

# 配置
INPUT_FILE = "matches_with_videos.json"
OUTPUT_FILE = "matches_with_videos.json" # 覆写自身

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def generate_scheme(match):
    """
    核心逻辑: 
    优先生成录像跳转 (PID)
    其次生成直播跳转 (Live URL/MgdbID)
    """
    
    # --- 1. 尝试生成录像 Scheme (优先级最高) ---
    pid = match.get('migu_pid', '')
    if pid:
        # 录像跳转 (WORLDCUP_DETAIL)
        live_url = match.get('migu_live_url', '')
        mgdb_id = ""
        if live_url:
            match_id = re.search(r'live/(\d+)', live_url)
            if match_id:
                mgdb_id = match_id.group(1)
                
        action_params = {
            "type": "JUMP_INNER_NEW_PAGE",
            "params": {
                "frameID": "default-frame",
                "pageID": "WORLDCUP_DETAIL",
                "location": "h5_share",
                "contentID": str(pid), # 录像 PID
                "extra": {}
            }
        }
        if mgdb_id:
            action_params["params"]["extra"]["mgdbID"] = str(mgdb_id)

        json_str = json.dumps(action_params)
        encoded_json = urllib.parse.quote(json_str)
        return f"miguvideo://miguvideo?action={encoded_json}", "VOD"

    # --- 2. 尝试生成直播 Scheme (优先级次之) ---
    live_url = match.get('migu_live_url', '')
    if live_url:
        # 从 URL 中提取直播间 ID (mgdbId)
        match_id = re.search(r'live/(\d+)', live_url)
        if match_id:
            mgdb_id = match_id.group(1)
            
            # 【核心修复】直播跳转也使用 WORLDCUP_DETAIL
            # 根据抓包: ...share","extra":{"mgdbID":"..."}}}
            action_params = {
                "type": "JUMP_INNER_NEW_PAGE",
                "params": {
                    "frameID": "default-frame",
                    "pageID": "WORLDCUP_DETAIL",  # 之前是 LIVE_DETAIL，现在改为 WORLDCUP_DETAIL
                    "location": "h5_share",       # 补全 location
                    "contentID": str(mgdb_id),    # 直播时，contentID 填 mgdbId
                    "extra": {
                        "mgdbID": str(mgdb_id)    # 关键：extra 里必须有 mgdbID
                    }
                }
            }
            json_str = json.dumps(action_params)
            encoded_json = urllib.parse.quote(json_str)
            return f"miguvideo://miguvideo?action={encoded_json}", "LIVE"
            
    return "", "NONE"

def process_links():
    logger.info("🔗 开始生成 Deep Links (修复版)...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            matches = json.load(f)
            
        updated_count = 0
        live_count = 0
        vod_count = 0
        
        for match in matches:
            scheme, link_type = generate_scheme(match)
            match['scheme_url'] = scheme
            
            if link_type != "NONE":
                updated_count += 1
                if link_type == "LIVE": live_count += 1
                elif link_type == "VOD": vod_count += 1

        # 保存回文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✅ 处理完成!")
        logger.info(f"   总链接数: {updated_count}")
        logger.info(f"   📼 录像链接: {vod_count}")
        logger.info(f"   🔴 直播链接: {live_count} (已采用抓包结构)")
        
    except Exception as e:
        logger.error(f"❌ 失败: {e}")

if __name__ == "__main__":
    process_links()