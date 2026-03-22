#!/bin/bash

# 🧪 后端 API 测试脚本
# 用法：bash test_api.sh

BASE_URL="http://localhost:5000"
COLORS_GREEN='\033[0;32m'
COLORS_RED='\033[0;31m'
COLORS_YELLOW='\033[1;33m'
COLORS_BLUE='\033[0;34m'
COLORS_NC='\033[0m' # No Color

echo -e "${COLORS_BLUE}🧪 音乐扒谱应用 - API 测试脚本${COLORS_NC}"
echo "=================================="
echo ""

# 1. 健康检查
echo -e "${COLORS_BLUE}1️⃣  健康检查...${COLORS_NC}"
RESPONSE=$(curl -s "$BASE_URL/api/health")
if [[ $RESPONSE == *"ok"* ]]; then
  echo -e "${COLORS_GREEN}✓ 后端运行正常${COLORS_NC}"
else
  echo -e "${COLORS_RED}✗ 后端未响应，请先运行: cd ~/project/music_project/backend && python app.py${COLORS_NC}"
  exit 1
fi
echo ""

# 2. 获取状态
echo -e "${COLORS_BLUE}2️⃣  获取应用状态...${COLORS_NC}"
curl -s "$BASE_URL/api/status" | python3 -m json.tool
echo ""

# 3. 获取可用源
echo -e "${COLORS_BLUE}3️⃣  获取可用音乐源...${COLORS_NC}"
SOURCES=$(curl -s "$BASE_URL/api/sources")
echo "$SOURCES" | python3 -m json.tool
echo ""

# 4. 切换到本地文件源
echo -e "${COLORS_BLUE}4️⃣  切换到本地文件源...${COLORS_NC}"
curl -s -X POST "$BASE_URL/api/sources/switch" \
  -H "Content-Type: application/json" \
  -d '{
    "source_name": "local_file",
    "config": {
      "music_dir": "~/Music",
      "recursive": true
    }
  }' | python3 -m json.tool
echo ""

# 5. 搜索本地音乐
echo -e "${COLORS_BLUE}5️⃣  搜索本地音乐 (关键词: 'song')...${COLORS_NC}"
SEARCH=$(curl -s "$BASE_URL/api/search?q=song&limit=3")
TOTAL=$(echo "$SEARCH" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

if [ "$TOTAL" -gt 0 ]; then
  echo "$SEARCH" | python3 -m json.tool
else
  echo -e "${COLORS_YELLOW}⚠️  本地 Music 文件夹中未找到音乐文件${COLORS_NC}"
  echo "   提示：在 ~/Music 文件夹中放入一些 .mp3 文件来测试搜索功能"
fi
echo ""

# 6. 测试文件上传（需要实际文件）
echo -e "${COLORS_BLUE}6️⃣  测试文件上传...${COLORS_NC}"

# 创建一个测试音频文件（10秒的无声 MP3）
TEST_FILE="/tmp/test_audio.mp3"
if [ ! -f "$TEST_FILE" ]; then
  echo "   创建测试音频文件..."
  # 使用 ffmpeg 创建 10 秒的无声 MP3（如果已安装）
  if command -v ffmpeg &> /dev/null; then
    ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 10 -q:a 9 -acodec libmp3lame "$TEST_FILE" 2>/dev/null
    echo "   ✓ 测试文件已创建"
  else
    echo -e "${COLORS_YELLOW}⚠️  ffmpeg 未安装，跳过音频文件创建${COLORS_NC}"
    echo "   安装：sudo apt-get install ffmpeg"
    TEST_FILE=""
  fi
fi

if [ -f "$TEST_FILE" ]; then
  echo "   上传文件..."
  UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/music/upload" \
    -F "file=@$TEST_FILE")
  FILENAME=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('filename', ''))" 2>/dev/null)
  
  if [ -n "$FILENAME" ]; then
    echo -e "${COLORS_GREEN}✓ 文件上传成功${COLORS_NC}"
    echo "  文件名: $FILENAME"
    echo "$UPLOAD_RESPONSE" | python3 -m json.tool
    
    # 7. 测试单旋律提取
    echo ""
    echo -e "${COLORS_BLUE}7️⃣  测试单旋律提取...${COLORS_NC}"
    echo "   处理中（可能需要 10-30 秒）..."
    MELODY=$(curl -s -X POST "$BASE_URL/api/transcribe/melody" \
      -H "Content-Type: application/json" \
      -d "{\"audio_file\": \"$FILENAME\"}")
    
    MELODY_STATUS=$(echo "$MELODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null)
    if [ "$MELODY_STATUS" = "success" ]; then
      echo -e "${COLORS_GREEN}✓ 单旋律提取成功${COLORS_NC}"
      echo "$MELODY" | python3 -m json.tool | head -30
    else
      echo -e "${COLORS_RED}✗ 单旋律提取失败${COLORS_NC}"
      echo "$MELODY" | python3 -m json.tool
    fi
  else
    echo -e "${COLORS_RED}✗ 文件上传失败${COLORS_NC}"
  fi
else
  echo -e "${COLORS_YELLOW}⚠️  跳过文件上传测试${COLORS_NC}"
fi

echo ""
echo "=================================="
echo -e "${COLORS_GREEN}✅ 测试完成！${COLORS_NC}"
echo ""
echo "📚 更多信息："
echo "  - API 文档：http://localhost:5000"
echo "  - 测试指南：API_TESTING_GUIDE.md"
echo "  - 代码示例：USAGE_EXAMPLES.md"
echo ""
