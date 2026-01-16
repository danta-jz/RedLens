import requests
import json
import urllib3

# 禁用安全警告 (因为我们要忽略证书验证)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def probe_migu_competitions():
    print("🔍 正在探测咪咕视频 (忽略SSL模式)...")
    
    # 咪咕搜索接口
    url = "https://m.miguvideo.com/mgs/api/v1/mobile/search/search_all.html"
    
    # 搜索关键词：直接搜阿森纳的足总杯录像
    params = {
        "text": "阿森纳 足总杯 全场回放", 
        "searchType": "100" 
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        # 加上 Referer 增加成功率
        "Referer": "https://m.miguvideo.com/"
    }
    
    try:
        # 关键修改：verify=False (不做证书校验)
        resp = requests.get(url, params=params, headers=headers, verify=False, timeout=10)
        data = resp.json()
        
        print("✅ 接口访问成功！正在分析数据...")
        
        # 提取结果列表
        # 咪咕的搜索结果结构通常比较深
        # 我们尝试找 list 下面的 items
        
        # 打印原始 JSON 的前一段，方便人工分析
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        print(f"📊 数据预览:\n{json_str[:2000]}") # 打印前2000个字符
        
    except Exception as e:
        print(f"❌ 依然失败: {e}")

if __name__ == "__main__":
    probe_migu_competitions()