#!/usr/bin/env python3
"""
RedLens 数据工厂 - 智能咪咕视频抓取器 (直播+录像版)
功能:
1. 获取已完赛场次的【全场回放】(PID)
2. 获取未完赛场次的【直播间链接】(Live URL)
支持: 英超(5), 足总杯(10000495), 联赛杯(7), 欧冠(200)
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===== 配置区 =====
OUTPUT_FILE = "migu_videos_complete.json"
FIXTURES_FILE = "matches.json"             # 最新赛程
HISTORY_FILE = "matches_with_videos.json"  # 历史存档 (用于去重)
MIGU_API_BASE = "https://vms-sc.miguvideo.com/vms-match/v6/staticcache/basic/match-list/normal-match-list"
SPORT_ID = "1"  # 足球

# 🏆 赛事 ID 映射表
COMPETITION_MAP = {
    "Premier League": "5",
    "FA Cup": "10000495",
    "League Cup": "7",
    "UEFA Champions League": "200"
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CompleteMiguFetcher:
    """完整的咪咕视频抓取器 - 支持多赛事动态 ID"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.miguvideo.com/',
            'Accept': 'application/json'
        }
        self.session = self._create_session()
        self.tasks: Set[Tuple[str, str]] = set()
    
    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _analyze_smart_mode_targets(self) -> Set[Tuple[str, str]]:
        """
        智能分析: 
        1. 过去的比赛 -> 没录像的要抓
        2. 未来的比赛 -> 没直播链接的要抓
        """
        tasks = set()
        
        if not os.path.exists(FIXTURES_FILE):
            logger.warning(f"⚠️ 未找到 {FIXTURES_FILE}")
            return set()
            
        with open(FIXTURES_FILE, 'r', encoding='utf-8') as f:
            fixtures = json.load(f)
            
        # 读取现有数据的状态
        existing_status = {} # key -> {'has_pid': bool, 'has_live': bool}
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                for h in history:
                    key = f"{h.get('date')}_{h.get('opponent')}"
                    existing_status[key] = {
                        'has_pid': bool(h.get('migu_pid')),
                        'has_live': bool(h.get('migu_live_url'))
                    }
            except: pass
        
        logger.info(f"📊 智能分析中... (历史记录: {len(existing_status)} 条)")
        
        fetch_count = 0
        for match in fixtures:
            status = match.get('status', 'U') # C=完赛, U=未赛
            date_str = match.get('date', '')
            opponent = match.get('opponent', '')
            comp_name = match.get('competition', 'Premier League')
            
            # 获取对应的咪咕栏目 ID
            comp_id = COMPETITION_MAP.get(comp_name, "5") # 默认英超

            key = f"{date_str}_{opponent}"
            current_state = existing_status.get(key, {'has_pid': False, 'has_live': False})
            
            needs_fetch = False
            
            # 策略 A: 已完赛，但没有录像 PID -> 抓！
            if status == 'C' and not current_state['has_pid']:
                needs_fetch = True
                logger.info(f"   📼 补录像: {date_str} vs {opponent}")
                
            # 策略 B: 未完赛，但没有直播链接 -> 抓！
            # (通常所有未完赛的我们都可以扫一遍，确保拿到最新的 ID)
            elif status == 'U':
                # 哪怕已经有了 live_url，也建议刷新一下，万一 ID 变了呢
                # 但为了节省资源，如果有了可以跳过。这里我们选择：如果没有 live_url 必须抓
                if not current_state['has_live']:
                    needs_fetch = True
                    logger.info(f"   📡 抓直播: {date_str} vs {opponent}")
                else:
                    # 可选：如果想强制刷新所有未来比赛，把这里也设为 True
                    pass

            if needs_fetch:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    migu_date = date_obj.strftime('%Y%m%d')
                    tasks.add((migu_date, comp_id))
                    fetch_count += 1
                except: pass
        
        if fetch_count == 0:
            logger.info("🟢 所有数据均为最新，无需抓取。")
        else:
            logger.info(f"🟠 共需抓取 {len(tasks)} 个日期的据")
            
        return tasks
    
    def _get_default_tasks(self) -> Set[Tuple[str, str]]:
        """Force模式: 强力扫描所有日期"""
        logger.info("💪 FORCE 模式：不分析差异，直接扫描所有比赛日期")
        tasks = set()
        
        if not os.path.exists(FIXTURES_FILE): return set()
        
        with open(FIXTURES_FILE, 'r', encoding='utf-8') as f:
            fixtures = json.load(f)
            
        for match in fixtures:
            try:
                date_str = match.get('date', '')
                comp_name = match.get('competition', 'Premier League')
                comp_id = COMPETITION_MAP.get(comp_name, "5")
                
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                migu_date = date_obj.strftime('%Y%m%d')
                tasks.add((migu_date, comp_id))
            except: pass
            
        return tasks

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), retry=retry_if_exception_type(Exception), reraise=False)
    def fetch_full_match_replay(self, mgdb_id: str) -> Optional[str]:
        # 查详情页找 PID
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
            
            def is_full_replay(video_name):
                """判断是否是全场回放而非集锦"""
                # 优先判定：包含"回放"但不包含"集锦"
                has_replay = '回放' in video_name
                has_highlight = '集锦' in video_name
                return has_replay and not has_highlight

            # 策略1: 找类型=4的视频，进一步筛选出"全场回放"（排除集锦）
            type4_videos = [r for r in replay_list if r.get('type', '') == '4']
            
            # 策略1a: 优先找包含"回放"但不包含"集锦"的视频
            full_replays = [v for v in type4_videos if is_full_replay(v.get('name', ''))]
            if full_replays:
                # 在全场回放中选最长的（通常是主讲解版本）
                longest = max(full_replays, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                pid = longest.get('pID', '')
                if pid:
                    logger.debug(f"   ✅ 找到全场回放: {longest.get('name')} (PID: {pid})")
                    return pid
            
            # 策略1b: 如果没有"回放"关键词的，就选type=4中时长最长的
            # （这可能是老版本或其他格式的完整比赛）
            if type4_videos:
                longest = max(type4_videos, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                # 只有在时长超过1小时才认为是完整比赛，否则可能是集锦
                duration_sec = duration_to_seconds(longest.get('duration', '00:00'))
                if duration_sec > 3600:
                    pid = longest.get('pID', '')
                    if pid:
                        logger.debug(f"   ✅ 找到全场回放(无关键词): {longest.get('name')} (PID: {pid})")
                        return pid
            
            # 兜底: 从所有视频中找最长的完整比赛
            if replay_list:
                longest = max(replay_list, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                duration_sec = duration_to_seconds(longest.get('duration', '00:00'))
                if duration_sec > 3600:  # 至少1小时
                    pid = longest.get('pID', '')
                    if pid:
                        logger.debug(f"   ⚠️ 兜底选择: {longest.get('name')} (PID: {pid})")
                        return pid
            
            return None
        except Exception as e:
            logger.warning(f"获取全场回放失败: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), retry=retry_if_exception_type(Exception), reraise=False)
    def fetch_api(self, date_str: str, comp_id: str) -> Optional[Dict]:
        url = f"{MIGU_API_BASE}/{date_str}/{comp_id}/up/{SPORT_ID}/miguvideo"
        try:
            response = self.session.get(url, headers=self.headers, timeout=30, verify=False)
            return response.json() if response.status_code == 200 else None
        except: return None

    def parse_match(self, match: Dict, date_key: str) -> Optional[Dict]:
        try:
            # 宽容匹配
            title = match.get('pkInfoTitle', '') or match.get('title', '')
            confront_teams = match.get('confrontTeams', [])
            is_arsenal_home = False
            opponent = "Unknown"
            
            has_arsenal = False
            if '阿森纳' in title: has_arsenal = True
            
            if confront_teams and len(confront_teams) == 2:
                name1 = confront_teams[0].get('name', '')
                name2 = confront_teams[1].get('name', '')
                
                if '阿森纳' in name1:
                    has_arsenal = True
                    is_arsenal_home = True
                    opponent = name2
                elif '阿森纳' in name2:
                    has_arsenal = True
                    is_arsenal_home = False
                    opponent = name1
            
            if not has_arsenal: return None

            match_status = match.get('matchStatus', '') # 2/3=完赛
            is_finished = match_status in ['2', '3']
            
            # === 核心数据提取 ===
            pid = match.get('pID', '') # 录像ID (可能不准，API可能返回集锦)
            mgdb_id = match.get('mgdbId', '') # 直播间ID (关键!)
            
            # 【关键修改】对于已完赛的比赛，深度抓取并验证PID
            # 这是为了确保我们获取全场回放而非集锦
            if is_finished and mgdb_id:
                verified_pid = self.fetch_full_match_replay(mgdb_id)
                if verified_pid:
                    pid = verified_pid  # 使用验证后的PID
                # 如果深度抓取没有找到，保持原有的 pid（可能是空或集锦）

            try: formatted_date = datetime.strptime(date_key, '%Y%m%d').strftime('%Y-%m-%d')
            except: formatted_date = date_key
            
            comp_name = match.get('competitionName') or match.get('mgdbName', '未知赛事')

            result = {
                'date': formatted_date, 'opponent': opponent, 'is_home': is_arsenal_home,
                'title': title, 'match_status': match_status, 'is_finished': is_finished,
                'competition': comp_name
            }
            
            # 填充录像信息
            if pid:
                result['pid'] = pid
                result['detail_url'] = f"https://www.miguvideo.com/p/detail/{pid}"
            
            # 填充直播信息 (只要有 mgdbId 就填，不管完没完赛)
            if mgdb_id:
                result['live_url'] = f"https://www.miguvideo.com/p/live/{mgdb_id}"
                
            # 提取比分
            if confront_teams and len(confront_teams) == 2:
                s1 = confront_teams[0].get('score', 0)
                s2 = confront_teams[1].get('score', 0)
                result['arsenal_score'] = s1 if is_arsenal_home else s2
                result['opponent_score'] = s2 if is_arsenal_home else s1

            return result
        except Exception as e:
            logger.warning(f"解析出错: {e}")
            return None

    def fetch_all_season(self, mode="smart") -> List[Dict]:
        logger.info(f"🚀 启动抓取 | 模式: {mode.upper()}")
        
        if mode == "force":
            self.tasks = self._get_default_tasks()
        else:
            self.tasks = self._analyze_smart_mode_targets()
            if not self.tasks:
                logger.info("💤 没有需要更新的比赛。")
                sys.exit(0)
        
        logger.info(f"🎯 任务数: {len(self.tasks)} 个 API 请求")
        all_matches = []
        
        for date_str, comp_id in sorted(list(self.tasks)):
            logger.info(f"   🔍 扫描: {date_str} [ID={comp_id}]")
            
            data = self.fetch_api(date_str, comp_id)
            if not data or data.get('code') != 200: continue
            
            match_list_raw = data.get('body', {}).get('matchList', {})
            match_dict = {}
            if isinstance(match_list_raw, dict): match_dict = match_list_raw
            elif isinstance(match_list_raw, list): match_dict = {date_str: match_list_raw}
            
            for date_key, matches in match_dict.items():
                if not isinstance(matches, list): continue
                for match in matches:
                    parsed = self.parse_match(match, date_key)
                    
                    # 【关键修改】只要抓到了(有PID或有LiveURL或纯比赛信息)都保存
                    if parsed:
                        all_matches.append(parsed)
                        # 日志优化
                        status_icon = "📼" if parsed.get('pid') else ("📡" if parsed.get('live_url') else "📄")
                        logger.info(f"     ✅ {status_icon} 获取: {parsed['date']} {parsed['opponent']}")
        
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
        if not matches: return
        try:
            # 读取旧数据进行增量更新
            old_matches = []
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    old_matches = json.load(f)
            
            merged_map = {f"{m['date']}_{m['opponent']}": m for m in old_matches}
            for m in matches:
                merged_map[f"{m['date']}_{m['opponent']}"] = m
                
            final_list = sorted(merged_map.values(), key=lambda x: x['date'])
            
            # 【手動修正】已知錯誤的 PID 映射 - 某些比賽的 API 返回錯誤 PID
            pid_corrections = {
                ('2026-01-11', '朴茨茅斯'): '962347145',  # Portsmouth FA Cup - 原 PID 不存在
            }
            
            # 應用修正
            for match in final_list:
                key = (match.get('date'), match.get('opponent'))
                if key in pid_corrections:
                    correct_pid = pid_corrections[key]
                    if match.get('pid') and match.get('pid') != correct_pid:
                        logger.info(f"🔧 修正: {key[0]} {key[1]} PID: {match.get('pid')} → {correct_pid}")
                        match['pid'] = correct_pid
                        match['detail_url'] = f"https://www.miguvideo.com/p/detail/{correct_pid}"

            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 数据已更新至 {OUTPUT_FILE} (共 {len(final_list)} 条)")
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")

def main():
    try:
        # 默认使用 force 模式扫一遍所有日期，确保抓到未来比赛
        run_mode = os.getenv("RUN_MODE", "force") 
        fetcher = CompleteMiguFetcher()
        matches = fetcher.fetch_all_season(mode=run_mode)
        fetcher.save_to_json(matches)
    except SystemExit: pass
    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")

if __name__ == "__main__":
    main()