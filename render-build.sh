#!/bin/bash
set -e

echo "🔄 开始Render部署构建..."

# 尝试使用包管理器安装Tesseract
echo "🔧 尝试安装Tesseract OCR..."
if command -v apt-get &> /dev/null; then
    apt-get update || true
    apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev || true
elif command -v yum &> /dev/null; then
    yum install -y tesseract tesseract-devel || true
fi

# 验证Tesseract安装
echo "✅ 检查Tesseract安装状态..."
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract已安装"
    tesseract --version
else
    echo "⚠️ Tesseract未安装，OCR功能将不可用"
fi

# 安装Python依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

echo "🚀 构建完成！"