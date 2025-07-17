import os, re
import pdfplumber
from pypdf import PdfReader, PdfWriter
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

WAREHOUSE_PREFIXES = {
    "915": ["WZ", "WX"] + [f"X{chr(i)}" for i in range(ord("A"), ord("X")+1)],
    "8090": ["AA", "BB", "CC", "DD", "EE", "FF"],
    "60": ["GA", "GB", "GC"]
}

# 动态设置Tesseract路径以适配不同环境
import platform
import shutil
import sys

# 动态检测Tesseract路径
def setup_tesseract():
    if platform.system() == "Windows":
        tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_cmd):
            return tesseract_cmd
    
    # Linux/Unix系统（包括Render）
    tesseract_cmd = shutil.which('tesseract')
    if tesseract_cmd:
        return tesseract_cmd
    
    # 尝试常见路径
    common_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract'
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    print("⚠️ 警告: 未找到Tesseract，OCR功能可能不可用")
    return None

# 设置Tesseract命令路径
tesseract_path = setup_tesseract()
if tesseract_path and OCR_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"✅ Tesseract路径设置为: {tesseract_path}")
else:
    print("⚠️ Tesseract未找到，OCR功能不可用，但应用仍可处理文本PDF")
    OCR_AVAILABLE = False

def extract_sku_sort_key(sku_text):
    """从SKU文本中提取排序键，实现智能排序逻辑"""
    
    # 常见的ALGIN SKU格式模式
    patterns = [
        # 048-OPAC—5 格式: 数字-字母—数字
        (r'(\d{3})-([A-Z]{2,4})—(\d+)', lambda m: (int(m.group(1)), m.group(2), int(m.group(3)))),
        
        # TFO1S—BK 格式: 字母数字—字母
        (r'([A-Z0-9]{3,5})—([A-Z]{2})', lambda m: (999, m.group(1), ord(m.group(2)[0]), ord(m.group(2)[1]) if len(m.group(2)) > 1 else 0)),
        
        # 048-TL—W6KWD 格式: 数字-字母—字母数字
        (r'(\d{3})-([A-Z]{2})—([A-Z0-9]+)', lambda m: (int(m.group(1)), m.group(2), hash(m.group(3)) % 10000)),
        
        # 简单的数字-字母 格式
        (r'(\d+)-([A-Z]+)', lambda m: (int(m.group(1)), m.group(2), 0)),
        
        # 纯字母数字组合
        (r'([A-Z]{2,4})(\d+)([A-Z]*)', lambda m: (1000, m.group(1), int(m.group(2)), m.group(3))),
    ]
    
    sku_upper = sku_text.upper()
    
    # 尝试匹配各种模式
    for pattern, key_func in patterns:
        match = re.search(pattern, sku_upper)
        if match:
            try:
                return key_func(match)
            except:
                continue
    
    # 如果没有匹配任何模式，使用字母排序
    return (9999, sku_text.upper(), 0)

