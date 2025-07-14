#!/bin/bash
set -e

echo "🔄 强制安装Tesseract OCR..."

# 设置非交互模式
export DEBIAN_FRONTEND=noninteractive

# 尝试以root权限运行
echo "📦 更新包管理器..."
sudo apt-get update -y || apt-get update -y || {
    echo "⚠️ 无法更新包管理器，尝试继续..."
}

echo "🔧 安装Tesseract和相关包..."
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev || \
apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev || {
    echo "❌ 无法安装Tesseract"
    exit 1
}

# 验证安装
echo "✅ 验证Tesseract安装..."
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract安装成功！"
    tesseract --version
    which tesseract
    echo "Tesseract路径: $(which tesseract)"
else
    echo "❌ Tesseract安装失败"
    exit 1
fi

echo "📦 安装Python依赖..."
pip install -r requirements.txt

echo "🚀 构建完成！Tesseract已成功安装"