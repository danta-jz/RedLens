import requests
from bs4 import BeautifulSoup
import re

def locate_element_structure():
    print("🕵️ 正在进行元素溯源 (Nuclear Mode)...")
    url = "https://www.arsenal.com/results-and-fixtures-list"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 直接搜索包含 "Champions League" 的【文本节点】
        # 这就像在 Word 里按 Ctrl+F 一样，不关心格式，只找字
        targets = soup.find_all(string=re.compile("Champions League"))
        
        print(f"✅ 找到了 {len(targets)} 处文本节点，开始分析家谱...\n")
        
        for i, text_node in enumerate(targets[:3]): # 只看前3个，避免刷屏
            parent = text_node.parent
            grandparent = parent.parent
            
            print(f"🧬 样本 #{i+1}:")
            print(f"   🔹 文本内容: '{text_node.strip()}'")
            print(f"   🔹 父亲标签: <{parent.name}> (Class: {parent.get('class')})")
            if grandparent:
                print(f"   🔹 爷爷标签: <{grandparent.name}> (Class: {grandparent.get('class')})")
            
            # 打印爷爷的全文，看看包含什么信息
            # 这样我们就能知道怎么写正则来提取同一层级的 日期 和 对手
            if grandparent:
                clean_gp_text = grandparent.get_text(" ", strip=True)[:200] # 只截取前200字
                print(f"   👀 爷爷视野内的完整信息: {clean_gp_text}...")
            print("-" * 50)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    locate_element_structure()