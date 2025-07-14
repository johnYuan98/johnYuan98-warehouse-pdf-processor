#!/bin/bash
set -e

echo "🔄 Render环境 - 强制安装Tesseract OCR"

# 检查是否有权限
echo "🔍 检查环境权限..."
if [ "$(id -u)" != "0" ]; then
    echo "⚠️ 非root用户，尝试使用sudo..."
    SUDO="sudo"
else
    echo "✅ Root用户"
    SUDO=""
fi

# 设置非交互模式
export DEBIAN_FRONTEND=noninteractive

# 安装Tesseract
echo "📦 安装Tesseract OCR..."
$SUDO apt-get update -qq || echo "警告: apt-get update失败"
$SUDO apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    pkg-config || {
    echo "❌ Tesseract安装失败，尝试备用方案..."
    
    # 备用方案：下载预编译二进制
    echo "📥 下载预编译Tesseract..."
    wget -q https://github.com/tesseract-ocr/tesseract/releases/download/5.3.4/tesseract-5.3.4-linux-x86_64.tar.gz
    tar -xzf tesseract-5.3.4-linux-x86_64.tar.gz
    export PATH=$PWD/tesseract-5.3.4-linux-x86_64/bin:$PATH
    export TESSDATA_PREFIX=$PWD/tesseract-5.3.4-linux-x86_64/share/tessdata
}

# 验证安装
echo "✅ 验证Tesseract..."
if command -v tesseract >/dev/null 2>&1; then
    tesseract --version
    tesseract --list-langs
    echo "Tesseract路径: $(which tesseract)"
    echo "✅ Tesseract验证成功"
else
    echo "❌ Tesseract验证失败"
    exit 1
fi

# 安装Python依赖
echo "📦 安装Python依赖..."
pip install --no-cache-dir -r requirements.txt

echo "🚀 所有依赖安装完成！"