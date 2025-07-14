# 📦 Warehouse PDF处理系统 - 部署指南

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+ 
- Tesseract OCR

### 2. 安装步骤

#### Windows 用户：
```bash
# 1. 安装 Tesseract OCR
# 下载：https://github.com/UB-Mannheim/tesseract/wiki
# 安装到：C:\Program Files\Tesseract-OCR
# 添加到系统PATH环境变量

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 运行应用
cd Warehouse
python app.py
```

#### macOS/Linux 用户：
```bash
# 1. 安装 Tesseract
# macOS:
brew install tesseract

# Linux:
sudo apt install tesseract-ocr

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 运行应用
cd Warehouse
python app.py
```

### 3. 访问应用
浏览器打开：http://localhost:5000

## 🔧 环境变量配置（可选）

```bash
# 设置密钥（生产环境推荐）
export SECRET_KEY="your-production-secret-key"
```

## 📋 功能说明

1. **仓库分拣** - 按915、8090、60仓库分类PDF标签
2. **ALGIN排序** - 专门的客户标签排序功能
3. **文件重命名** - 处理后可重命名输出文件
4. **自动清理** - 1小时后自动清理临时文件

## ⚠️ 故障排除

### 问题1：tesseract command not found
**解决**：确保Tesseract已安装并添加到PATH

### 问题2：ModuleNotFoundError
**解决**：运行 `pip install -r requirements.txt`

### 问题3：Permission denied
**解决**：确保有uploads文件夹的写权限

## 📞 技术支持

如有问题，请检查：
1. Python版本是否>=3.8
2. 所有依赖包是否已安装
3. Tesseract是否正确配置
4. 防火墙是否允许5000端口