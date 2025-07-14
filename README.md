# 📦 Warehouse PDF处理系统

一个智能的PDF标签分拣和排序系统，支持仓库标签分类和ALGIN客户标签排序。

## 🚀 功能特性

- **🏢 仓库分拣**: 自动识别并分类915、8090、60仓库标签
- **📋 ALGIN排序**: 专门的客户标签智能排序功能
- **🔍 OCR识别**: 使用Tesseract OCR处理图像标签
- **📝 文件重命名**: 处理后可重命名输出文件
- **🧹 自动清理**: 1小时后自动清理临时文件
- **☁️ 云端部署**: 支持Render平台一键部署

## 🛠️ 快速开始

### 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/johnYuan98/johnYuan98-warehouse-pdf-processor.git
cd johnYuan98-warehouse-pdf-processor

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装Tesseract OCR
# Windows: 下载安装包 https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt install tesseract-ocr

# 4. 运行应用
python app.py
```

访问: http://localhost:5000

### ☁️ 云端部署 (Render)

1. **Fork此仓库**
2. **在Render创建Web Service**
3. **连接GitHub仓库**
4. **自动部署完成**

详细步骤: [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
