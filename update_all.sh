#!/bin/bash
set -e

# ... (前半部分 echo 保持不变) ...

# 打印当前运行模式
echo "⚙️ 运行模式 (RUN_MODE): ${RUN_MODE:-force}"

# Step 1: 获取英超官方赛程
echo "📊 Step 1/4: 获取英超官方赛程..."
# 只有在 force 模式或者 matches.json 不存在时才强制更新赛程
# 为了保险起见，赛程文件很小，每次更新也没问题
python3 DataFactory/fetch_fixtures.py

# Step 2: 智能追更咪咕视频
echo "📹 Step 2/4: 智能追更咪咕视频..."
# 这里的 python 脚本内部会读取 RUN_MODE 环境变量
# 如果是 smart 模式且无比赛，脚本会在这里 exit 0 退出，不再往下执行耗时操作
python3 DataFactory/fetch_all_migu_videos.py

# 注意：如果 fetch_all_migu_videos.py 因为"没比赛"退出了，
# 我们依然需要运行后续步骤吗？
# 如果没抓到新视频，merge_data 出来的结果是一样的，
# 但为了确保 git diff 能检测到"无变化"，还是跑完流程最稳妥。
# 且 merge 和 generate 都是本地纯计算，不耗费网络资源，秒级完成。

# Step 3: 数据融合
echo "🔄 Step 3/4: 数据融合..."
python3 DataFactory/merge_data.py

# Step 4: 生成 Deep Links
echo "🔗 Step 4/4: 生成 Deep Links..."
python3 DataFactory/generate_deep_links.py

echo "✅ 完成!"