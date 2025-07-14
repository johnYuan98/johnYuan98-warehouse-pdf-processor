# 📦 Warehouse PDF处理系统 - 部署指南

## 🚀 云端部署 (Render)

### 1. 快速部署步骤

1. **Fork GitHub仓库**
   - 访问：https://github.com/johnYuan98/johnYuan98-warehouse-pdf-processor
   - 点击右上角"Fork"按钮

2. **在Render创建Web Service**
   - 登录：https://render.com
   - 点击"New +" → "Web Service"
   - 连接您的GitHub账户
   - 选择fork的仓库

3. **配置部署**
   - Runtime: Python 3
   - Build Command: `./build.sh`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - 其他设置保持默认

4. **部署完成**
   - 自动安装依赖并部署
   - 获得公网访问地址

## 🛠️ 本地开发

### 环境要求
- Python 3.8+ 
- Tesseract OCR

### 安装步骤

#### Windows 用户：
```bash
# 1. 安装 Tesseract OCR
# 下载：https://github.com/UB-Mannheim/tesseract/wiki
# 安装到：C:\Program Files\Tesseract-OCR

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 运行应用
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

<<<<<<< HEAD
=======
## 🚀 云端部署 (Render)

### 自动部署到Render
本项目已配置为可直接部署到Render平台：

```bash
# 1. 推送代码到Git仓库
git add .
git commit -m "Deploy to Render"
git push origin main

# 2. 在Render上创建Web Service
# 3. 连接Git仓库，Render会自动识别配置
```

**详细部署步骤**: 参见 [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)

### 部署文件说明
- `build.sh` - 自动安装Tesseract OCR
- `render.yaml` - Render服务配置
- `Procfile` - 应用启动配置
- `requirements.txt` - 包含生产环境依赖

>>>>>>> 92f2831ec97a2c5a0aed6b7e8d18d646d1a144e1
## 📞 技术支持

如有问题，请检查：
1. Python版本是否>=3.8
2. 所有依赖包是否已安装
3. Tesseract是否正确配置
<<<<<<< HEAD
4. 防火墙是否允许5000端口
=======
4. 防火墙是否允许5000端口
5. **云端部署**: 查看Render构建日志和运行日志
>>>>>>> 92f2831ec97a2c5a0aed6b7e8d18d646d1a144e1
