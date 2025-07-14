from flask import Flask, request, render_template, redirect, url_for, send_file, flash, jsonify, session
import os
import time
import glob
import tempfile
import shutil
import threading
import re
from werkzeug.utils import secure_filename
from pdf_logic import process_pdf

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Fix for time variable conflict issue - version 2
print("🔧 Starting warehouse PDF processor with time conflict fix v2", flush=True)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 临时文件管理
TEMP_FILES = {}  # 存储临时文件信息 {session_id: {'files': [], 'timestamp': time}}
TEMP_CLEANUP_DELAY = 3600  # 1小时后清理未下载的文件

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_session_id():
    """获取或创建session ID"""
    if 'session_id' not in session:
        session['session_id'] = str(int(time.time() * 1000))  # 使用时间戳作为session ID
    return session['session_id']

def cleanup_temp_files(session_id):
    """清理指定session的临时文件"""
    if session_id in TEMP_FILES:
        temp_info = TEMP_FILES[session_id]
        for file_path in temp_info.get('files', []):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                # 清理空的临时目录
                temp_dir = os.path.dirname(file_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                print(f"清理文件失败 {file_path}: {e}")
        del TEMP_FILES[session_id]

def schedule_cleanup(session_id, delay=TEMP_CLEANUP_DELAY):
    """计划清理临时文件"""
    def delayed_cleanup():
        time.sleep(delay)
        cleanup_temp_files(session_id)
    
    thread = threading.Thread(target=delayed_cleanup)
    thread.daemon = True
    thread.start()

def store_temp_files(session_id, file_paths):
    """存储临时文件信息"""
    TEMP_FILES[session_id] = {
        'files': file_paths,
        'timestamp': time.time()
    }
    
    # 清理旧的temp_output目录
    cleanup_old_temp_dirs()

def cleanup_old_temp_dirs():
    """清理超过2小时的临时输出目录"""
    try:
        temp_output_dir = os.path.join(os.getcwd(), 'temp_output')
        if not os.path.exists(temp_output_dir):
            return
            
        current_time = time.time()
        for item in os.listdir(temp_output_dir):
            item_path = os.path.join(temp_output_dir, item)
            if os.path.isdir(item_path):
                # 检查目录创建时间
                dir_time = os.path.getctime(item_path)
                if current_time - dir_time > 7200:  # 2小时 = 7200秒
                    import shutil
                    shutil.rmtree(item_path)
                    print(f"🗑️ 清理过期目录: {item_path}", flush=True)
    except Exception as e:
        print(f"⚠️ 清理临时目录失败: {str(e)}", flush=True)

def get_recent_results():
    """获取当前session的处理结果"""
    session_id = get_session_id()
    if session_id in TEMP_FILES:
        temp_info = TEMP_FILES[session_id]
        files = temp_info.get('files', [])
        
        # 检查文件是否还存在
        existing_files = [f for f in files if os.path.exists(f)]
        
        if existing_files:
            # 区分仓库文件和ALGIN文件
            warehouse_files = []
            algin_file = None
            
            for file_path in existing_files:
                filename = os.path.basename(file_path)
                if 'ALGIN' in filename or 'algin' in filename.lower():
                    algin_file = file_path
                else:
                    warehouse_files.append(file_path)
            
            return {
                'output_files': warehouse_files if warehouse_files else None,
                'sorted_file': algin_file
            }
    
    return {'output_files': None, 'sorted_file': None}

@app.route('/')
def index():
    # 检查是否有最近的处理结果
    recent = get_recent_results()
    return render_template('index.html', 
                         output_files=recent['output_files'], 
                         sorted_file=recent['sorted_file'])

@app.route('/', methods=['POST'])
def upload_warehouse():
    """处理仓库分拣功能"""
    print("🔄 收到仓库分拣请求", flush=True)
    if 'pdf_file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and file.filename and allowed_file(file.filename):
        timestamp = str(int(time.time()))
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        try:
            print(f"📁 创建临时目录处理文件: {filename}", flush=True)
            # 使用应用内的输出目录，更可靠
            new_timestamp = int(time.time())
            temp_dir = os.path.join(os.getcwd(), 'temp_output', f"warehouse_{new_timestamp}")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"📂 临时目录: {temp_dir}", flush=True)
            results = process_pdf(filepath, temp_dir, mode="warehouse")
            print(f"✅ 处理完成，生成了 {len(results)} 个文件", flush=True)
            
            # 存储临时文件信息
            session_id = get_session_id()
            store_temp_files(session_id, results)
            
            # 计划清理（1小时后）
            schedule_cleanup(session_id, TEMP_CLEANUP_DELAY)
            
            flash(f'Successfully processed! Generated {len(results)} files.')
            return render_template('index.html', output_files=results)
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload a PDF file.')
    return redirect(url_for('index'))

