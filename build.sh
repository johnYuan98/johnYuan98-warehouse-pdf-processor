#!/bin/bash

echo "🔄 开始Render部署构建..."

# 更新包管理器
echo "📦 更新包管理器..."
apt-get update

# 安装Tesseract OCR及相关包
echo "🔧 安装Tesseract OCR..."
apt-get install -y tesseract-ocr
apt-get install -y tesseract-ocr-eng
apt-get install -y libtesseract-dev

# 验证安装
echo "✅ 验证Tesseract安装..."
tesseract --version
which tesseract

# 安装Python依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

echo "🚀 构建完成！"