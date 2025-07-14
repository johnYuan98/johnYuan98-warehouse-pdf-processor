@echo off
echo ========================================
echo Warehouse PDF处理系统 - 安装脚本
echo ========================================

echo.
echo 1. 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误：未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo 2. 检查Tesseract...
tesseract --version
if %errorlevel% neq 0 (
    echo 警告：未找到Tesseract OCR
    echo 请从以下链接下载安装：
    echo https://github.com/UB-Mannheim/tesseract/wiki
    echo 安装后添加到系统PATH
    pause
)

echo.
echo 3. 安装Python依赖包...
cd Warehouse
pip install -r requirements.txt

echo.
echo 4. 创建uploads目录...
if not exist "uploads" mkdir uploads

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 运行命令：
echo cd Warehouse
echo python app.py
echo.
echo 然后访问：http://localhost:5000
echo.
pause