@app.route('/sort_labels', methods=['POST'])
def sort_labels():
    """处理ALGIN客户Label排序功能"""
    print("🔄 收到ALGIN排序请求", flush=True)
    if 'pdf_file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and file.filename and allowed_file(file.filename):
        timestamp = str(int(time.time()))
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        try:
            print(f"📁 创建ALGIN临时目录处理文件: {filename}", flush=True)
            # 使用应用内的输出目录，更可靠
            new_timestamp = int(time.time())
            temp_dir = os.path.join(os.getcwd(), 'temp_output', f"algin_{new_timestamp}")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"📂 ALGIN临时目录: {temp_dir}", flush=True)
            results = process_pdf(filepath, temp_dir, mode="algin")
            print(f"✅ ALGIN处理完成，生成了 {len(results)} 个文件", flush=True)
            
            # 存储临时文件信息
            session_id = get_session_id()
            store_temp_files(session_id, results)
            
            # 计划清理（1小时后）
            schedule_cleanup(session_id, TEMP_CLEANUP_DELAY)
            
            # 对于ALGIN排序，我们只返回第一个结果作为sorted_file
            sorted_file = results[0] if results else None
            
            flash(f'Successfully processed! Generated {len(results)} files.')
            return render_template('index.html', sorted_file=sorted_file)
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload a PDF file.')
    return redirect(url_for('index'))

@app.route('/rename_file', methods=['POST'])
def rename_file():
    """重命名文件功能"""
    try:
        data = request.get_json()
        old_filename = data.get('old_filename')
        new_filename = data.get('new_filename')
        
        if not old_filename or not new_filename:
            return jsonify({'success': False, 'error': 'Missing filename parameters'})
        
        # 确保新文件名有.pdf扩展名
        if not new_filename.lower().endswith('.pdf'):
            new_filename += '.pdf'
        
        # 检查文件名是否包含不允许的字符
        if re.search(r'[<>:"/\\|?*]', new_filename):
            return jsonify({'success': False, 'error': 'Filename contains invalid characters'})
        
        # 使用session管理的临时文件信息
        session_id = get_session_id()
        
        file_found = False
        old_path = None
        new_path = None
        
        # 首先在当前session的临时文件中查找
        if session_id in TEMP_FILES:
            temp_info = TEMP_FILES[session_id]
            temp_files = temp_info.get('files', [])
            
            for file_path in temp_files:
                file_basename = os.path.basename(file_path)
                file_exists = os.path.exists(file_path)
                
                if file_basename == old_filename and file_exists:
                    old_path = file_path
                    new_path = os.path.join(os.path.dirname(file_path), new_filename)
                    file_found = True
                    break
        
        # 如果在session中没找到，搜索所有临时目录（安全fallback）
        if not file_found:
            
            # 只搜索系统临时目录中的相关临时目录
            temp_base = tempfile.gettempdir()
            algin_pattern = os.path.join(temp_base, "algin_*")
            warehouse_pattern = os.path.join(temp_base, "warehouse_*")
            
            for pattern in [algin_pattern, warehouse_pattern]:
                matching_dirs = glob.glob(pattern)
                
                for dir_path in matching_dirs:
                    potential_path = os.path.join(dir_path, old_filename)
                    if os.path.exists(potential_path):
                        old_path = potential_path
                        new_path = os.path.join(dir_path, new_filename)
                        file_found = True
                        break
                if file_found:
                    break
        
        if not file_found:
            return jsonify({'success': False, 'error': f'File "{old_filename}" not found. Please re-process your file.'})
        
        # 检查新文件名是否已存在
        if os.path.exists(new_path):
            return jsonify({'success': False, 'error': f'File "{new_filename}" already exists'})
        
        # 执行重命名
        os.rename(old_path, new_path)
        
        # 更新临时文件信息
        if session_id in TEMP_FILES:
            temp_info = TEMP_FILES[session_id]
            updated_files = []
            for file_path in temp_info.get('files', []):
                if file_path == old_path:
                    updated_files.append(new_path)
                else:
                    updated_files.append(file_path)
            TEMP_FILES[session_id]['files'] = updated_files
        
        return jsonify({
            'success': True, 
            'new_filename': new_filename,
            'old_path': old_path,
            'new_path': new_path
        })
        
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied. File may be in use.'})
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'File not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Rename failed: {str(e)}'})

@app.route('/clear_results', methods=['POST'])
def clear_results():
    """清除当前显示的结果，准备新的处理"""
    return jsonify({'success': True, 'message': 'Results cleared'})