def is_sku_match(ocr_sku, excel_sku):
    """
    大幅增强的SKU匹配逻辑，专门优化OCR识别准确率
    """
    # 标准化处理
    ocr_clean = ocr_sku.upper().strip()
    excel_clean = excel_sku.upper().strip()
    
    # 1. 完全匹配
    if ocr_clean == excel_clean:
        return True
    
    # 2. 标准化处理 - 增强版
    def normalize_sku(sku):
        import re
        # 统一所有破折号和空格
        sku = sku.replace('—', '-').replace('_', '-').replace('–', '-')
        # 去除多余空格，但保留必要的分隔符
        sku = re.sub(r'\s+', '', sku)  # 去除所有空格
        # 处理常见OCR错误的字符替换
        replacements = {
            'TF01S': 'TFO1S',  # 关键修复：OCR常把TFO1S识别为TF01S
            'TFO15': 'TFO1S',  # S被识别为5
            'TF015': 'TFO1S',  # 综合错误
            'OPAC—': 'OPAC-', # 长破折号
            'OPAC_': 'OPAC-', # 下划线
        }
        for wrong, correct in replacements.items():
            sku = sku.replace(wrong, correct)
        return sku
    
    ocr_norm = normalize_sku(ocr_clean)
    excel_norm = normalize_sku(excel_clean)
    
    if ocr_norm == excel_norm:
        return True
    
    # 3. 数字/字母常见OCR错误纠正
    def apply_ocr_corrections(sku):
        corrections = {
            '0': 'O', 'O': '0',  # 数字0和字母O互换
            '1': 'I', 'I': '1',  # 数字1和字母I互换
            '5': 'S', 'S': '5',  # 数字5和字母S互换
            '8': 'B', 'B': '8',  # 数字8和字母B互换
            '6': '9', '9': '6',  # 数字6和9互换
            'G': '6', '6': 'G',  # 字母G和数字6互换
            'Q': 'O', 'O': 'Q',  # 字母Q和O互换
        }
        result = sku
        for wrong, correct in corrections.items():
            result = result.replace(wrong, correct)
        return result
    
    ocr_corrected = apply_ocr_corrections(ocr_norm)
    if ocr_corrected == excel_norm:
        return True
    
    # 双向纠错：也对Excel进行OCR纠错尝试
    excel_corrected = apply_ocr_corrections(excel_norm)
    if ocr_norm == excel_corrected:
        return True
    
    # 4. 智能前缀/后缀匹配（处理截断问题）
    # OCR可能截断，检查核心部分是否匹配
    if len(ocr_norm) >= 6 and len(excel_norm) >= 6:
        # 前缀匹配：OCR可能被截断
        if excel_norm.startswith(ocr_norm) and len(ocr_norm) >= len(excel_norm) * 0.7:
            return True
        # 反向：Excel在OCR中被截断
        if ocr_norm.startswith(excel_norm) and len(excel_norm) >= len(ocr_norm) * 0.7:
            return True
    
    # 5. 核心SKU提取匹配
    def extract_core_components(sku):
        import re
        # 提取主要的字母数字组件
        parts = re.findall(r'[A-Z0-9]+', sku)
        return parts
    
    ocr_parts = extract_core_components(ocr_norm)
    excel_parts = extract_core_components(excel_norm)
    
    # 检查主要组件是否匹配（允许部分缺失）
    if len(ocr_parts) >= 2 and len(excel_parts) >= 2:
        # 至少前两个主要组件匹配
        if len(ocr_parts) >= 2 and len(excel_parts) >= 2:
            if (ocr_parts[0] == excel_parts[0] and ocr_parts[1] == excel_parts[1]):
                return True
    
    # 6. 特殊SKU系列优化匹配
    
    # OPAC系列特殊处理
    if 'OPAC' in ocr_norm and 'OPAC' in excel_norm:
        import re
        ocr_num = re.search(r'OPAC-?(\d+)', ocr_norm)
        excel_num = re.search(r'OPAC-?(\d+)', excel_norm)
        if ocr_num and excel_num:
            ocr_n = ocr_num.group(1)
            excel_n = excel_num.group(1)
            # 处理5/6/9的常见混淆
            number_equivalents = {'5': '9', '9': '5', '6': '9', '9': '6'}
            if ocr_n == excel_n or number_equivalents.get(ocr_n) == excel_n:
                return True
    
    # TFO1S系列特殊处理
    if ('TFO1S' in ocr_norm or 'TF01S' in ocr_norm or 'TFO15' in ocr_norm) and 'TFO1S' in excel_norm:
        return True
    
    # TL系列特殊处理
    if 'TL' in ocr_norm and 'TL' in excel_norm:
        # 提取W后面的部分
        import re
        ocr_w_part = re.search(r'TL-?W(\w+)', ocr_norm)
        excel_w_part = re.search(r'TL-?W(\w+)', excel_norm)
        if ocr_w_part and excel_w_part:
            if ocr_w_part.group(1)[:3] == excel_w_part.group(1)[:3]:  # 前3个字符匹配
                return True
    
    # 7. 容错匹配：相似度计算
    def calculate_similarity(s1, s2):
        # 简单的编辑距离相似度
        if len(s1) == 0 or len(s2) == 0:
            return 0
        
        # 计算相同字符的比例
        min_len = min(len(s1), len(s2))
        max_len = max(len(s1), len(s2))
        
        same_chars = sum(1 for i in range(min_len) if s1[i] == s2[i])
        similarity = same_chars / max_len
        return similarity
    
    # 如果相似度很高（85%以上），认为匹配
    similarity = calculate_similarity(ocr_norm, excel_norm)
    if similarity >= 0.85 and len(ocr_norm) >= 6 and len(excel_norm) >= 6:
        return True
    
    return False

