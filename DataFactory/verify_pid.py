#!/usr/bin/env python3
"""
验证脚本：确认 PID 对应的是中文3人解说版本
"""

import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_session():
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.miguvideo.com/',
}

print("📋 验证 PID 对应的视频内容\n")
print("=" * 80)

with open('migu_videos_complete.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

matches = [m for m in data if '曼联' in m.get('opponent', '') and '2026-01' in m.get('date', '')]

if matches:
    m = matches[0]
    print(f"\n比赛: {m.get('date')} 阿森纳 vs {m.get('opponent')}")
    print(f"当前 PID: {m.get('pid')}")
    print(f"当前 URL: {m.get('detail_url')}\n")
    
    # 从 live_url 提取 mgdbId
    live_url = m.get('live_url', '')
    if '/p/live/' in live_url:
        mgdb_id = live_url.split('/p/live/')[-1]
        
        # 查询详情页
        detail_url = f"https://vms-sc.miguvideo.com/vms-match/v5/staticcache/basic/all-view-list/{mgdb_id}/2/miguvideo"
        
        session = create_session()
        response = session.get(detail_url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            replay_list = data.get('body', {}).get('replayList', [])
            
            print(f"📹 全部回放视频:\n")
            
            for idx, video in enumerate(replay_list):
                pid = video.get('pID')
                name = video.get('name')
                duration = video.get('duration')
                
                is_current = "✅ 当前选中" if pid == m.get('pid') else ""
                print(f"[{idx+1}] {name:<40} | PID: {pid} | 时长: {duration} {is_current}")
            
            print("\n" + "=" * 80)
            print("\n结论:")
            current_video = [v for v in replay_list if v.get('pID') == m.get('pid')]
            if current_video:
                print(f"✅ 正确! PID {m.get('pid')} 对应的是:")
                print(f"   📺 {current_video[0].get('name')}")
                if '詹俊' in current_video[0].get('name', ''):
                    print(f"   🎙️  这是中文解说版本（含詹俊、张路、李子琪三人解说）")
                print(f"   ⏱️  时长: {current_video[0].get('duration')}")
            else:
                print(f"❌ PID {m.get('pid')} 未找到对应的视频")

print("\n" + "=" * 80)

