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

import platform
import shutil

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
import sys
tesseract_path = setup_tesseract()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"✅ Tesseract路径设置为: {tesseract_path}", flush=True)
    sys.stdout.flush()
else:
    print("⚠️ Tesseract未找到，OCR功能不可用，但应用仍可处理文本PDF", flush=True)
    sys.stdout.flush()
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

# 导入改进的SKU匹配函数
from improved_sku_match import is_sku_match_improved

def is_sku_match(ocr_sku, excel_sku):
    """使用改进的SKU匹配逻辑"""
    return is_sku_match_improved(ocr_sku, excel_sku)

def is_sku_match_old(ocr_sku, excel_sku):
    """
    改进的SKU匹配逻辑，处理OCR扫描结果与正确SKU列表的差异
    """
    # 标准化处理
    ocr_clean = ocr_sku.upper().strip()
    excel_clean = excel_sku.upper().strip()
    
    # 1. 完全匹配
    if ocr_clean == excel_clean:
        return True
    
    # 2. 标准化破折号后匹配
    def normalize_dashes(sku):
        return sku.replace('—', '-').replace('_', '-').replace(' ', '')
    
    ocr_norm = normalize_dashes(ocr_clean)
    excel_norm = normalize_dashes(excel_clean)
    
    if ocr_norm == excel_norm:
        return True
    
    # 3. 处理OCR常见错误 - 增强版本
    # 首先尝试多种常见的OCR错误纠正
    correction_pairs = [
        ('9', '6'), ('6', '9'),  # 6和9混淆
        ('0', 'O'), ('O', '0'),  # 0和O混淆
        ('1', 'I'), ('I', '1'),  # 1和I混淆
        ('5', 'S'), ('S', '5'),  # 5和S混淆
        ('8', 'B'), ('B', '8'),  # 8和B混淆
        ('G', '6'), ('6', 'G'),  # G和6混淆
        ('D', 'B'), ('B', 'D'),  # D和B混淆
        ('Q', 'O'), ('O', 'Q'),  # Q和O混淆
        ('Z', '2'), ('2', 'Z'),  # Z和2混淆
    ]
    
    # 尝试不同的纠错组合
    for wrong, correct in correction_pairs:
        ocr_corrected = ocr_norm.replace(wrong, correct)
        if ocr_corrected == excel_norm:
            return True
        
        # 也尝试多重替换
        ocr_multi = ocr_corrected
        for w2, c2 in correction_pairs:
            if w2 != wrong:  # 避免重复替换
                ocr_multi = ocr_multi.replace(w2, c2)
                if ocr_multi == excel_norm:
                    return True
    
    # 4. 核心部分匹配（去除特殊字符）
    def extract_core_sku(sku):
        import re
        parts = re.findall(r'[A-Z0-9]+', sku)
        return ''.join(parts)
    
    ocr_core = extract_core_sku(ocr_norm)
    excel_core = extract_core_sku(excel_norm)
    
    if ocr_core == excel_core:
        return True
    
    # 5. 前缀匹配（对于可能被截断的SKU）
    if len(ocr_norm) >= 8 and len(excel_norm) >= 8:
        if excel_norm.startswith(ocr_norm) or ocr_norm.startswith(excel_norm):
            # 确保长度差异合理
            if abs(len(ocr_norm) - len(excel_norm)) <= 3:
                return True
    
    # 6. 精确包含关系匹配
    if len(ocr_norm) >= 6 and len(excel_norm) >= 6:
        if ocr_norm in excel_norm or excel_norm in ocr_norm:
            # 确保不是意外的子串匹配
            if abs(len(ocr_norm) - len(excel_norm)) <= 2:
                return True
    
    # 7. 特殊处理：OPAC系列的常见OCR错误（增强版）
    if 'OPAC' in ocr_norm and 'OPAC' in excel_norm:
        # 提取完整的OPAC格式 - 支持更多变体
        ocr_opac_match = re.search(r'(048-?)?OPAC-?(\d+)([A-Z]*)', ocr_norm)
        excel_opac_match = re.search(r'(048-?)?OPAC-?(\d+)([A-Z]*)', excel_norm)
        
        if ocr_opac_match and excel_opac_match:
            ocr_num = ocr_opac_match.group(2)
            ocr_suffix = ocr_opac_match.group(3)
            excel_num = excel_opac_match.group(2)
            excel_suffix = excel_opac_match.group(3)
            
            # 数字纠错映射
            num_corrections = {
                '9': ['6', '5'],  # 9经常被误识别为6或5
                '6': ['9', '5'],  # 6经常被误识别为9或5
                '5': ['6', '9'],  # 5经常被误识别为6或9
            }
            
            # 检查数字匹配 - 只在数字完全相同时匹配，不要纠错
            num_matches = (ocr_num == excel_num)
            
            # 后缀匹配 - 只在完全相同时匹配，不要纠错
            suffix_matches = (ocr_suffix == excel_suffix)
            
            if num_matches and suffix_matches:
                print(f"🔧 OPAC纠错匹配: {ocr_sku} -> {excel_sku}")
                return True
    
    # 8. TFO1S系列的常见错误
    if ('TFO1S' in ocr_norm or 'TF01S' in ocr_norm) and 'TFO1S' in excel_norm:
        return True
    
    return False