def load_algin_sku_order(excel_path="uploads/ALGIN.xlsx"):
    """加载ALGIN SKU的正确排序顺序"""
    # 使用硬编码的正确SKU顺序（用户提供的准确顺序）
    correct_order = [
        "014-HG-17061-A", "014-HG-17061-B", "014-HG-20064-BRO", "014-HG-30343-B",
        "014-HG-31803-DG", "014-HG-31804-LB", "014-HG-31804-NA", "014-HG-31901-GY",
        "014-HG-31957-BK", "014-HG-40007-ESP", "014-HG-40009-GY-A", "014-HG-40009-GY-B",
        "014-HG-40010-GY", "014-HG-40013-BRO", "014-HG-40013-WH", "014-HG-40740-DWA-A",
        "014-HG-40740-DWA-B", "014-HG-41020-WH", "014-HG-41023", "014-HG-41802-ESP",
        "014-HG-41830-APE", "014-HG-41830-CT-GYW", "014-HG-41830-GYW", "014-HG-41831-BRO",
        "014-HG-41831-HT-WHT", "014-HG-41831-WHT", "014-HG-41890-BK", "014-HG-41894-EB",
        "014-HG-41894-WS", "014-HG-41896-WH", "014-HG-41898-BE", "014-HG-43004-BRO",
        "014-HG-43301-CAM", "014-HG-43302-BRO", "014-HG-43302-WL", "014-HG-43303-CAM",
        "014-HG-43501-BK", "014-HG-43503-CH", "014-HG-43503-OAK", "014-HG-43503-WA",
        "014-HG-43505-BRO", "014-HG-44701-BK", "048-OPAC-5", "048-OPAC-5H",
        "048-OPAC-6", "048-OPAC-6H", "048-TL-W10KI", "048-TL-W10KWD",
        "048-TL-W12KWD", "048-TL-W14KWD", "048-TL-W6KWD", "048-TL-W8KWD",
        "050-HA-50028", "050-HA-50036-LT", "050-HA-50042-CT", "050-LMT-23-GY",
        "050-LMT-23-WD", "050-LMT-28-GY-B", "060-ROT-11L-WH", "060-ROT-15V2-DG",
        "060-ROT-15V2-GN", "060-ROT-15V2-RD", "060-ROT-22L-BK", "TFO1S-BK"
    ]
    
    print(f"✅ 使用正确的SKU排序顺序")
    print(f"📊 包含 {len(correct_order)} 个SKU的正确顺序")
    
    return correct_order

def is_unscanned_sku_label(text):
    """判断是否为'未能扫出SKU的label'页面 - 增强汇总页面检测"""
    if not text or not text.strip():
        return False
        
    text_upper = text.upper()
    
    # 1. 首先检查是否为汇总页面（最重要的判断）
    summary_patterns = [
        r'TOTAL\s+\d+\s+LABELS',     # "Total XX Labels"
        r'UPS:\s*\d+\s+LABELS',      # "UPS: XX Labels"
        r'SINGLE.*LABEL',            # "Single...Label"
        r'TOTAL.*\d+.*LABEL',        # 通用的Total...Label格式
    ]
    
    # 如果包含汇总模式，这就是汇总页面
    for pattern in summary_patterns:
        if re.search(pattern, text_upper):
            print(f"🔍 检测到汇总页面模式: {pattern}")
            return True
    
    # 2. 必须包含ALGIN相关标识
    has_algin = bool(re.search(r'(ALN|ALGIN|ALIGN)', text_upper))
    if not has_algin:
        return False
    
    # 3. 检查是否包含UPS信息但没有具体SKU（老的逻辑）
    ups_pattern = r'UPS\d*L'  # UPS后跟数字和L，如UPS1L, UPS128L等
    ups_matches = re.findall(ups_pattern, text_upper)
    has_ups = len(ups_matches) >= 1
    
    # 4. 检查是否包含FSO标识（表示是总结页面）
    has_fso = bool(re.search(r'FSO', text_upper))
    
    # 5. 检查是否不包含明确的产品SKU
    detailed_sku_patterns = [
        r'\b\d{3}-[A-Z]{2,4}-[A-Z0-9]+\b',    # 048-OPAC-5, 048-TL-W6KWD等
        r'\b[A-Z0-9]{4,6}-[A-Z]{2}\b',        # TFO1S-BK等
        r'\b\d{3}-[A-Z]{2,4}—\d+\b',         # 048-OPAC—5
        r'\b[A-Z0-9]{3,5}—[A-Z]{2}\b',       # TFO1S—BK
    ]
    has_detailed_sku = any(re.search(pattern, text_upper) for pattern in detailed_sku_patterns)
    
    # 6. 汇总页面的多重判断逻辑
    if has_algin:
        # 情况1: 有UPS信息、FSO标识但没有具体SKU（原逻辑）
        if has_ups and has_fso and not has_detailed_sku:
            return True
        
        # 情况2: 包含"总计"或"统计"信息的页面
        if re.search(r'(TOTAL|UPS:.*\d+|统计|总计)', text_upper):
            return True
        
        # 情况3: 页面内容很短且只包含汇总信息
        if len(text.strip()) < 200 and re.search(r'LABELS?', text_upper):
            return True
    
    return False

