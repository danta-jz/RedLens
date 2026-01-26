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
    支持多语言 PID（中文/粤语）
    """
    
    # --- 1. 尝试生成录像 Scheme (优先级最高) ---
    pid = match.get('migu_pid', '')
    pid_mandarin = match.get('migu_pid_mandarin', '')
    pid_cantonese = match.get('migu_pid_cantonese', '')
    
    schemes = {}  # 存储多个语言版本的 scheme
    
    def _generate_vod_scheme(pid_value, mgdb_id=''):
        """生成 VOD scheme 的辅助函数"""
        if not pid_value:
            return None
        
        action_params = {
            "type": "JUMP_INNER_NEW_PAGE",
            "params": {
                "frameID": "default-frame",
                "pageID": "WORLDCUP_DETAIL",
                "location": "h5_share",
                "contentID": str(pid_value),  # 录像 PID
                "extra": {}
            }
        }
        if mgdb_id:
            action_params["params"]["extra"]["mgdbID"] = str(mgdb_id)
        
        json_str = json.dumps(action_params)
        encoded_json = urllib.parse.quote(json_str)
        return f"miguvideo://miguvideo?action={encoded_json}"
    
    # 获取 mgdb_id
    live_url = match.get('migu_live_url', '')
    mgdb_id = ""
    if live_url:
        match_id = re.search(r'live/(\d+)', live_url)
        if match_id:
            mgdb_id = match_id.group(1)
    
    # 生成主 PID scheme
    if pid:
        schemes['scheme_url'] = _generate_vod_scheme(pid, mgdb_id)
        schemes['type'] = "VOD"
    
    # 生成中文版本 scheme
    if pid_mandarin:
        schemes['scheme_url_mandarin'] = _generate_vod_scheme(pid_mandarin, mgdb_id)
    
    # 生成粤语版本 scheme
    if pid_cantonese:
        schemes['scheme_url_cantonese'] = _generate_vod_scheme(pid_cantonese, mgdb_id)
    
    # 如果没有录像，尝试生成直播 scheme
    if not pid:
        if live_url:
            if mgdb_id:
                action_params = {
                    "type": "JUMP_INNER_NEW_PAGE",
                    "params": {
                        "frameID": "default-frame",
                        "pageID": "WORLDCUP_DETAIL",
                        "location": "h5_share",
                        "contentID": str(mgdb_id),
                        "extra": {
                            "mgdbID": str(mgdb_id)
                        }
                    }
                }
                json_str = json.dumps(action_params)
                encoded_json = urllib.parse.quote(json_str)
                schemes['scheme_url'] = f"miguvideo://miguvideo?action={encoded_json}"
                schemes['type'] = "LIVE"
    
    return schemes

def process_links():
    logger.info("🔗 开始生成 Deep Links (多语言版)...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            matches = json.load(f)
            
        updated_count = 0
        live_count = 0
        vod_count = 0
        multilang_count = 0
        
        for match in matches:
            schemes = generate_scheme(match)
            
            # 更新主 scheme
            match['scheme_url'] = schemes.get('scheme_url', '')
            
            # 更新多语言 scheme
            if schemes.get('scheme_url_mandarin'):
                match['scheme_url_mandarin'] = schemes.get('scheme_url_mandarin')
                multilang_count += 1
            
            if schemes.get('scheme_url_cantonese'):
                match['scheme_url_cantonese'] = schemes.get('scheme_url_cantonese')
                multilang_count += 1
            
            link_type = schemes.get('type', 'NONE')
            if link_type != "NONE":
                updated_count += 1
                if link_type == "LIVE": 
                    live_count += 1
                elif link_type == "VOD": 
                    vod_count += 1

        # 保存回文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✅ 处理完成!")
        logger.info(f"   总链接数: {updated_count}")
        logger.info(f"   📼 录像链接: {vod_count}")
        logger.info(f"   🔴 直播链接: {live_count}")
        logger.info(f"   🌐 多语言支持: {multilang_count} (中文/粤语)")
        
    except Exception as e:
        logger.error(f"❌ 失败: {e}")

if __name__ == "__main__":
    process_links()