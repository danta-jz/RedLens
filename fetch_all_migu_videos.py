#!/usr/bin/env python3
"""
RedLens 数据工厂 - 完整版咪咕视频抓取器
获取2025/26赛季所有阿森纳比赛的录像链接
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import aiohttp

# ===== 配置区 =====
OUTPUT_FILE = "migu_videos_complete.json"
MIGU_API_BASE = "https://vms-sc.miguvideo.com/vms-match/v6/staticcache/basic/match-list/normal-match-list"
COMPETITION_ID = "5"  # 英超
SPORT_ID = "1"  # 足球

# 2025/26赛季时间范围
SEASON_START = "20250817"  # 2025年8月17日（赛季开始）
SEASON_END = "20260524"    # 2026年5月24日（赛季结束）

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CompleteMiguFetcher:
    """完整的咪咕视频抓取器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.miguvideo.com/',
            'Accept': 'application/json'
        }
        self.all_matches = []
    
    async def fetch_api(self, date_str: str, direction: str = "up") -> Optional[Dict]:
        """
        调用咪咕API
        
        Args:
            date_str: 基准日期，格式如 "20260105"
            direction: "up"=往前翻（历史）, "default"=当前/未来, "down"=往后翻
        """
        # API格式: /normal-match-list/{date}/{competition_id}/{direction}/1/miguvideo
        url = f"{MIGU_API_BASE}/{date_str}/{COMPETITION_ID}/{direction}/{SPORT_ID}/miguvideo"
        
        logger.info(f"📡 请求: {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.warning(f"⚠️ API返回状态码: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"❌ API请求失败: {str(e)}")
                return None
    
    def parse_match(self, match: Dict, date_key: str) -> Optional[Dict]:
        """
        解析单场比赛数据
        
        Args:
            match: API返回的比赛数据
            date_key: 日期键，如 "20260104"
        """
        try:
            title = match.get('pkInfoTitle', '')
            
            # 只处理阿森纳的比赛
            if '阿森纳' not in title:
                return None
            
            confront_teams = match.get('confrontTeams', [])
            if len(confront_teams) != 2:
                return None
            
            team1 = confront_teams[0]
            team2 = confront_teams[1]
            
            # 确定对手
            is_arsenal_home = '阿森纳' in team1.get('name', '')
            opponent = team2.get('name', '') if is_arsenal_home else team1.get('name', '')
            
            # 比赛状态
            match_status = match.get('matchStatus', '')
            is_finished = match_status == '2'
            
            # 提取PID
            pid = match.get('pID', '')
            
            # 转换日期格式
            try:
                date_obj = datetime.strptime(date_key, '%Y%m%d')
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except:
                formatted_date = date_key
            
            result = {
                'date': formatted_date,
                'opponent': opponent,
                'is_home': is_arsenal_home,
                'title': title,
                'match_status': match_status,
                'is_finished': is_finished,
                'competition': match.get('mgdbName', '英超联赛')
            }
            
            # 如果比赛已完赛且有PID，添加录像信息
            if is_finished and pid:
                result['pid'] = pid
                result['detail_url'] = f"https://www.miguvideo.com/p/detail/{pid}"
                # 使用 mgdbId 作为 live URL 的 ID（不是 roomId）
                mgdb_id = match.get('mgdbId', '')
                result['live_url'] = f"https://www.miguvideo.com/p/live/{mgdb_id}" if mgdb_id else ""
                
                # 添加比分
                if is_arsenal_home:
                    result['arsenal_score'] = team1.get('score', 0)
                    result['opponent_score'] = team2.get('score', 0)
                else:
                    result['arsenal_score'] = team2.get('score', 0)
                    result['opponent_score'] = team1.get('score', 0)
            else:
                result['pid'] = ""
                result['detail_url'] = ""
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 解析比赛失败: {str(e)}")
            return None
    
    async def fetch_range(self, start_date: str, end_date: str, direction: str = "up") -> List[Dict]:
        """
        获取日期范围内的所有比赛
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            direction: 翻页方向
        """
        matches = []
        current_date = start_date
        
        logger.info(f"🔍 获取 {start_date} 到 {end_date} 的比赛...")
        
        # 为了覆盖整个范围，我们需要多次调用API
        # 每次API返回大约一周的数据
        max_iterations = 30  # 最多30次请求，覆盖约半年
        
        for i in range(max_iterations):
            data = await self.fetch_api(current_date, direction)
            
            if not data or data.get('code') != 200:
                logger.warning(f"⚠️ 第 {i+1} 次请求失败")
                break
            
            body = data.get('body', {})
            match_list = body.get('matchList', {})
            days = body.get('days', [])
            
            if not match_list:
                logger.info(f"✅ 第 {i+1} 次请求无数据，停止")
                break
            
            logger.info(f"📅 第 {i+1} 次请求包含日期: {days}")
            
            # 解析这批数据
            batch_count = 0
            for date_key, date_matches in match_list.items():
                for match in date_matches:
                    parsed = self.parse_match(match, date_key)
                    if parsed:
                        matches.append(parsed)
                        batch_count += 1
            
            logger.info(f"✅ 第 {i+1} 次请求找到 {batch_count} 场阿森纳比赛")
            
            # 更新基准日期为这批数据中最早的日期
            if days:
                if direction == "up":
                    current_date = days[0]  # 最早的日期
                else:
                    current_date = days[-1]  # 最晚的日期
                
                # 检查是否已经超出范围
                if direction == "up" and current_date < start_date:
                    logger.info(f"✅ 已到达起始日期 {start_date}，停止")
                    break
                elif direction == "down" and current_date > end_date:
                    logger.info(f"✅ 已到达结束日期 {end_date}，停止")
                    break
            else:
                break
            
            # 避免请求过快
            await asyncio.sleep(1)
        
        return matches
    
    async def fetch_all_season(self) -> List[Dict]:
        """获取整个赛季的所有比赛"""
        logger.info("🚀 开始获取2025/26赛季所有阿森纳比赛...")
        
        all_matches = []
        
        # 获取今天的日期
        today = datetime.now().strftime('%Y%m%d')
        
        # 策略1: 从今天开始往前翻，获取历史比赛
        # 咪咕API的"up"方向是往前翻（历史），需要从最近的日期开始
        logger.info("\n📜 获取历史比赛...")
        
        # 从今天开始，持续往前翻页直到赛季开始
        current_date = today
        
        for iteration in range(30):  # 最多30次迭代
            data = await self.fetch_api(current_date, "up")
            
            if not data or data.get('code') != 200:
                break
            
            body = data.get('body', {})
            match_list = body.get('matchList', {})
            days = body.get('days', [])
            
            if not match_list or not days:
                break
            
            logger.info(f"📅 第 {iteration+1} 批包含日期: {days}")
            
            # 解析这批数据
            batch_count = 0
            for date_key, matches in match_list.items():
                for match in matches:
                    parsed = self.parse_match(match, date_key)
                    if parsed:
                        all_matches.append(parsed)
                        batch_count += 1
            
            logger.info(f"✅ 第 {iteration+1} 批找到 {batch_count} 场阿森纳比赛")
            
            # 更新为这批数据中最早的日期，继续往前翻
            earliest_date = days[0]
            
            # 如果已经到达或超过赛季开始日期，停止
            if earliest_date <= SEASON_START:
                logger.info(f"✅ 已到达赛季开始日期 {SEASON_START}")
                break
            
            current_date = earliest_date
            await asyncio.sleep(1)
        
        # 策略2: 获取未来比赛（使用default模式）
        logger.info("\n📅 获取未来比赛...")
        data = await self.fetch_api("0", "default")
        if data and data.get('code') == 200:
            body = data.get('body', {})
            match_list = body.get('matchList', {})
            
            for date_key, matches in match_list.items():
                for match in matches:
                    parsed = self.parse_match(match, date_key)
                    if parsed:
                        all_matches.append(parsed)
        
        # 按日期排序并去重
        seen = set()
        unique_matches = []
        for match in sorted(all_matches, key=lambda x: x['date']):
            key = (match['date'], match['opponent'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches
    
    def save_to_json(self, matches: List[Dict]):
        """保存结果到JSON文件"""
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\n💾 数据已保存至 {OUTPUT_FILE}")
            logger.info(f"📊 共 {len(matches)} 场比赛")
            
            # 统计
            finished = sum(1 for m in matches if m['is_finished'])
            upcoming = len(matches) - finished
            with_video = sum(1 for m in matches if m.get('pid'))
            
            logger.info(f"✅ 已完赛: {finished} 场")
            logger.info(f"📅 未完赛: {upcoming} 场")
            logger.info(f"🎬 有录像: {with_video} 场")
            
            if with_video > 0:
                logger.info(f"\n📹 录像链接示例（前5场）:")
                count = 0
                for m in matches:
                    if m.get('detail_url'):
                        logger.info(f"   {m['date']} {m['opponent']}: {m['detail_url']}")
                        count += 1
                        if count >= 5:
                            break
            
        except Exception as e:
            logger.error(f"❌ 保存文件失败: {str(e)}")
            raise


async def main():
    """主函数"""
    try:
        fetcher = CompleteMiguFetcher()
        matches = await fetcher.fetch_all_season()
        
        if not matches:
            logger.warning("⚠️ 未获取到任何比赛数据")
            return
        
        fetcher.save_to_json(matches)
        logger.info("\n✅ 咪咕视频抓取完成!")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
    except Exception as e:
        logger.error(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

