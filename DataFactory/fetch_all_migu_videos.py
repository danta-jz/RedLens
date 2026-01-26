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
    def fetch_full_match_replay(self, mgdb_id: str) -> Optional[Dict]:
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
            
            def is_definitely_highlight(video_name):
                """判断是否一定是集锦"""
                return '集锦' in video_name or '精彩' in video_name
            
            def detect_language_commentators(video_name):
                """
                检测视频的语言和解说人数
                返回: (language, num_commentators, priority)
                language: 'mandarin', 'cantonese', 'english', 'unknown'
                num_commentators: 实际的解说人数 (从括号中的名字推断)
                priority: 用于排序的优先级 (越高越优先)
                """
                import re
                
                # 统计括号中的人名数（用逗号和顿号分割）
                commentator_pattern = r'[（(]([^)）]+)[)）]'
                match = re.search(commentator_pattern, video_name)
                num_commentators = 0
                
                if match:
                    names = match.group(1)
                    # 统计人数：逗号、顿号、and、&作为分隔符
                    num_commentators = names.count('、') + names.count(',') + names.count('and') + names.count('&') + 1
                
                # 检测粤语标记（粤语多数是2人）
                if '粤' in video_name or any(name in video_name for name in ['陈凯冬', '何辉', '黄镇', '罗毅']):
                    return 'cantonese', max(num_commentators, 2), 1  # 粤语优先级最低
                
                # 检测英文标记
                if 'English' in video_name or '英文' in video_name:
                    return 'english', max(num_commentators, 1), 2
                
                # 检测中文标记 - 使用括号内的名字来判断
                if num_commentators >= 3:
                    # 3人及以上的中文解说
                    return 'mandarin', num_commentators, 10 + num_commentators  # 3人版本最优（优先级最高）
                elif num_commentators == 1:
                    # 1人解说（单人评论员）
                    return 'mandarin', 1, 3
                elif num_commentators == 2:
                    # 2人中文解说
                    return 'mandarin', 2, 5
                
                # 其他情况
                if '中文' in video_name or '国语' in video_name:
                    return 'mandarin', max(num_commentators, 2), 4
                
                return 'unknown', num_commentators if num_commentators > 0 else 2, 0

            # 日志记录可用的视频
            logger.debug(f"   📹 检查 mgdbId={mgdb_id} 的视频列表: {len(replay_list)} 个")
            for idx, v in enumerate(replay_list[:8]):  # 记录前8个，便于分析语言
                dur_sec = duration_to_seconds(v.get('duration', '00:00'))
                lang, commentators, priority = detect_language_commentators(v.get('name', ''))
                logger.debug(f"     [{idx+1}] {v.get('name')} | 时长={v.get('duration')} | 语言={lang} | {commentators}人 | 优先级={priority}")

            # 【优先级1】查找中文全场回放（优先选择3人解说）
            full_replays_with_lang = []
            for v in replay_list:
                if is_definitely_highlight(v.get('name', '')):
                    continue
                lang, commentators, priority = detect_language_commentators(v.get('name', ''))
                dur_sec = duration_to_seconds(v.get('duration', '00:00'))
                
                # 只考虑"回放"标记的视频和时长足够长的视频
                if '回放' in v.get('name', '') and dur_sec > 3600:  # 1小时以上的回放
                    full_replays_with_lang.append({
                        'video': v,
                        'duration_sec': dur_sec,
                        'language': lang,
                        'commentators': commentators,
                        'priority': priority,
                        'is_replay_labeled': True
                    })
            
            # 收集所有语言版本的 PID
            replay_pids = {
                'mandarin': None,     # 中文 PID
                'cantonese': None,    # 粤语 PID
                'other': None         # 其他 PID
            }
            
            if full_replays_with_lang:
                # 按优先级排序
                sorted_replays = sorted(
                    full_replays_with_lang,
                    key=lambda x: (x['priority'], x['duration_sec']),
                    reverse=True
                )
                
                # 【重要】遍历所有视频，收集所有语言的 PID（不仅是最优的）
                best = sorted_replays[0]  # 最优选择（用于 primary）
                
                for idx, item in enumerate(sorted_replays):  # 遍历所有，不限 3 个
                    lang = item['language']
                    pid = item['video'].get('pID', '')
                    name = item['video'].get('name', '')
                    dur_min = item['duration_sec'] // 60
                    priority = item['priority']
                    
                    # 记录日志（前5个）
                    if idx < 5:
                        logger.debug(f"   [{idx+1}] {lang:10} | 优先级={priority:2d} | {name} ({dur_min}分钟, PID: {pid})")
                    
                    # 保存各语言的 PID（最高优先级的版本）
                    if lang == 'mandarin' and not replay_pids['mandarin']:
                        replay_pids['mandarin'] = pid
                    elif lang == 'cantonese' and not replay_pids['cantonese']:
                        replay_pids['cantonese'] = pid
                    elif not replay_pids['other']:
                        replay_pids['other'] = pid
                
                best_pid = best['video'].get('pID', '')
                if best_pid:
                    logger.debug(f"   ✅ 最优选择(优先级={best['priority']}): {best['video'].get('name')} (PID: {best_pid})")
                    replay_pids['primary'] = best_pid  # 主 PID（优先级最高的）
                    return replay_pids
            
            # 【优先级2】查找任何非集锦的回放视频（不限语言）
            replay_candidates = [
                v for v in replay_list 
                if '回放' in v.get('name', '') and not is_definitely_highlight(v.get('name', '')) and duration_to_seconds(v.get('duration', '00:00')) > 3600
            ]
            if replay_candidates:
                longest = max(replay_candidates, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                pid = longest.get('pID', '')
                if pid:
                    lang, _, _ = detect_language_commentators(longest.get('name', ''))
                    logger.debug(f"   ✅ 优先级2(回放标签): {longest.get('name')} ({lang}, PID: {pid})")
                    replay_pids['primary'] = pid
                    if lang == 'mandarin':
                        replay_pids['mandarin'] = pid
                    elif lang == 'cantonese':
                        replay_pids['cantonese'] = pid
                    return replay_pids
            
            # 【优先级3】从所有视频中找时长最长且可能是完整比赛的（>90分钟）
            full_match_candidates = [
                v for v in replay_list 
                if not is_definitely_highlight(v.get('name', '')) and duration_to_seconds(v.get('duration', '00:00')) > 5400
            ]
            if full_match_candidates:
                longest = max(full_match_candidates, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                dur_sec = duration_to_seconds(longest.get('duration', '00:00'))
                pid = longest.get('pID', '')
                if pid:
                    logger.debug(f"   ✅ 优先级3(长时间): {longest.get('name')} ({int(dur_sec/60)}分钟, PID: {pid})")
                    replay_pids['primary'] = pid
                    return replay_pids
            
            # 【优先级4】type=4 的视频中找最长的（可能是官方版本）
            type4_videos = [r for r in replay_list if r.get('type', '') == '4']
            if type4_videos:
                longest = max(type4_videos, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                dur_sec = duration_to_seconds(longest.get('duration', '00:00'))
                if not is_definitely_highlight(longest.get('name', '')):
                    pid = longest.get('pID', '')
                    if pid:
                        logger.debug(f"   ✅ 优先级4(type=4): {longest.get('name')} ({int(dur_sec/60)}分钟, PID: {pid})")
                        replay_pids['primary'] = pid
                        return replay_pids
            
            # 【优先级5】兜底: 所有视频中找最长的非集锦视频
            non_highlight_videos = [v for v in replay_list if not is_definitely_highlight(v.get('name', ''))]
            if non_highlight_videos:
                longest = max(non_highlight_videos, key=lambda x: duration_to_seconds(x.get('duration', '00:00')))
                dur_sec = duration_to_seconds(longest.get('duration', '00:00'))
                pid = longest.get('pID', '')
                if pid and dur_sec > 1800:  # 至少30分钟
                    logger.debug(f"   ⚠️ 优先级5(兜底): {longest.get('name')} ({int(dur_sec/60)}分钟, PID: {pid})")
                    replay_pids['primary'] = pid
                    return replay_pids
            
            logger.debug(f"   ❌ 未找到合适的全场回放视频")
            return None if not any(replay_pids.values()) else replay_pids
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
            # 现在支持返回多语言的 PID
            replay_pids = {}  # {'mandarin': pid, 'cantonese': pid, 'primary': pid}
            if is_finished and mgdb_id:
                verified_pids = self.fetch_full_match_replay(mgdb_id)
                if verified_pids:
                    replay_pids = verified_pids  # 获取多语言 PID 字典
                    pid = verified_pids.get('primary', pid)  # 使用优先级最高的 PID
                # 如果深度抓取没有找到，保持原有的 pid（可能是空或集锦）

            try: formatted_date = datetime.strptime(date_key, '%Y%m%d').strftime('%Y-%m-%d')
            except: formatted_date = date_key
            
            comp_name = match.get('competitionName') or match.get('mgdbName', '未知赛事')

            result = {
                'date': formatted_date, 'opponent': opponent, 'is_home': is_arsenal_home,
                'title': title, 'match_status': match_status, 'is_finished': is_finished,
                'competition': comp_name
            }
            
            # 填充录像信息 - 支持多语言 PID
            if pid:
                result['migu_pid'] = pid  # 主 PID（默认中文优先）
                result['migu_detail_url'] = f"https://www.miguvideo.com/p/detail/{pid}"
            
            # 添加语言特定的 PID（便于用户选择语言）
            if replay_pids.get('mandarin'):
                result['migu_pid_mandarin'] = replay_pids.get('mandarin')
                result['migu_detail_url_mandarin'] = f"https://www.miguvideo.com/p/detail/{replay_pids.get('mandarin')}"
            if replay_pids.get('cantonese'):
                result['migu_pid_cantonese'] = replay_pids.get('cantonese')
                result['migu_detail_url_cantonese'] = f"https://www.miguvideo.com/p/detail/{replay_pids.get('cantonese')}"
            
            # 填充直播信息 (只要有 mgdbId 就填，不管完没完赛)
            if mgdb_id:
                result['migu_live_url'] = f"https://www.miguvideo.com/p/live/{mgdb_id}"
                
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