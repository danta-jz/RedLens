#!/usr/bin/env python3
"""
RedLens 数据工厂 - 智能咪咕视频抓取器
获取2025/26赛季阿森纳比赛的录像链接 - 智能追更版本
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ===== 配置区 =====
OUTPUT_FILE = "migu_videos_complete.json"
FIXTURES_FILE = "matches.json"             # 最新赛程 (fetch_fixtures.py 的产出)
HISTORY_FILE = "matches_with_videos.json"  # 历史存档 (用于比对是否已有录像)
MIGU_API_BASE = "https://vms-sc.miguvideo.com/vms-match/v6/staticcache/basic/match-list/normal-match-list"
COMPETITION_ID = "5"  # 英超
SPORT_ID = "1"  # 足球

# 智能追更配置
LOOKBACK_DAYS = 3   # 默认往前查询天数
LOOKAHEAD_DAYS = 7  # 默认往后查询天数

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CompleteMiguFetcher:
    """完整的咪咕视频抓取器 - 使用同步requests库，智能追更版本"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.miguvideo.com/',
            'Accept': 'application/json'
        }
        self.session = self._create_session()
        self.target_dates = set()
    
    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _analyze_smart_mode_targets(self) -> Set[str]:
        """
        核心智能逻辑：
        对比 'matches.json'(最新状态) 和 'matches_with_videos.json'(已有录像)
        找出：状态已完赛(C) 且 还没有录像PID 的比赛日期
        """
        target_dates = set()
        
        # 1. 读取最新赛程
        if not os.path.exists(FIXTURES_FILE):
            logger.warning(f"⚠️ 未找到 {FIXTURES_FILE}，无法进行智能分析")
            return set()
            
        with open(FIXTURES_FILE, 'r', encoding='utf-8') as f:
            fixtures = json.load(f)
            
        # 2. 读取已有录像库 (用来判断是否已经抓过了)
        existing_pids = {} # key: date+opponent, value: pid
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                for h in history:
                    # 建立索引：日期_对手 -> PID
                    key = f"{h.get('date')}_{h.get('opponent')}"
                    existing_pids[key] = h.get('migu_pid')
            except Exception as e:
                logger.warning(f"⚠️ 读取历史存档失败: {e}")
        
        logger.info(f"📊 智能分析中... (参考历史记录: {len(existing_pids)} 条)")
        
        pending_count = 0
        for match in fixtures:
            status = match.get('status', 'U')
            date_str = match.get('date', '') # 2025-01-04
            opponent = match.get('opponent', '')
            
            # 关键逻辑：已完赛(C) 且 (历史记录里不存在 或 PID为空)
            if status == 'C':
                key = f"{date_str}_{opponent}"
                has_video = existing_pids.get(key)
                
                if not has_video:
                    # 这才是真正的"待追更"比赛
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        # 咪咕API格式: YYYYMMDD
                        target_dates.add(date_obj.strftime('%Y%m%d'))
                        logger.info(f"   🔥 发现待追更比赛: {date_str} vs {opponent}")
                        pending_count += 1
                    except:
                        pass
        
        if pending_count == 0:
            logger.info("🟢 所有已完赛场次均已有录像，无需更新。")
        else:
            logger.info(f"🟠 需追更 {pending_count} 场比赛，涉及 {len(target_dates)} 个日期")
            
        return target_dates
    
    def _get_default_date_range(self) -> Set[str]:
        """强制模式下的默认范围"""
        today = datetime.now()
        dates = set()
        for i in range(LOOKBACK_DAYS):
            dates.add((today - timedelta(days=i)).strftime('%Y%m%d'))
        for i in range(1, LOOKAHEAD_DAYS + 1):
            dates.add((today + timedelta(days=i)).strftime('%Y%m%d'))
        return dates

    # ... [中间 fetch_full_match_replay, fetch_api, parse_match 方法保持不变，无需修改] ...
    # (为了节省篇幅，这里省略中间未变动的辅助函数，Cursor 会保留原有的)
    # 请确保 fetch_full_match_replay, fetch_api, parse_match 依然存在且逻辑不变
    # ...

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), retry=retry_if_exception_type(Exception), reraise=False)
    def fetch_full_match_replay(self, mgdb_id: str) -> Optional[str]:
        # ... (保留原逻辑) ...
        # 这里需要完整保留你之前文件里的这个函数代码
        url = f"https://vms-sc.miguvideo.com/vms-match/v5/staticcache/basic/all-view-list/{mgdb_id}/2/miguvideo"
        try:
            response = self.session.get(url, headers=self.headers, timeout=10, verify=False)
            if response.status_code != 200: return None
            data = response.json()
            replay_list = data.get('body', {}).get('replayList', [])
            if not replay_list: return None
            
            def duration_to_seconds(duration_str):
                try:
                    parts = duration_str.split(':')
                    if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    return 0
                except: return 0

            type4_videos = [r for r in replay_list if r.get('type', '') == '4']
            if type4_videos:
                longest = max(type4_videos, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                return longest.get('pID', '')
            
            if replay_list:
                longest = max(replay_list, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                if longest.get('duration', '') > '01:00:00': return longest.get('pID', '')
            return None
        except: return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), retry=retry_if_exception_type(Exception), reraise=False)
    def fetch_api(self, date_str: str, direction: str = "up") -> Optional[Dict]:
        url = f"{MIGU_API_BASE}/{date_str}/{COMPETITION_ID}/{direction}/{SPORT_ID}/miguvideo"
        try:
            response = self.session.get(url, headers=self.headers, timeout=30, verify=False)
            return response.json() if response.status_code == 200 else None
        except: return None

    def parse_match(self, match: Dict, date_key: str) -> Optional[Dict]:
        # ... (保留原逻辑) ...
        try:
            title = match.get('pkInfoTitle', '')
            if '阿森纳' not in title: return None
            confront_teams = match.get('confrontTeams', [])
            if len(confront_teams) != 2: return None
            team1, team2 = confront_teams[0], confront_teams[1]
            is_arsenal_home = '阿森纳' in team1.get('name', '')
            opponent = team2.get('name', '') if is_arsenal_home else team1.get('name', '')
            match_status = match.get('matchStatus', '')
            is_finished = match_status == '2'
            pid = match.get('pID', '')
            
            try: formatted_date = datetime.strptime(date_key, '%Y%m%d').strftime('%Y-%m-%d')
            except: formatted_date = date_key
            
            result = {
                'date': formatted_date, 'opponent': opponent, 'is_home': is_arsenal_home,
                'title': title, 'match_status': match_status, 'is_finished': is_finished,
                'competition': match.get('mgdbName', '英超联赛')
            }
            if is_finished and pid:
                result['pid'] = pid
                result['detail_url'] = f"https://www.miguvideo.com/p/detail/{pid}"
                mgdb_id = match.get('mgdbId', '')
                result['live_url'] = f"https://www.miguvideo.com/p/live/{mgdb_id}" if mgdb_id else ""
                if is_arsenal_home:
                    result['arsenal_score'] = team1.get('score', 0)
                    result['opponent_score'] = team2.get('score', 0)
                else:
                    result['arsenal_score'] = team2.get('score', 0)
                    result['opponent_score'] = team1.get('score', 0)
            else:
                result['pid'] = ""; result['detail_url'] = ""
            return result
        except: return None

    def fetch_all_season(self, mode="smart") -> List[Dict]:
        logger.info(f"🚀 启动抓取 | 模式: {mode.upper()}")
        
        # === 核心逻辑修改区 ===
        if mode == "force":
            logger.info("💪 Force Mode: 忽略智能分析，强制抓取默认范围")
            self.target_dates = self._get_default_date_range()
        else:
            # Smart Mode
            self.target_dates = self._analyze_smart_mode_targets()
            
            # 如果没有待抓取的日期，直接退出 (省钱关键!)
            if not self.target_dates:
                logger.info("💤 Smart Mode: 没有需要追更的比赛，任务结束。")
                sys.exit(0)  # 直接退出脚本，不再执行后续请求
        
        # ... 后续抓取逻辑保持不变 ...
        logger.info(f"🎯 目标日期数: {len(self.target_dates)} 个")
        all_matches = []
        for target_date in sorted(self.target_dates):
            logger.info(f"   🔍 抓取日期: {target_date}")
            data = self.fetch_api(target_date, "up")
            if not data or data.get('code') != 200: continue
            
            match_list = data.get('body', {}).get('matchList', {})
            for date_key, matches in match_list.items():
                for match in matches:
                    parsed = self.parse_match(match, date_key)
                    if parsed:
                        if parsed.get('is_finished'):
                            mgdb_id = match.get('mgdbId', '')
                            if mgdb_id:
                                pid = self.fetch_full_match_replay(mgdb_id)
                                if pid: 
                                    parsed['pid'] = pid
                                    parsed['detail_url'] = f"https://www.miguvideo.com/p/detail/{pid}"
                        all_matches.append(parsed)
        
        # 去重
        seen = set()
        unique_matches = []
        for match in sorted(all_matches, key=lambda x: x['date']):
            key = (match['date'], match['opponent'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
                
        return unique_matches

    def save_to_json(self, matches: List[Dict]):
        # ... (保留原逻辑) ...
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 数据已保存至 {OUTPUT_FILE}")
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")

def main():
    try:
        # 读取环境变量，默认为 force (本地运行如果不传参，最好全量跑一次；Actions 里会传 smart)
        run_mode = os.getenv("RUN_MODE", "force")
        
        fetcher = CompleteMiguFetcher()
        matches = fetcher.fetch_all_season(mode=run_mode)
        
        if matches:
            fetcher.save_to_json(matches)
            
    except SystemExit:
        pass # 正常退出
    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()