def extract_sort_key_for_unscanned(text):
    """为未能扫描出来SKU的label提取排序键"""
    text_upper = text.upper()
    
    # 1. 首先尝试提取SO#
    so_match = re.search(r'SO#\s*(\d+)', text_upper)
    if so_match:
        return (1, int(so_match.group(1)))  # (类型1: 有SO#, SO#数字)
    
    # 2. 如果没有SO#，尝试提取UPS标签数量
    ups_match = re.search(r'UPS:\s*(\d+)', text_upper)
    if ups_match:
        return (2, int(ups_match.group(1)))  # (类型2: 无SO#但有UPS数量, UPS数量)
    
    # 3. 默认排序键
    return (3, 0)  # (类型3: 其他, 0)

def get_warehouse_sort_key(item):
    if len(item) == 4 and isinstance(item[2], int):
        prefix, num, suffix = item[1], item[2], item[3]
        if prefix in WAREHOUSE_PREFIXES["915"]:
            return (
                WAREHOUSE_PREFIXES["915"].index(prefix),
                num
            )
    elif len(item) == 4:
        prefix, row, num = item[1], item[2], item[3]
        if prefix in WAREHOUSE_PREFIXES["8090"]:
            row_order = [f"A{chr(i)}" for i in range(ord("A"), ord("Z")+1)] + \
                        [c*2 for c in reversed("ZYXWVUTSRQP")]
            return (
                WAREHOUSE_PREFIXES["8090"].index(prefix),
                row_order.index(row) if row in row_order else len(row_order),
                num
            )
        elif prefix in WAREHOUSE_PREFIXES["60"]:
            rows_60 = ["AA", "AB", "AC", "AD"]
            return (
                WAREHOUSE_PREFIXES["60"].index(prefix),
                rows_60.index(row) if row in rows_60 else len(rows_60),
                num
            )
    return (999, 999, 999)

