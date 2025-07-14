# 🚀 Render 部署指南

## 📋 部署准备

### 1. 文件确认
确保以下文件存在并正确配置：

- ✅ `app.py` - Flask应用主文件
- ✅ `pdf_logic.py` - PDF处理逻辑（已配置动态Tesseract路径）
- ✅ `requirements.txt` - Python依赖（包含gunicorn）
- ✅ `build.sh` - Render构建脚本（安装Tesseract）
- ✅ `render.yaml` - Render服务配置
- ✅ `Procfile` - 备用启动配置
- ✅ `.gitignore` - Git忽略文件
- ✅ `uploads/.gitkeep` - 确保uploads目录存在

### 2. 核心修改说明

#### Tesseract OCR配置 (pdf_logic.py)
- ✅ 动态检测Tesseract路径（支持Windows/Linux）
- ✅ 自动fallback到系统PATH中的tesseract
- ✅ 错误处理和警告信息

#### Flask应用配置 (app.py)
- ✅ 支持PORT环境变量
- ✅ 生产环境自动禁用debug模式
- ✅ 绑定到0.0.0.0以接受外部连接

#### 构建脚本 (build.sh)
- ✅ 自动安装Tesseract OCR及依赖
- ✅ 验证安装状态
- ✅ 安装Python依赖

## 🚀 Render部署步骤

### 方法1: 直接从Git仓库部署

1. **将代码推送到Git仓库**
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **在Render上创建新服务**
   - 登录 [Render Dashboard](https://dashboard.render.com)
   - 点击 "New" → "Web Service"
   - 连接你的Git仓库
   - 选择分支（通常是main）

3. **配置服务设置**
   - **Name**: warehouse-pdf-processor（或任何你喜欢的名称）
   - **Environment**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - **Plan**: Free（或根据需要选择）

4. **设置环境变量**（可选）
   - `SECRET_KEY`: 让Render自动生成
   - `FLASK_ENV`: production

### 方法2: 使用render.yaml自动配置

如果你的仓库包含`render.yaml`文件，Render会自动读取配置：

1. 推送代码到Git仓库
2. 在Render中选择 "Blueprint" 部署方式
3. Render会自动应用`render.yaml`中的配置

## ✅ 部署后验证

### 1. 检查构建日志
确保看到以下信息：
```
🔄 开始Render部署构建...
📦 更新包管理器...
🔧 安装Tesseract OCR...
✅ 验证Tesseract安装...
tesseract 4.x.x
/usr/bin/tesseract
📦 安装Python依赖...
🚀 构建完成！
```

### 2. 检查应用日志
应用启动时应该看到：
```
✅ Tesseract路径设置为: /usr/bin/tesseract
```

### 3. 功能测试
- 访问部署的URL
- 上传一个PDF文件测试仓库分拣功能
- 测试ALGIN标签排序功能
- 验证OCR识别是否正常工作

## 🔧 故障排除

### 问题1: Build失败 - tesseract安装错误
**解决方案**:
- 检查`build.sh`文件权限
- 确保脚本有执行权限：`chmod +x build.sh`

### 问题2: 应用启动失败
**解决方案**:
- 检查`requirements.txt`中是否包含`gunicorn`
- 验证`app.py`中的端口配置

### 问题3: OCR功能不工作
**解决方案**:
- 检查应用日志中的Tesseract路径设置
- 确保构建过程中Tesseract安装成功

### 问题4: 文件上传失败
**解决方案**:
- 确保uploads目录存在
- 检查文件权限设置
- Render的临时文件系统是只读的，应用会自动处理

## 🎯 最佳实践

1. **环境变量**: 在生产环境中设置适当的SECRET_KEY
2. **监控**: 使用Render的监控功能查看应用性能
3. **日志**: 定期检查应用日志确保一切正常
4. **更新**: 定期更新依赖包和Tesseract版本

## 📞 支持

如果遇到问题：
1. 检查Render的构建和运行日志
2. 验证所有必需文件是否存在
3. 确认Git仓库是否包含最新的部署配置

🚀 **部署完成后，你的PDF处理应用就可以在Render上正常运行了！**