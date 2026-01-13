#!/usr/bin/env python3
"""
RedLens 数据工厂 - Deep Link 生成器
为咪咕视频生成 App 跳转链接
"""

import json
import urllib.parse
import re
import logging
from typing import Dict, Optional

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

INPUT_FILE = "matches_with_videos.json"
OUTPUT_FILE = "matches_with_videos.json"


def extract_room_id(live_url: str) -> Optional[str]:
    """
    从 migu_live_url 中提取房间号 (mgdbID)
    
    Args:
        live_url: 完整的直播间 URL，如 "https://www.miguvideo.com/p/live/120000542331"
        
    Returns:
        房间号字符串，如 "120000542331"，提取失败则返回 None
    """
    if not live_url:
        return None
    
    # 使用正则提取 URL 末尾的数字
    match = re.search(r'(\d+)$', live_url)
    if match:
        return match.group(1)
    
    return None


def generate_scheme_url(pid: str, room_id: str) -> str:
    """
    生成咪咕视频 App 的 Deep Link
    
    Args:
        pid: 录像内容 ID (contentID)
        room_id: 直播间房间号 (mgdbID)
        
    Returns:
        完整的 Scheme URL
    """
    if not pid or not room_id:
        return ""
    
    # 构造 Action JSON
    action = {
        "type": "JUMP_INNER_NEW_PAGE",
        "params": {
            "frameID": "default-frame",
            "pageID": "WORLDCUP_DETAIL",
            "location": "h5_share",
            "contentID": str(pid),
            "extra": {
                "mgdbID": str(room_id)
            }
        }
    }
    
    # 序列化并进行 URL 编码
    json_str = json.dumps(action, ensure_ascii=False)
    encoded_str = urllib.parse.quote(json_str)
    
    return f"miguvideo://miguvideo?action={encoded_str}"


def process_matches(input_file: str, output_file: str) -> None:
    """
    处理所有比赛数据，生成 Deep Link
    
    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径
    """
    logger.info("🔗 开始生成 Deep Links...")
    
    # 读取数据
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        logger.info(f"📖 读取 {len(matches)} 场比赛数据")
    except FileNotFoundError:
        logger.error(f"❌ 文件不存在: {input_file}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 解析失败: {e}")
        return
    
    # 处理每场比赛
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for match in matches:
        pid = match.get('migu_pid', '')
        live_url = match.get('migu_live_url', '')
        
        # 空值检查 - 未来的比赛可能没有这些数据
        if not pid or not live_url:
            match['scheme_url'] = ""
            skip_count += 1
            continue
        
        # 提取房间号
        room_id = extract_room_id(live_url)
        if not room_id:
            logger.warning(f"⚠️ 无法提取房间号: {match.get('date')} vs {match.get('opponent')}")
            match['scheme_url'] = ""
            error_count += 1
            continue
        
        # 生成 Scheme URL
        scheme_url = generate_scheme_url(pid, room_id)
        if scheme_url:
            match['scheme_url'] = scheme_url
            success_count += 1
        else:
            match['scheme_url'] = ""
            error_count += 1
    
    # 保存结果
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 数据已保存至 {output_file}")
        logger.info(f"")
        logger.info(f"📊 处理结果:")
        logger.info(f"   ✅ 成功生成: {success_count} 场")
        logger.info(f"   ⏭️  跳过: {skip_count} 场 (未完赛或无录像)")
        logger.info(f"   ❌ 失败: {error_count} 场")
        
        # 打印示例
        if success_count > 0:
            logger.info(f"")
            logger.info(f"🔗 Deep Link 示例 (前3场):")
            count = 0
            for match in matches:
                if match.get('scheme_url') and count < 3:
                    logger.info(f"   {match.get('date')} vs {match.get('opponent')}")
                    logger.info(f"   {match['scheme_url'][:100]}...")
                    logger.info(f"")
                    count += 1
        
        logger.info(f"✅ Deep Link 生成完成!")
        
    except Exception as e:
        logger.error(f"❌ 保存文件失败: {e}")


def main():
    """主函数"""
    process_matches(INPUT_FILE, OUTPUT_FILE)


if __name__ == "__main__":
    main()