def process_pdf(input_pdf, output_dir, mode="warehouse"):
    print(f"🔄 开始处理PDF: {os.path.basename(input_pdf)}")
    
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    print(f"📄 总页数: {total_pages}")
    
    # 根据模式决定是否加载ALGIN SKU顺序
    if mode == "algin":
        algin_sku_order = load_algin_sku_order()
        groups = {"915": [], "8090": [], "60": [], "algin_sorted": [], "algin_unscanned": [], "algin_summary": [], "unknown": [], "blank": []}
    else:
        algin_sku_order = None
        groups = {"915": [], "8090": [], "60": [], "unknown": [], "blank": []}
    
    # 统计变量
    ocr_pages = 0
    processed_pages = 0
    
    # 重要：跟踪所有页面，确保没有页面丢失
    all_processed_pages = set()
    
    with pdfplumber.open(input_pdf) as plumber:
        for idx, page in enumerate(plumber.pages):
            processed_pages += 1
            
            # 每处理5页显示一次进度（更频繁的反馈）
            if processed_pages % 5 == 0:
                print(f"📊 处理进度: {processed_pages}/{total_pages} ({processed_pages/total_pages*100:.1f}%)")
            
            text = page.extract_text() or ""
            
            # Check if page is truly blank (no text, no images, no visual elements)
            has_visual_content = (
                len(page.images) > 0 or 
                len(page.rects) > 0 or 
                len(page.lines) > 0 or
                len(page.chars) > 0
            )
            
            # 记录页面已处理
            all_processed_pages.add(idx)
            
            # Only consider it blank if there's no text AND no visual content
            if not text.strip() and not has_visual_content:
                groups["blank"].append((idx, ""))
                continue
            
            # If no extractable text but has visual content, try OCR (for ALGIN mode)
            if mode == "algin" and not text.strip() and has_visual_content:
                ocr_pages += 1
                ocr_text = ""
                if OCR_AVAILABLE:
                    try:
                        # Convert page to image and run OCR with optimized resolution
                        page_image = page.to_image(resolution=120)  # 平衡质量和速度
                        # 优化的OCR配置（减少尝试次数）
                        ocr_configs = [
                            '--psm 6 --oem 1',  # 最快的配置，优先使用
                            '--psm 4 --oem 1',  # 备用配置
                        ]
                        for config in ocr_configs:
                            try:
                                ocr_text = pytesseract.image_to_string(page_image.original, config=config)
                                if ocr_text.strip():
                                    text = ocr_text
                                    print(f"🔍 页面{idx+1} OCR成功: {text[:50]}...")
                                    break
                            except Exception as ocr_e:
                                print(f"❌ 页面{idx+1} OCR失败: {str(ocr_e)[:50]}")
                                continue
                        if text.strip():
                            # OCR成功，继续处理
                            pass
                        else:
                            print(f"⚠️  页面{idx+1} 所有OCR配置均失败")
                            # 检查是否是未能扫出SKU的label
                            if is_unscanned_sku_label(ocr_text):
                                sort_key = extract_sort_key_for_unscanned(ocr_text)
                                groups["algin_summary"].append((idx, sort_key, ocr_text[:100]))
                                continue
                            # 假设这是ALGIN标签但无法识别
                            groups["algin_unscanned"].append((idx, "[ALGIN Label - OCR失败]"))
                            continue
                    except Exception as e:
                        print(f"❌ 页面{idx+1} OCR失败: {str(e)}")
                        groups["algin_unscanned"].append((idx, f"[ALGIN Label - OCR异常: {str(e)[:30]}]"))
                        continue
                else:
                    print(f"⚠️  页面{idx+1} OCR不可用，有视觉内容但无法处理")
                    # 如果OCR不可用，但页面有视觉内容，我们假设这可能是ALGIN标签
                    groups["algin_unscanned"].append((idx, "[ALGIN Label - OCR不可用]"))
                    continue
            
            # First, check if this is a summary page (for ALGIN mode)
            if mode == "algin" and is_unscanned_sku_label(text):
                sort_key = extract_sort_key_for_unscanned(text)
                groups["algin_summary"].append((idx, sort_key, text[:100]))
                continue
            
            # 根据模式决定处理逻辑
            if mode == "algin":
                # ALGIN排序模式 - 非常积极的识别策略
                # 根据用户反馈，几乎所有页面都应该是ALGIN标签页面
                text_upper = text.upper()
                
                # 首先检查是否明确不是ALGIN标签（仓库标签等）
                is_definitely_not_algin = False
                
                # 检查仓库模式匹配
                warehouse_patterns = [
                    r"\b([A-Z]{2})-(\d{3})-([A-Z0-9]+)\b",  # 915格式
                    r"\b([A-Z]{2})-([A-Z]{2})-(\d{2,3})\b"  # 8090/60格式
                ]
                
                for pattern in warehouse_patterns:
                    if re.search(pattern, text):
                        is_definitely_not_algin = True
                        break
                
                # 如果不是明确的仓库标签，就假设是ALGIN标签
                is_algin_label = not is_definitely_not_algin
                
                if is_algin_label:
                    # 使用智能SKU识别和排序逻辑 - 大幅增强模式匹配
                    algin_sku_patterns = [
                        # 标准完整格式
                        r'\b(\d{3})-([A-Z]{2,4})-([A-Z0-9]+)\b',                    # 048-OPAC-5, 048-TL-W6KWD
                        r'\b(\d{3})-([A-Z]{2,4})—(\d+)-?([A-Z]*)\b',                # 048-OPAC—5, 014-HG—17061-B  
                        r'\b([A-Z0-9]{3,5})-([A-Z]{2})\b',                          # TFO1S-BK
                        r'\b([A-Z0-9]{3,5})—([A-Z]{2})\b',                          # TFO1S—BK
                        r'\b(\d{3})-([A-Z]{2})—([A-Z0-9]+)\b',                      # 048-TL—W6KWD
                        
                        # 014-HG系列格式
                        r'\b(014)-([A-Z]{2})-(\d{5})-([A-Z]+)\b',                   # 014-HG-17061-A
                        r'\b(014)-([A-Z]{2})-(\d{5})-([A-Z]{2,3})\b',               # 014-HG-17061-BRO
                        r'\b(014)-([A-Z]{2})-(\d{5})\b',                            # 014-HG-41023
                        
                        # 050系列格式
                        r'\b(050)-([A-Z]{2,3})-(\d{2,5})-?([A-Z]*)\b',              # 050-HA-50028, 050-LMT-23-GY
                        
                        # 060系列格式
                        r'\b(060)-([A-Z]{3})-(\d{2,3}[A-Z]*)-([A-Z]{2,3})\b',       # 060-ROT-11L-WH, 060-ROT-15V2-DG
                        
                        # 处理截断和空格问题的模式
                        r'(\d{3})\s*-\s*([A-Z]{2,4})\s*[-—]\s*([A-Z0-9]+)',        # 带空格的格式: "048 -TL-W..."
                        r'(\d{3})\s*-\s*([A-Z]{2,4})\s*[-—]\s*([A-Z0-9]*)',        # 可能截断的格式
                        r'([A-Z0-9]{3,5})\s*[-—]\s*([A-Z]{2})',                     # TF01S —BK 格式
                        
                        # 非常宽松的模式（处理严重OCR错误）
                        r'(\d{3})\s*[-—]?\s*([A-Z]{2,4})',                          # 最基本的数字-字母格式
                        r'([A-Z0-9]{4,6})\s*[-—]\s*([A-Z]{1,3})',                   # 字母数字-字母格式
                        
                        # 通用灵活格式（最后匹配）
                        r'\b(\d{3})-([A-Z]{2,4})-([A-Z0-9-]+)\b',                   # 通用数字-字母-字母数字格式
                        r'\b([A-Z0-9]{3,6})-([A-Z0-9]{2,6})\b',                     # 通用字母数字-字母数字格式
                    ]
                    
                    sku_found = False
                    found_skus = []
                    
                    # 查找完整SKU格式
                    for pattern in algin_sku_patterns:
                        matches = re.findall(pattern, text.upper())
                        if matches:
                            for match in matches:
                                if isinstance(match, tuple):
                                    # 过滤掉空字符串，然后重新组合
                                    non_empty_parts = [part for part in match if part]
                                    potential_sku = '-'.join(non_empty_parts)
                                else:
                                    potential_sku = match
                                
                                # 更严格的SKU验证 - 增强版
                                if (len(potential_sku) >= 5 and 
                                    not re.match(r'^\d{4}$', potential_sku) and
                                    not potential_sku.startswith('AGD') and
                                    # 确保包含至少一个字母和一个数字
                                    re.search(r'[A-Z]', potential_sku) and
                                    re.search(r'\d', potential_sku) and
                                    # 排除明显的错误模式
                                    not re.match(r'^\d{3}-[A-Z]{2,4}$', potential_sku) and  # 排除时间戳格式
                                    not potential_sku.startswith(('101-', '102-', '103-', '104-', '105-')) and  # 排除页面编号
                                    not re.search(r'(AOI|AATT|AI0)', potential_sku)):  # 排除时间标记
                                    found_skus.append(potential_sku)
                    
                    # 选择最佳SKU - 增强匹配逻辑
                    if found_skus:
                        # 首先尝试与Excel SKU列表精确匹配
                        matched_sku = None
                        best_match_score = 0
                        
                        for potential_sku in found_skus:
                            for excel_sku in algin_sku_order:
                                if is_sku_match(potential_sku, excel_sku):
                                    matched_sku = excel_sku  # 使用Excel中的标准格式
                                    best_match_score = 1.0
                                    break
                            if matched_sku:
                                break
                        
                        # 如果没有精确匹配，尝试部分匹配和智能推断
                        if not matched_sku and found_skus:
                            # 尝试部分匹配Excel SKU
                            for potential_sku in found_skus:
                                best_partial_match = None
                                best_match_score = 0
                                
                                for excel_sku in algin_sku_order:
                                    # 计算相似度分数
                                    similarity = 0
                                    
                                    # 前缀匹配（最重要）
                                    if potential_sku.startswith('048') and excel_sku.startswith('048'):
                                        similarity += 50
                                        if 'OPAC' in potential_sku and 'OPAC' in excel_sku:
                                            similarity += 30
                                        elif 'TL' in potential_sku and 'TL' in excel_sku:
                                            similarity += 30
                                    elif potential_sku.startswith('TF') and excel_sku.startswith('TF'):
                                        similarity += 50
                                    elif potential_sku.startswith('060') and excel_sku.startswith('060'):
                                        similarity += 50
                                    elif potential_sku.startswith('014') and excel_sku.startswith('014'):
                                        similarity += 50
                                    elif potential_sku.startswith('050') and excel_sku.startswith('050'):
                                        similarity += 50
                                    
                                    # 关键词匹配
                                    if 'OPAC' in potential_sku and 'OPAC' in excel_sku:
                                        similarity += 20
                                    if 'ROT' in potential_sku and 'ROT' in excel_sku:
                                        similarity += 20
                                    if 'HG' in potential_sku and 'HG' in excel_sku:
                                        similarity += 20
                                    
                                    if similarity > best_match_score:
                                        best_match_score = similarity
                                        best_partial_match = excel_sku
                                
                                if best_partial_match and best_match_score >= 50:
                                    matched_sku = best_partial_match
                                    break
                            
                            # 如果仍然没有匹配，选择最可能的SKU
                            if not matched_sku:
                                def sku_priority(sku):
                                    score = 0
                                    # 优先选择包含已知SKU模式的
                                    if re.match(r'048-(OPAC|TL)', sku):
                                        score += 100
                                    elif re.match(r'TFO1S', sku):
                                        score += 100
                                    elif re.match(r'060-ROT', sku):
                                        score += 100
                                    elif re.match(r'014-HG', sku):
                                        score += 100
                                    elif re.match(r'050-(HA|LMT)', sku):
                                        score += 100
                                    
                                    # 长度奖励
                                    score += len(sku)
                                    
                                    # 分隔符奖励
                                    if '-' in sku or '—' in sku:
                                        score += 10
                                    
                                    return -score
                                
                                found_skus.sort(key=sku_priority)
                                matched_sku = found_skus[0]
                        
                        groups["algin_sorted"].append((idx, matched_sku, text[:200]))
                        print(f"🔗 页面{idx+1} 匹配成功 → Excel='{matched_sku}'")
                        sku_found = True
                    
                    if not sku_found:
                        groups["algin_unscanned"].append((idx, "[ALGIN Label - 未扫描出来的label]", text[:200]))
                    continue
                
            # Look for 915 warehouse pattern
            m_915 = re.search(r"\b([A-Z]{2})-(\d{3})-([A-Z0-9]+)\b", text)
            if m_915:
                prefix, num, suffix = m_915.group(1), int(m_915.group(2)), m_915.group(3)
                if prefix in WAREHOUSE_PREFIXES["915"]:
                    groups["915"].append((idx, prefix, num, suffix))
                else:
                    groups["unknown"].append((idx, text[:100]))
                continue
                
            # Look for other warehouse patterns
            m_other = re.search(r"\b([A-Z]{2})-([A-Z]{2})-(\d{2,3})\b", text)
            if m_other:
                prefix, row, num = m_other.group(1), m_other.group(2), int(m_other.group(3))
                if prefix in WAREHOUSE_PREFIXES["8090"]:
                    groups["8090"].append((idx, prefix, row, num))
                elif prefix in WAREHOUSE_PREFIXES["60"]:
                    groups["60"].append((idx, prefix, row, num))
                else:
                    groups["unknown"].append((idx, text[:100]))
                continue
                
            # If no patterns found, add to unknown
            groups["unknown"].append((idx, text[:100]))
    
    # 显示最终处理进度
    print(f"📊 处理完成: {processed_pages}/{total_pages} (100.0%)")
    
    # Sort each warehouse group
    for warehouse in ["915", "8090", "60"]:
        groups[warehouse].sort(key=get_warehouse_sort_key)
    
    # Sort ALGIN labels by Excel SKU order
    def get_algin_sort_key(item):
        if len(item) >= 2:
            sku_string = item[1] if len(item) > 1 else ""
            
            # 如果是placeholder，放在最后
            if "[ALGIN Label" in str(sku_string):
                return (999, 999)
            
            # 在Excel SKU列表中查找位置
            if algin_sku_order:
                # 首先尝试精确匹配（对于已经匹配过的SKU）
                if sku_string in algin_sku_order:
                    return (0, algin_sku_order.index(sku_string))
                
                # 如果不是精确匹配，再尝试模糊匹配
                for i, excel_sku in enumerate(algin_sku_order):
                    if is_sku_match(sku_string, excel_sku):
                        return (0, i)
                
                # 在Excel中没找到，但是有SKU，放在Excel SKU后面
                return (1, sku_string)
            else:
                # 没有Excel文件，使用智能排序
                return (0,) + extract_sku_sort_key(sku_string)
        
        return (999, 999)
    
    if mode == "algin":
        groups["algin_sorted"].sort(key=get_algin_sort_key)
        print(f"\n📋 ALGIN排序结果预览:")
        
        # 统计每种SKU的数量
        sku_counts = {}
        for item in groups["algin_sorted"]:
            sku = item[1] if len(item) > 1 else "未知"
            sku_counts[sku] = sku_counts.get(sku, 0) + 1
        
        # 显示SKU统计
        print(f"📊 SKU分布统计:")
        for sku, count in sorted(sku_counts.items()):
            excel_index = algin_sku_order.index(sku) if sku in algin_sku_order else -1
            print(f"   {sku}: {count}页 (Excel第{excel_index+1}位)")
        
        # 显示前15个排序结果
        print(f"\n📋 排序结果前15个:")
        for i, item in enumerate(groups["algin_sorted"][:15]):
            sku = item[1] if len(item) > 1 else "未知"
            page_num = item[0] + 1
            excel_index = algin_sku_order.index(sku) if sku in algin_sku_order else -1
            print(f"   {i+1:2d}. 页面{page_num:3d} → {sku} (Excel第{excel_index+1}位)")
        if len(groups["algin_sorted"]) > 15:
            print(f"   ... 还有 {len(groups['algin_sorted']) - 15} 个SKU")
    
    # 显示处理统计
    print(f"\n📊 处理完成统计:")
    print(f"   总页数: {total_pages}")
    if mode == "algin":
        print(f"   ALGIN已排序: {len(groups['algin_sorted'])}")
        print(f"   ALGIN未扫描: {len(groups['algin_unscanned'])}")
        print(f"   ALGIN汇总页: {len(groups['algin_summary'])}")
    print(f"   915仓库: {len(groups['915'])}")
    print(f"   8090仓库: {len(groups['8090'])}")
    print(f"   60仓库: {len(groups['60'])}")
    print(f"   未知类型: {len(groups['unknown'])}")
    print(f"   空白页: {len(groups['blank'])}")
    
    outputs = []
    os.makedirs(output_dir, exist_ok=True)
    
    # Process groups in order based on mode
    if mode == "algin":
        # ALGIN模式: 处理ALGIN相关页面
        processing_order = ["algin_combined", "915", "8090", "60", "unknown", "blank"]
    else:
        # 仓库模式: 只处理仓库相关页面
        processing_order = ["915", "8090", "60", "unknown", "blank"]
    
    for warehouse in processing_order:
        if warehouse == "algin_combined":
            # 对于ALGIN排序，处理所有ALGIN相关的页面
            algin_sorted_pages = groups["algin_sorted"]
            algin_unsorted_pages = groups["algin_unscanned"]
            algin_summary_pages = groups["algin_summary"]
            
            # 分离有SKU和无SKU的ALGIN页面
            algin_with_sku = []
            algin_without_sku = []
            
            for item in algin_sorted_pages:
                sku_string = item[1] if len(item) > 1 else ""
                if "[ALGIN Label" in str(sku_string):
                    algin_without_sku.append(item)
                else:
                    algin_with_sku.append(item)
            
            # 按排序顺序组合：有SKU的ALGIN页面 + 汇总页面
            all_pages = algin_with_sku.copy()  # 使用copy确保不影响原始列表
            
            # 将汇总页面添加到最后（按原始页面顺序）
            algin_summary_pages.sort(key=lambda x: x[0])  # 按页面索引排序
            summary_pages_formatted = [(item[0], "汇总页面", item[2]) for item in algin_summary_pages]
            all_pages.extend(summary_pages_formatted)
            
            if not all_pages:
                print(f"⚠️  警告: 没有找到有SKU的页面，将输出所有ALGIN页面")
                all_pages = algin_sorted_pages[:150] if len(algin_sorted_pages) > 150 else algin_sorted_pages
                if not all_pages:
                    print(f"❌ 错误: 没有找到任何ALGIN页面！")
                    continue
                
            writer = PdfWriter()
            for item in all_pages:
                page_idx = item[0]
                writer.add_page(reader.pages[page_idx])
            
            output_name = "ALGIN_Label_已排序.pdf"
            output_path = os.path.join(output_dir, output_name)
            with open(output_path, "wb") as f:
                writer.write(f)
            outputs.append(output_path)
            print(f"✅ 生成文件: {output_name} ({len(all_pages)} 页)")
            print(f"   其中: {len(algin_with_sku)} 个SKU标签 + {len(algin_summary_pages)} 个汇总页面")
            
            # 验证数字：总页数应该等于各部分之和
            expected_total = len(algin_with_sku) + len(algin_summary_pages)
            if len(all_pages) != expected_total:
                print(f"⚠️  页面计数不一致: 输出{len(all_pages)}页 vs 预期{expected_total}页")
            
            # 检查是否有未扫描页面被忽略
            total_algin_pages = len(groups["algin_sorted"]) + len(groups["algin_unscanned"]) + len(groups["algin_summary"])
            if total_algin_pages != len(all_pages):
                print(f"📊 未包含的页面: {total_algin_pages - len(all_pages)} 页 (可能是未扫描的标签页面)")
            continue
            
        pages = groups[warehouse]
        if not pages:
            print(f"⚠️  {warehouse} 组为空，跳过")
            continue
            
        writer = PdfWriter()
        for item in pages:
            page_idx = item[0]
            writer.add_page(reader.pages[page_idx])
        
        # Determine output filename
        if warehouse == "unknown":
            # 检查是否包含大量ALGIN标签
            algin_count = 0
            for item in pages:
                page_content = item[1] if len(item) > 1 else ""
                if any(keyword in str(page_content).upper() for keyword in ['ALN', 'ALGIN', 'ALIGN']):
                    algin_count += 1
            
            if algin_count > len(pages) * 0.5:  # 如果超过50%的页面包含ALGIN标签
                output_name = "ALGIN标签页面_请使用ALGIN排序功能.pdf"
                print(f"🔍 检测到 {algin_count}/{len(pages)} 页包含ALGIN标签")
                print(f"💡 建议：请使用'ALGIN客户的Label排序'功能处理此文件")
            else:
                output_name = "未找到仓库.pdf"
        elif warehouse == "blank":
            output_name = "空白页.pdf"
        else:
            output_name = f"{warehouse}_Sorted.pdf"
            
        output_path = os.path.join(output_dir, output_name)
        with open(output_path, "wb") as f:
            writer.write(f)
        outputs.append(output_path)
        print(f"✅ 生成文件: {output_name} ({len(pages)} 页)")
    
    return outputs