def load_algin_sku_order(excel_path="uploads/ALGIN.xlsx"):
    """加载ALGIN SKU的正确排序顺序"""
    # 使用用户提供的完整正确SKU顺序（2025年7月15日更新）
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
    """判断是否为'未能扫出SKU的label'页面 - 更严格的判断逻辑"""
    if not text or not text.strip():
        return False
        
    text_upper = text.upper()
    
    # 1. 必须包含ALGIN相关标识
    has_algin = bool(re.search(r'(ALN|ALGIN|ALIGN)', text_upper))
    if not has_algin:
        return False
    
    # 2. 必须包含UPS信息（特殊格式的UPS标签编号）
    ups_pattern = r'UPS\d*L'  # UPS后跟数字和L，如UPS1L, UPS128L等
    ups_matches = re.findall(ups_pattern, text_upper)
    if len(ups_matches) < 1:  # 必须有至少1个特殊格式的UPS标签编号
        return False
    
    # 3. 包含FSO标识（表示是总结页面）
    has_fso = bool(re.search(r'FSO', text_upper))
    if not has_fso:
        return False
    
    # 4. 不应该包含明确的产品SKU
    detailed_sku_patterns = [
        r'\b\d{3}-[A-Z]{2,4}-[A-Z0-9]+\b',    # 048-OPAC-5, 048-TL-W6KWD等
        r'\b[A-Z0-9]{4,6}-[A-Z]{2}\b',        # TFO1S-BK等
        r'\b\d{3}-[A-Z]{2,4}—\d+\b',         # 048-OPAC—5
        r'\b[A-Z0-9]{3,5}—[A-Z]{2}\b',       # TFO1S—BK
    ]
    has_detailed_sku = any(re.search(pattern, text_upper) for pattern in detailed_sku_patterns)
    if has_detailed_sku:
        return False
    
    # 5. 必须同时满足以上条件才是总结页面
    return True

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
        groups = {"915": [], "8090": [], "60": [], "algin_sorted": [], "algin_unscanned": [], "unscanned_sku_labels": [], "unknown": [], "blank": []}
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
            
            # 每处理10页显示一次进度
            if processed_pages % 10 == 0:
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
                        # Convert page to image and run OCR with multiple configurations
                        page_image = page.to_image(resolution=150)  # 提高分辨率
                        # 尝试多个OCR配置
                        ocr_configs = [
                            '--psm 6 --oem 1 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-— ',
                            '--psm 4 --oem 1',  # 单列文本
                            '--psm 3 --oem 1',  # 自动检测
                            '--psm 1 --oem 1',  # 自动方向和脚本检测
                        ]
                        for config in ocr_configs:
                            try:
                                ocr_text = pytesseract.image_to_string(page_image.original, config=config)
                                if ocr_text.strip():
                                    text = ocr_text
                                    print(f"🔍 页面{idx+1} OCR成功(配置{config[:10]}): {text[:50]}...")
                                    break
                            except Exception as ocr_e:
                                print(f"❌ 页面{idx+1} OCR配置失败: {ocr_e}")
                                continue
                        if text.strip():
                            # OCR成功，继续处理
                            pass
                        else:
                            print(f"⚠️  页面{idx+1} 所有OCR配置均失败")
                            # 检查是否是未能扫出SKU的label
                            if is_unscanned_sku_label(ocr_text):
                                sort_key = extract_sort_key_for_unscanned(ocr_text)
                                groups["unscanned_sku_labels"].append((idx, sort_key, ocr_text[:100]))
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
            
            # First, check if this is an "未能扫出SKU的label" page (for ALGIN mode)
            if mode == "algin" and is_unscanned_sku_label(text):
                sort_key = extract_sort_key_for_unscanned(text)
                groups["unscanned_sku_labels"].append((idx, sort_key, text[:100]))
                print(f"📋 识别为总结页面: 页面{idx+1}")
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
                    # 先进行OCR文本清理和预处理
                    def clean_ocr_text(text):
                        """清理OCR文本中的常见错误"""
                        cleaned = text.upper()
                        
                        # OCR常见错误纠正
                        replacements = {
                            '048—OPAC-': '048-OPAC-',
                            '048—OPAC—': '048-OPAC-',
                            '048-—OPAC-': '048-OPAC-',
                            '048—OPA': '048-OPAC-',
                            '048-—OP': '048-OPAC-',
                            '048—TL—': '048-TL-',
                            '048-—TL—': '048-TL-',
                            '014—HG—': '014-HG-',
                            '014-—HG—': '014-HG-',
                            'OPAC-9': 'OPAC-6',  # OCR常把6识别为9
                            'OPAC-9B': 'OPAC-6',
                            'OPAC-9H': 'OPAC-6H',
                            'OPAC-9HB': 'OPAC-6H',
                            'TFO1S—': 'TFO1S-',
                            'W5KWDS': 'W8KWD',  # 修正常见OCR错误
                        }
                        
                        for wrong, correct in replacements.items():
                            cleaned = cleaned.replace(wrong, correct)
                        
                        return cleaned
                    
                    cleaned_text = clean_ocr_text(text)
                    print(f"🧹 页面{idx+1} 清理后文本: {cleaned_text[:100]}...")
                    
                    # 使用智能SKU识别和排序逻辑 - 扩展模式匹配
                    algin_sku_patterns = [
                        # 048系列OPAC和TL格式 - 最高优先级
                        r'\b(048)-(OPAC)-(\d+[A-Z]?)\b',                           # 048-OPAC-5, 048-OPAC-6H
                        r'\b(048)-(TL)-(W\d+[A-Z]+)\b',                           # 048-TL-W6KWD, 048-TL-W10KWD
                        
                        # TFO1S系列
                        r'\b(TFO1S)-(BK)\b',                                       # TFO1S-BK
                        
                        # 014-HG系列格式
                        r'\b(014)-(HG)-(\d{5})-(\d[A-Z]+)\b',                     # 014-HG-17061-A
                        r'\b(014)-(HG)-(\d{5})-(\d[A-Z]{2,3})\b',                 # 014-HG-17061-BRO
                        r'\b(014)-(HG)-(\d{5})\b',                                # 014-HG-41023
                        
                        # 050系列格式
                        r'\b(050)-(HA|LMT)-(\d{2,5})-?([A-Z]*)\b',                # 050-HA-50028, 050-LMT-23-GY
                        
                        # 060系列格式
                        r'\b(060)-(ROT)-(\d{2,3}[A-Z]*)-(\d[A-Z]{2,3})\b',        # 060-ROT-11L-WH, 060-ROT-15V2-DG
                        
                        # 备用模式 - 较低优先级
                        r'\b(\d{3})-(\d[A-Z]{2,4})-(\d[A-Z0-9]+)\b',              # 通用数字-字母-字母数字格式
                        r'\b([A-Z0-9]{3,6})-(\d[A-Z0-9]{2,6})\b',                 # 通用字母数字-字母数字格式
                    ]
                    
                    sku_found = False
                    found_skus = []
                    
                    # 查找完整SKU格式 - 在清理后的文本中搜索
                    for pattern in algin_sku_patterns:
                        matches = re.findall(pattern, cleaned_text)
                        if matches:
                            for match in matches:
                                if isinstance(match, tuple):
                                    # 过滤掉空字符串，然后重新组合
                                    non_empty_parts = [part for part in match if part]
                                    potential_sku = '-'.join(non_empty_parts)
                                else:
                                    potential_sku = match
                                
                                # 更严格的SKU验证
                                if (len(potential_sku) >= 5 and 
                                    not re.match(r'^\d{4}$', potential_sku) and
                                    not potential_sku.startswith('AGD') and
                                    # 确保包含至少一个字母和一个数字
                                    re.search(r'[A-Z]', potential_sku) and
                                    re.search(r'\d', potential_sku) and
                                    # 过滤掉明显错误的SKU
                                    not potential_sku.startswith('OPAC-') and  # 应该是048-OPAC-
                                    not potential_sku.endswith('HB')):         # 避免6HB这样的错误
                                    found_skus.append(potential_sku)
                                    print(f"✅ 页面{idx+1} 识别SKU: {potential_sku}")
                    
                    # 如果没找到标准格式，尝试部分识别和重建SKU
                    if not found_skus:
                        # 尝试识别部分SKU信息并重建
                        if 'OPAC' in cleaned_text and '048' in cleaned_text:
                            # 尝试重建048-OPAC格式 - 改进版本
                            opac_patterns = [
                                r'048.{0,3}OPAC.{0,3}(\d+[A-Z]?)',  # 048-OPAC-6H
                                r'OPAC.{0,3}(\d+[A-Z]?)',           # OPAC-6H
                            ]
                            for pattern in opac_patterns:
                                matches = re.findall(pattern, cleaned_text)
                                for num in matches:
                                    # 修正常见的OCR错误
                                    if num.endswith('B'):  # 6B -> 6
                                        num = num[:-1]
                                    elif num.endswith('9'):  # 可能是6被识别成9
                                        num = num[:-1] + '6'
                                    
                                    rebuilt_sku = f"048-OPAC-{num}"
                                    found_skus.append(rebuilt_sku)
                                    print(f"🔧 页面{idx+1} 重建SKU: {rebuilt_sku}")
                                    break
                        
                        elif 'TL' in cleaned_text and '048' in cleaned_text and 'W' in cleaned_text:
                            # 尝试重建048-TL格式
                            tl_patterns = re.findall(r'(W\d+[A-Z]+)', cleaned_text)
                            for pattern in tl_patterns:
                                if len(pattern) >= 4:  # W6KWD, W10KWD等
                                    rebuilt_sku = f"048-TL-{pattern}"
                                    found_skus.append(rebuilt_sku)
                                    print(f"🔧 页面{idx+1} 重建SKU: {rebuilt_sku}")
                        
                        elif 'TFO1S' in cleaned_text and 'BK' in cleaned_text:
                            # TFO1S-BK格式
                            found_skus.append("TFO1S-BK")
                            print(f"🔧 页面{idx+1} 重建SKU: TFO1S-BK")
                        
                        elif '014' in cleaned_text and 'HG' in cleaned_text:
                            # 尝试重建014-HG格式 - 改进版本
                            hg_patterns = [
                                r'014.{0,3}HG.{0,3}(\d{5}).{0,3}([A-Z]{2,3})',  # 014-HG-41896-WH
                                r'HG.{0,3}(\d{5}).{0,3}([A-Z]{2,3})',           # HG-41896-WH
                                r'(\d{5}).{0,3}([A-Z]{2,3})',                   # 41896-WH
                            ]
                            for pattern in hg_patterns:
                                matches = re.findall(pattern, cleaned_text)
                                for num, suffix in matches:
                                    if len(num) == 5:  # 确保是5位数字
                                        rebuilt_sku = f"014-HG-{num}-{suffix}"
                                        found_skus.append(rebuilt_sku)
                                        print(f"🔧 页面{idx+1} 重建SKU: {rebuilt_sku}")
                                        break
                    
                    # 选择最佳SKU
                    if found_skus:
                        def sku_priority(sku):
                            has_separator = '-' in sku or '—' in sku
                            length = len(sku)
                            return (not has_separator, -length)
                        
                        found_skus.sort(key=sku_priority)
                        best_sku = found_skus[0]
                        
                        groups["algin_sorted"].append((idx, best_sku, text[:200]))
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
    
    # 验证所有页面都被处理了
    if len(all_processed_pages) != total_pages:
        print(f"⚠️  警告: 处理的页面数({len(all_processed_pages)})与总页数({total_pages})不匹配")
        missing_pages = set(range(total_pages)) - all_processed_pages
        if missing_pages:
            print(f"❌ 缺失页面: {sorted(missing_pages)}")
    else:
        print(f"✅ 所有 {total_pages} 页都已正确处理")
    
    # Sort each warehouse group
    for warehouse in ["915", "8090", "60"]:
        groups[warehouse].sort(key=get_warehouse_sort_key)
    
    # Sort ALGIN labels by Excel SKU order - 修复版本
    def get_algin_sort_key(item):
        if len(item) >= 2:
            sku_string = item[1] if len(item) > 1 else ""
            
            # 如果是placeholder，放在最后
            if "[ALGIN Label" in str(sku_string):
                return (999, 999)
            
            # 在Excel SKU列表中查找位置
            if algin_sku_order:
                for i, excel_sku in enumerate(algin_sku_order):
                    if is_sku_match(sku_string, excel_sku):
                        return (0, i, sku_string)
                
                # 在Excel中没找到，但是有SKU，放在Excel SKU后面
                return (1, sku_string)
            else:
                # 没有Excel文件，使用智能排序
                return (0,) + extract_sku_sort_key(sku_string)
        
        return (999, 999)
    
    if mode == "algin":
        # 调试：显示所有识别到的SKU
        print(f"🔍 调试 - 识别到的SKU列表:")
        for i, item in enumerate(groups["algin_sorted"]):
            sku = item[1] if len(item) > 1 else "未知"
            print(f"   {i+1}. {sku}")
        
        groups["algin_sorted"].sort(key=get_algin_sort_key)
        
        # 调试：显示排序后的SKU分组
        print(f"🔍 调试 - 排序后的SKU分组列表:")
        current_sku = None
        group_count = 0
        for i, item in enumerate(groups["algin_sorted"]):
            sku = item[1] if len(item) > 1 else "未知"
            page_num = item[0] if len(item) > 0 else "未知"
            sort_key = get_algin_sort_key(item)
            
            # 检查是否是新的SKU组
            if current_sku != sku:
                current_sku = sku
                group_count += 1
                print(f"   组{group_count}: {sku}")
            
            print(f"      页面{page_num} (排序键: {sort_key})")
    
    # 显示处理统计
    print(f"\n📊 处理完成统计:")
    print(f"   总页数: {total_pages}")
    if mode == "algin":
        print(f"   ALGIN已排序: {len(groups['algin_sorted'])}")
        print(f"   ALGIN未扫描: {len(groups['algin_unscanned'])}")
        print(f"   未扫描SKU标签: {len(groups['unscanned_sku_labels'])}")
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
            # 对于ALGIN排序，只处理ALGIN相关的页面
            algin_sorted_pages = groups["algin_sorted"]
            algin_unsorted_pages = groups["algin_unscanned"]
            
            # 分离有SKU和无SKU的ALGIN页面
            algin_with_sku = []
            algin_without_sku = []
            
            for item in algin_sorted_pages:
                sku_string = item[1] if len(item) > 1 else ""
                if "[ALGIN Label" in str(sku_string):
                    algin_without_sku.append(item)
                else:
                    algin_with_sku.append(item)
            
            # 输出所有ALGIN页面（有SKU的优先排序，然后是无SKU、未扫描和总结页面）
            unscanned_summary_pages = groups.get("unscanned_sku_labels", [])
            all_pages = algin_with_sku + algin_without_sku + algin_unsorted_pages + unscanned_summary_pages
            
            if not all_pages:
                print(f"⚠️  警告: 没有找到有SKU的页面，将输出所有ALGIN页面")
                all_pages = algin_sorted_pages[:150] if len(algin_sorted_pages) > 150 else algin_sorted_pages
                if not all_pages:
                    print(f"❌ 错误: 没有找到任何ALGIN页面！")
                    continue
            
            print(f"📊 ALGIN页面统计: 有效SKU页面({len(algin_with_sku)}) / 总页数({len(algin_with_sku) + len(algin_without_sku) + len(algin_unsorted_pages) + len(unscanned_summary_pages)})")
            print(f"🔍 过滤掉: 无SKU({len(algin_without_sku)}) + 未扫描({len(algin_unsorted_pages)}) + 总结({len(unscanned_summary_pages)}) 页")
                
            # 输出所有ALGIN页面（有SKU的优先排序，然后是无SKU、未扫描和总结页面）
            writer = PdfWriter()
            print(f"🔍 最终输出页面顺序:")
            for i, item in enumerate(all_pages):
                page_idx = item[0]
                sku_string = item[1] if len(item) > 1 else "未知"
                print(f"   第{i+1}页输出: 原页面{item[0]+1} -> SKU: {sku_string}")
                writer.add_page(reader.pages[page_idx])
            
            output_name = "ALGIN_Label_已排序.pdf"
            output_path = os.path.join(output_dir, output_name)
            with open(output_path, "wb") as f:
                writer.write(f)
            outputs.append(output_path)
            print(f"✅ 生成文件: {output_name} ({len(all_pages)} 页)")
            print(f"📁 文件完整路径: {output_path}", flush=True)
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