@app.route('/download/<path:filename>')
def download_file(filename):
    """下载文件，支持临时文件自动清理"""
    try:
        print(f"📥 下载请求: {filename}", flush=True)
        
        # 处理文件路径
        if filename.startswith('app/'):
            # 如果路径以'app/'开头，去掉这个前缀并转为绝对路径
            clean_filename = filename[4:]  # 去掉'app/'前缀
            abs_filename = os.path.join(os.getcwd(), clean_filename)
            print(f"🔄 清理路径前缀，转换为: {abs_filename}", flush=True)
        elif not os.path.isabs(filename):
            # 其他相对路径直接在当前工作目录中查找
            abs_filename = os.path.join(os.getcwd(), filename)
            print(f"🔄 转换为绝对路径: {abs_filename}", flush=True)
        else:
            abs_filename = filename
        
        # 检查文件是否存在
        if not os.path.exists(abs_filename):
            print(f"❌ 文件不存在: {abs_filename}", flush=True)
            print(f"📂 当前工作目录: {os.getcwd()}", flush=True)
            
            # 尝试在临时目录中查找
            import glob
            # 搜索应用内的temp_output目录和系统/tmp目录
            temp_files = (
                glob.glob(f"{os.getcwd()}/temp_output/*/*.pdf") + 
                glob.glob(f"/tmp/*/*.pdf")
            )
            print(f"🔍 找到的临时文件: {temp_files}", flush=True)
            
            # 查找匹配的文件
            target_filename = os.path.basename(filename)
            print(f"🎯 查找目标文件名: {target_filename}", flush=True)
            
            matching_files = [f for f in temp_files if os.path.basename(f) == target_filename]
            print(f"✅ 匹配的文件: {matching_files}", flush=True)
            
            if matching_files:
                # 使用找到的第一个匹配文件
                abs_filename = matching_files[0]
                print(f"🔄 使用找到的文件: {abs_filename}", flush=True)
            else:
                flash('File not found')
                return redirect(url_for('index'))
        
        print(f"✅ 开始下载文件: {abs_filename}", flush=True)
        
        # 获取文件名
        filename = os.path.basename(abs_filename)
        print(f"📝 下载文件名: {filename}", flush=True)
        
        # 发送文件，添加强制下载头
        response = send_file(
            abs_filename, 
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
        # 处理中文文件名的编码问题
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename, safe='')
        
        # 添加强制下载的响应头
        response.headers['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"🔄 设置响应头: Content-Disposition=attachment; filename*=UTF-8''{encoded_filename}", flush=True)
        return response
    except Exception as e:
        print(f"❌ 下载错误: {str(e)}", flush=True)
        flash(f'Download error: {str(e)}')
        return redirect(url_for('index'))

@app.route('/clear_temp_files', methods=['POST'])
def clear_temp_files():
    """立即清理当前session的临时文件"""
    session_id = get_session_id()
    cleanup_temp_files(session_id)
    return jsonify({'success': True, 'message': 'Temporary files cleared'})

@app.route('/force_download/<path:filename>')
def force_download_file(filename):
    """强制下载文件的备选路由"""
    try:
        print(f"🔥 强制下载请求: {filename}", flush=True)
        
        # 处理文件路径
        if filename.startswith('app/'):
            clean_filename = filename[4:]
            abs_filename = os.path.join(os.getcwd(), clean_filename)
        elif not os.path.isabs(filename):
            abs_filename = os.path.join(os.getcwd(), filename)
        else:
            abs_filename = filename
            
        print(f"🔥 强制下载路径: {abs_filename}", flush=True)
        
        if not os.path.exists(abs_filename):
            # 搜索临时文件
            import glob
            temp_files = glob.glob(f"{os.getcwd()}/temp_output/*/*.pdf")
            target_filename = os.path.basename(filename)
            matching_files = [f for f in temp_files if os.path.basename(f) == target_filename]
            
            if matching_files:
                abs_filename = matching_files[0]
                print(f"🔥 找到文件: {abs_filename}", flush=True)
            else:
                return "File not found", 404
        
        # 读取文件内容并直接返回
        with open(abs_filename, 'rb') as f:
            file_data = f.read()
        
        from flask import Response
        import urllib.parse
        filename_only = os.path.basename(abs_filename)
        encoded_filename = urllib.parse.quote(filename_only, safe='')
        
        response = Response(
            file_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}',
                'Content-Type': 'application/pdf',
                'Content-Length': str(len(file_data)),
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
        print(f"🔥 强制下载响应已创建: {filename_only}", flush=True)
        return response
        
    except Exception as e:
        print(f"🔥 强制下载错误: {str(e)}", flush=True)
        return f"Download error: {str(e)}", 500

if __name__ == '__main__':
    print("🚀 启动仓库PDF处理系统...", flush=True)
    print(f"📂 当前工作目录: {os.getcwd()}", flush=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    print(f"🌐 服务启动在端口: {port}", flush=True)
    print(f"🔧 调试模式: {debug_mode}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
