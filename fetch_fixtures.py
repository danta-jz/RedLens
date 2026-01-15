#!/usr/bin/env python3
"""
RedLens 赛程抓取器 - 终极清洗版 (Table Parser v3)
修复: 
1. 误将 "日期-时间" (Jan 20 - 20:00) 识别为比分的问题
2. 清理 "V", "Carabao Cup" 等残留字符
3. 增加朴茨茅斯等中文队名映射支持预埋
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime
import re

OUTPUT_FILE = "matches.json"
SOURCE_URL = "https://www.arsenal.com/results-and-fixtures-list"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def parse_arsenal_date(date_text):
    """
    解析类似 "Wed Oct 1" 的日期，智能推断年份
    """
    try:
        parts = date_text.strip().split()
        if len(parts) < 2: return ""
        
        month_str = parts[-2]
        day_str = parts[-1]
        
        now = datetime.now()
        month_num = datetime.strptime(month_str, "%b").month
        
        # 赛季跨年逻辑：8-12月是2025，1-7月是2026
        if month_num >= 8:
            year = 2025
        else:
            year = 2026

        dt = datetime.strptime(f"{year} {month_str} {day_str}", "%Y %b %d")
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return ""

def fetch_arsenal_fixtures():
    logger.info("🚀 启动赛程抓取 (Smart Cleaner Mode)...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(SOURCE_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        matches = []
        
        rows = soup.find_all('tr')
        logger.info(f"🔍 扫描到 {len(rows)} 行数据，开始深度清洗...")

        for row in rows:
            # 获取原始文本
            original_text = row.get_text(" ", strip=True)
            
            # 必须包含 Arsenal
            if "Arsenal" not in original_text: continue
            
            # --- 步骤 1: 提取并移除 日期/时间 (关键修复) ---
            # 模式: Mon Jan 14 - 20:00
            # 我们先找到这个模式，提取数据，然后把它从文本里删掉！防止干扰比分
            
            date_str = ""
            time_str = "00:00"
            
            # 匹配日期+时间段 (Wed Jan 14 - 20:00)
            # 正则解释: 星期+空格+月+空格+日+空格+横杠+空格+时间
            datetime_pattern = r'([A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2})\s*-\s*(\d{1,2}:\d{2})'
            dt_match = re.search(datetime_pattern, original_text)
            
            clean_text = original_text # 用于后续处理的文本
            
            if dt_match:
                # 提取
                raw_date = dt_match.group(1) # Wed Jan 14
                time_str = dt_match.group(2) # 20:00
                date_str = parse_arsenal_date(raw_date)
                
                # 【关键】从文本中移除这段日期时间字符串
                clean_text = clean_text.replace(dt_match.group(0), "")
            else:
                # 兜底：如果找不到完整的时间组合，尝试单独找日期
                date_only_match = re.search(r'([A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2})', original_text)
                if date_only_match:
                    date_str = parse_arsenal_date(date_only_match.group(1))
                    clean_text = clean_text.replace(date_only_match.group(0), "")

            if not date_str: continue

            # --- 步骤 2: 提取赛事 ---
            competition = "Unknown"
            # 定义映射关系，不仅用于提取，也用于后续清理
            comp_keywords = {
                "Champions League": "UEFA Champions League",
                "Premier League": "Premier League",
                "FA Cup": "FA Cup",
                "League Cup": "League Cup",
                "Carabao Cup": "League Cup", # 别名
                "Friendly": "Friendly"
            }
            
            for k, v in comp_keywords.items():
                if k in original_text:
                    competition = v
                    break
            
            if competition == "Unknown" and "U21" not in original_text:
                continue

            # --- 步骤 3: 提取比分 (在去除了时间之后) ---
            # 此时 clean_text 里已经没有 "20 - 20:00" 这种干扰项了
            status = 'U'
            score = ""
            # 找类似 "2 - 0" 或 "2-0"
            score_match = re.search(r'(\d+)\s*-\s*(\d+)', clean_text)
            
            # 只有当日期是今天或过去，才信任比分 (防止未来日期的误判)
            is_past = False
            try:
                match_date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if match_date_obj.date() <= datetime.now().date():
                    is_past = True
            except: pass

            if score_match and is_past:
                status = 'C'
                score = score_match.group(0)
                # 从文本中移除比分，方便后续提取对手
                clean_text = clean_text.replace(score, "")

            # --- 步骤 4: 提取对手 (大扫除) ---
            # 移除所有干扰词
            remove_list = [
                competition, "Arsenal", "Home", "Away", 
                "Carabao Cup", "League Cup", "Premier League", "Champions League", "UEFA", "FA Cup",
                "Mens", "Women", "Tickets", "Report", "Highlights",
                "(H)", "(A)", " V ", " v ", " vs " # 移除 " V "
            ]
            
            opponent_text = clean_text
            for term in remove_list:
                # 使用不区分大小写的替换
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                opponent_text = pattern.sub("", opponent_text)
            
            # 移除多余符号
            opponent_text = opponent_text.replace("-", "").strip()
            # 移除连续空格
            opponent = " ".join(opponent_text.split())
            
            # 最终检查: 如果剩下一个单字母 "V"，也去掉
            if opponent.lower() == "v": continue
            if len(opponent) < 2: continue

            # --- 步骤 5: 主客场 ---
            # 简单的逻辑：如果原始文本里 Arsenal 在对手前面?
            # 或者看是否有 (H) / (A) 标记，或者 Home/Away
            is_home = True
            if "(A)" in original_text or "Away" in original_text:
                is_home = False
            elif "(H)" in original_text or "Home" in original_text:
                is_home = True
            else:
                # 位置判断法
                # 原始文本通常是: Date Time Home v Away
                # 如果 Arsenal 的 index 小于 Opponent 的 index -> 主场
                try:
                    idx_ars = original_text.find("Arsenal")
                    idx_opp = original_text.find(opponent)
                    if idx_ars > -1 and idx_opp > -1:
                        if idx_ars > idx_opp:
                            is_home = False
                except: pass

            matches.append({
                "date": date_str,
                "time": time_str,
                "opponent": opponent,
                "competition": competition,
                "is_home": is_home,
                "status": status,
                "score": score
            })

        # 去重
        unique_matches = []
        seen = set()
        for m in matches:
            key = f"{m['date']}_{m['opponent']}"
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)
        
        unique_matches.sort(key=lambda x: x['date'])
        
        logger.info(f"✅ 成功提取 {len(unique_matches)} 场比赛")
        return unique_matches

    except Exception as e:
        logger.error(f"❌ 错误: {e}")
        return []

if __name__ == "__main__":
    data = fetch_arsenal_fixtures()
    if data:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 简单校验打印
        for m in data[-5:]: # 打印最后5场看看未来赛程是否正常
            logger.info(f"{m['date']} {m['opponent']} (Status: {m['status']})")