# 🏭 仓库PDF处理系统

专业的仓库标签分拣和排序工具，支持多种仓库类型和客户定制排序。

## 🚀 主要功能

### 1. 4DS 915，8090，60仓库分单工具
- ✅ 自动识别PDF中的仓库标签并按类型分组
- ✅ 支持915、8090、60三种仓库类型
- ✅ 智能排序和分类输出

### 2. ALGIN客户的Label排序  
- ✅ 专门针对ALGIN客户的标签排序
- ✅ 支持68种不同SKU格式的识别和排序
- ✅ 按照预设SKU顺序精确排列
- ✅ 智能OCR处理图像标签

## 📦 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动应用
```bash
python app.py
```

### 访问系统
打开浏览器访问：`http://localhost:5000`

## 📁 项目结构

### 🔥 核心文件
- `app.py` - Flask Web应用主程序
- `pdf_logic.py` - PDF处理核心逻辑（已优化）
- `requirements.txt` - 项目依赖包
- `ALGIN.xlsx` - ALGIN SKU排序参考
- `templates/index.html` - Web界面

### 📂 归档文件 
`可被删除的文件/` 文件夹包含：
- 旧版本代码备份
- 测试和调试脚本
- 临时输出文件夹
- 重复上传文件

## ⚡ 功能特点

- **智能识别**：自动区分仓库标签和ALGIN客户标签
- **精确排序**：支持68种ALGIN SKU格式，按正确顺序排列
- **OCR支持**：处理图像化的标签内容
- **Web界面**：简单易用的拖拽上传界面
- **批量处理**：支持大文件PDF的快速处理

## ✅ 测试状态

两个主要功能均已修复并完全可用：
- ✅ **仓库分单工具** - 正确识别915/8090/60仓库标签
- ✅ **ALGIN排序工具** - 准确识别151页ALGIN标签并排序

## 🔧 技术栈

- **后端**：Flask, Python 3.12+
- **PDF处理**：pdfplumber, pypdf
- **OCR**：pytesseract, Pillow  
- **前端**：HTML5, CSS3, JavaScript
- **数据处理**：pandas, openpyxl