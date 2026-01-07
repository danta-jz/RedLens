#!/usr/bin/env python3
"""
RedLens 数据工厂 - 阿森纳赛程抓取模块
Data Factory Module for Arsenal Fixtures

功能：从英超官网或阿森纳官网抓取赛程数据
特性：幂等性、重试机制、多数据源回退
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pytz
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ===== 配置区 Configuration =====
OUTPUT_FILE = "matches.json"
ARSENAL_TEAM_ID = 1  # Arsenal's team ID on Premier League website
TIMEOUT_MS = 30000  # 30 seconds timeout
TARGET_TIMEZONE = pytz.timezone('Asia/Shanghai')  # 北京时间 UTC+8
UK_TIMEZONE = pytz.timezone('Europe/London')

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class FixtureFetcher:
    """赛程抓取器 - 极简主义设计，专注核心逻辑"""
    
    def __init__(self):
        self.matches = []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError, Exception)),
        reraise=True
    )
    async def fetch_from_premier_league(self) -> List[Dict]:
        """
        方法一：从英超官网 API 抓取数据（推荐）
        优势：结构化 JSON，稳定性高，无需复杂选择器
        """
        logger.info("🎯 尝试从英超官网抓取数据...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # 英超官网的赛程 API endpoint
                api_url = f"https://footballapi.pulselive.com/football/fixtures?comps=1&teams={ARSENAL_TEAM_ID}&compSeasons=719&page=0&pageSize=100&sort=asc&statuses=U,L"
                
                logger.info(f"📡 请求 API: {api_url}")
                response = await page.goto(api_url, wait_until='networkidle', timeout=TIMEOUT_MS)
                
                if response.status != 200:
                    raise Exception(f"API 返回状态码: {response.status}")
                
                # 解析 JSON 响应
                data = await response.json()
                fixtures = data.get('content', [])
                
                logger.info(f"✅ 成功获取 {len(fixtures)} 场比赛")
                
                matches = []
                for fixture in fixtures:
                    match = self._parse_premier_league_fixture(fixture)
                    if match:
                        matches.append(match)
                
                return matches
                
            except Exception as e:
                logger.error(f"❌ 英超官网抓取失败: {str(e)}")
                raise
            finally:
                await browser.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError, Exception)),
        reraise=True
    )
    async def fetch_from_arsenal_website(self) -> List[Dict]:
        """
        方法二：从阿森纳官网抓取（备用方案）
        优势：官方数据，更新及时
        """
        logger.info("🎯 尝试从阿森纳官网抓取数据...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                url = "https://www.arsenal.com/fixtures"
                logger.info(f"📡 访问页面: {url}")
                
                await page.goto(url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
                
                # 等待赛程列表加载
                await page.wait_for_selector('.fixture-list', timeout=TIMEOUT_MS)
                
                # 执行页面内的 JavaScript 提取数据
                matches = await page.evaluate("""
                    () => {
                        const fixtures = [];
                        const items = document.querySelectorAll('.fixture');
                        
                        items.forEach(item => {
                            try {
                                const dateEl = item.querySelector('.fixture__date');
                                const timeEl = item.querySelector('.fixture__time');
                                const opponentEl = item.querySelector('.fixture__opponent-name');
                                const venueEl = item.querySelector('.fixture__venue');
                                const homeAwayEl = item.querySelector('.fixture__home-away');
                                
                                if (dateEl && opponentEl) {
                                    fixtures.push({
                                        date: dateEl.textContent.trim(),
                                        time: timeEl ? timeEl.textContent.trim() : 'TBC',
                                        opponent: opponentEl.textContent.trim(),
                                        venue: venueEl ? venueEl.textContent.trim() : '',
                                        isHome: homeAwayEl ? homeAwayEl.textContent.includes('Home') : null
                                    });
                                }
                            } catch (e) {
                                console.error('Parse error:', e);
                            }
                        });
                        
                        return fixtures;
                    }
                """)
                
                logger.info(f"✅ 成功获取 {len(matches)} 场比赛")
                
                # 标准化数据格式
                normalized_matches = []
                for match in matches:
                    normalized = self._parse_arsenal_website_fixture(match)
                    if normalized:
                        normalized_matches.append(normalized)
                
                return normalized_matches
                
            except Exception as e:
                logger.error(f"❌ 阿森纳官网抓取失败: {str(e)}")
                raise
            finally:
                await browser.close()
    
    def _parse_premier_league_fixture(self, fixture: Dict) -> Optional[Dict]:
        """解析英超官网 API 返回的数据结构"""
        try:
            # 提取比赛时间
            kickoff = fixture.get('kickoff', {})
            date_str = kickoff.get('label')  # 格式如 "Sat 15 Jan 15:00"
            
            if not date_str or date_str == "TBC":
                return None
            
            # 解析日期时间
            match_datetime = self._parse_datetime(date_str)
            if not match_datetime:
                return None
            
            # 转换为北京时间
            beijing_time = match_datetime.astimezone(TARGET_TIMEZONE)
            
            # 提取主客队信息
            teams = fixture.get('teams', [])
            home_team = teams[0] if len(teams) > 0 else {}
            away_team = teams[1] if len(teams) > 1 else {}
            
            # 判断阿森纳是主队还是客队
            is_arsenal_home = home_team.get('team', {}).get('id') == ARSENAL_TEAM_ID
            opponent = away_team.get('team', {}).get('name') if is_arsenal_home else home_team.get('team', {}).get('name')
            
            # 提取场馆信息
            venue_info = fixture.get('ground', {})
            venue = venue_info.get('name', 'TBC')
            
            return {
                'date': beijing_time.strftime('%Y-%m-%d'),
                'time': beijing_time.strftime('%H:%M'),
                'opponent': opponent,
                'is_home': is_arsenal_home,
                'venue': venue
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 解析比赛数据失败: {str(e)}")
            return None
    
    def _parse_arsenal_website_fixture(self, fixture: Dict) -> Optional[Dict]:
        """解析阿森纳官网返回的数据结构"""
        try:
            date_str = fixture.get('date', '')
            time_str = fixture.get('time', 'TBC')
            
            if not date_str or time_str == 'TBC':
                return None
            
            # 组合日期和时间
            datetime_str = f"{date_str} {time_str}"
            match_datetime = self._parse_datetime(datetime_str)
            
            if not match_datetime:
                return None
            
            # 转换为北京时间
            beijing_time = match_datetime.astimezone(TARGET_TIMEZONE)
            
            return {
                'date': beijing_time.strftime('%Y-%m-%d'),
                'time': beijing_time.strftime('%H:%M'),
                'opponent': fixture.get('opponent', ''),
                'is_home': fixture.get('isHome', True),
                'venue': fixture.get('venue', 'TBC')
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 解析比赛数据失败: {str(e)}")
            return None
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        智能日期解析器 - 支持多种格式
        示例：
        - "Sat 15 Jan 15:00"
        - "15/01/2025 15:00"
        - "2025-01-15 15:00"
        """
        formats = [
            '%a %d %b %H:%M',      # Sat 15 Jan 15:00
            '%d/%m/%Y %H:%M',      # 15/01/2025 15:00
            '%Y-%m-%d %H:%M',      # 2025-01-15 15:00
            '%d %B %Y %H:%M',      # 15 January 2025 15:00
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # 如果没有年份信息，默认为当前年份
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                # 假设原始时间为英国时间
                dt_uk = UK_TIMEZONE.localize(dt)
                return dt_uk
            except ValueError:
                continue
        
        logger.warning(f"⚠️ 无法解析日期格式: {date_str}")
        return None
    
    async def fetch(self) -> List[Dict]:
        """
        核心方法：多数据源智能回退
        遵循 Fail-Fast 原则，优先使用最稳定的数据源
        """
        logger.info("🚀 RedLens 数据工厂启动...")
        
        # 策略一：尝试英超官网 API（推荐）
        try:
            matches = await self.fetch_from_premier_league()
            if matches:
                logger.info("✅ 使用数据源：英超官网 API")
                return matches
        except Exception as e:
            logger.warning(f"⚠️ 英超官网不可用，准备回退...")
        
        # 策略二：回退到阿森纳官网
        try:
            matches = await self.fetch_from_arsenal_website()
            if matches:
                logger.info("✅ 使用数据源：阿森纳官网")
                return matches
        except Exception as e:
            logger.error(f"❌ 所有数据源均不可用")
            raise Exception("所有数据源均失败，请检查网络连接或稍后重试")
        
        return []
    
    def save_to_json(self, matches: List[Dict]):
        """
        保存为 JSON - 幂等性设计
        多次运行结果一致，确保数据完整性
        """
        try:
            # 按日期排序
            matches_sorted = sorted(matches, key=lambda x: (x['date'], x['time']))
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(matches_sorted, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 数据已保存至 {OUTPUT_FILE}")
            logger.info(f"📊 共 {len(matches_sorted)} 场比赛")
            
            # 打印预览
            if matches_sorted:
                logger.info("📅 最近一场比赛:")
                first_match = matches_sorted[0]
                logger.info(f"   {first_match['date']} {first_match['time']} "
                           f"{'主场 vs' if first_match['is_home'] else '客场 @'} "
                           f"{first_match['opponent']}")
        
        except Exception as e:
            logger.error(f"❌ 保存文件失败: {str(e)}")
            raise


async def main():
    """
    主函数 - 极简执行流程
    体现 RedLens 的"手术刀"哲学：精准、高效、无冗余
    """
    try:
        fetcher = FixtureFetcher()
        matches = await fetcher.fetch()
        
        if not matches:
            logger.warning("⚠️ 未获取到任何比赛数据")
            return
        
        fetcher.save_to_json(matches)
        logger.info("✅ 数据工厂任务完成")
        
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
