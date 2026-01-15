import requests
import re
import json
import urllib3

# 禁用 SSL 警告 (解决你的 Mac 报错)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_migu_competition_ids():
    print("🕵️ 正在解剖咪咕赛程页面，寻找赛事 ID...")
    
    # 目标页面: 足球赛程页
    url = "https://www.miguvideo.com/p/schedule/5"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        # 使用 verify=False 绕过 SSL 报错
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        html = response.text
        
        print(f"✅ 页面获取成功 (长度: {len(html)})，开始扫描配置数据...")
        
        # 咪咕通常把栏目配置写在 JavaScript 变量里，或者 hidden input 里
        # 我们搜索包含 "英超" 或 "足总杯" 的附近文本
        
        # 策略 1: 查找 JSON 结构 (通常在 window.__INITIAL_STATE__ 或类似结构里)
        # 这里的正则试图匹配: "name":"英超","columnId":"xxx" 这种模式
        
        # 查找所有赛事的模式匹配
        # 匹配模式: 名字...ID
        # 这是一个宽泛的正则，试图抓取 name/title 和 id 之间的关系
        matches = re.finditer(r'["\']?name["\']?\s*:\s*["\']([^"\']+)["\'].{1,100}?["\']?columnId["\']?\s*:\s*["\']?(\d+)["\']?', html)
        
        found = {}
        for m in matches:
            name = m.group(1)
            col_id = m.group(2)
            # 过滤掉非中文或太长的干扰项
            if len(name) < 20:
                found[name] = col_id
                
        # 策略 2: 如果上面的没找到，试另一种常见的字段 "data-id"
        if not found:
             print("⚠️ 策略 1 未命中，尝试策略 2...")
             # 尝试直接搜 "英格兰足总杯" 附近的数字
             # 比如 <li data-id="1234">英格兰足总杯</li>
             search_text = "足总杯"
             idx = html.find(search_text)
             if idx != -1:
                 # 打印上下文，让我们人工看看
                 start = max(0, idx - 200)
                 end = min(len(html), idx + 200)
                 print("\n🔎 发现 '足总杯' 附近的 HTML 片段:")
                 print(html[start:end])
        
        if found:
            print("\n🎉 成功提取到赛事 ID 映射:")
            print(json.dumps(found, indent=2, ensure_ascii=False))
            print("\n💡 请告诉我 '英格兰足总杯' 或 '足总杯' 对应的数字是多少！")
        else:
            print("\n❌ 自动提取失败。请把上面打印的 'HTML 片段' 发给我分析。")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    extract_migu_competition_ids()