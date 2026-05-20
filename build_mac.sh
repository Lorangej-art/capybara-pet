#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  macOS 本地打包脚本
#  用法: bash build_mac.sh
#  输出: dist/CapybaraPet （双击即可运行）
# ═══════════════════════════════════════════════════════════════

set -e

echo "=== 检查 Python3 ==="
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    echo "   brew install python3"
    exit 1
fi

echo "=== 安装依赖 ==="
pip3 install PyQt5 pyinstaller

echo "=== 开始打包 ==="
pyinstaller --onefile --noconsole --name "CapybaraPet" lulu_pet.py

echo ""
echo "✅ 打包完成！"
echo "   文件位置: $(pwd)/dist/CapybaraPet"
echo ""
echo "   双击 dist/CapybaraPet 即可运行。"
echo ""
echo "   如需发送给别人，直接发这个文件即可，对方不需要装任何东西。"
echo ""
echo "   ⚠️ 首次运行时，macOS 可能会提示「无法验证开发者」。"
echo "   对方需要在 Finder 中右键 → 打开，确认一次后即可正常双击运行。"
