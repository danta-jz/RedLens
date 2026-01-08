#!/bin/bash
#
# RedLens 数据工厂 - 自动更新脚本
# 定期运行此脚本以更新赛程和录像数据
#

set -e  # 遇到错误立即退出

echo "🚀 RedLens 数据工厂开始运行..."
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 切换到脚本所在目录
cd "$(dirname "$0")"

# Step 1: 获取英超官方赛程
echo "📊 Step 1/3: 获取英超官方赛程..."
python3 fetch_fixtures.py
if [ $? -ne 0 ]; then
    echo "❌ 获取官方赛程失败"
    exit 1
fi
echo ""

# Step 2: 获取咪咕视频录像链接
echo "📹 Step 2/3: 获取咪咕视频录像..."
python3 fetch_all_migu_videos.py
if [ $? -ne 0 ]; then
    echo "❌ 获取咪咕视频失败"
    exit 1
fi
echo ""

# Step 3: 数据融合
echo "🔄 Step 3/3: 融合数据..."
python3 merge_data.py
if [ $? -ne 0 ]; then
    echo "❌ 数据融合失败"
    exit 1
fi
echo ""

echo "✅ RedLens 数据工厂完成!"
echo "📁 生成的文件:"
echo "   - matches.json              (英超官方赛程)"
echo "   - migu_videos_complete.json (咪咕视频数据)"
echo "   - matches_with_videos.json  (最终融合数据)"
echo ""

# 显示统计信息
python3 -c "
import json

with open('matches_with_videos.json', 'r') as f:
    data = json.load(f)

finished = sum(1 for m in data if m.get('status') == 'C')
with_video = sum(1 for m in data if m.get('migu_pid'))
upcoming = len(data) - finished

print('📊 数据统计:')
print(f'   总场次: {len(data)} 场')
print(f'   已完赛: {finished} 场 (有录像: {with_video} 场)')
print(f'   未完赛: {upcoming} 场')
"

echo ""
echo "💡 提示: 可以将此脚本添加到 crontab 定期运行"
echo "   例如每天凌晨2点运行: 0 2 * * * /path/to/update_all.sh"

