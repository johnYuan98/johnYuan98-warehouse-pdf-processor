import re

def is_sku_match_improved(ocr_sku, excel_sku):
    """
    增强的SKU匹配逻辑，专门处理ALGIN相关的OCR错误
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
    
    # 2.5. 特殊处理：常见的OPAC/TL缺失前缀问题
    if not ocr_norm.startswith('048-') and excel_norm.startswith('048-'):
        # 尝试给OCR结果添加048-前缀
        if excel_norm.startswith('048-OPAC-') and 'OPAC' in ocr_norm:
            # 处理OPAC-6, OPAC-6H等情况
            opac_part = re.search(r'OPAC[-]?(\d+[A-Z]?)', ocr_norm)
            if opac_part:
                prefixed_ocr = f"048-OPAC-{opac_part.group(1)}"
                if prefixed_ocr == excel_norm:
                    return True
        elif excel_norm.startswith('048-TL-') and ('TL' in ocr_norm or 'W' in ocr_norm):
            # 处理TL系列，如048-TL-W6KWD
            w_part = re.search(r'(W\d+[A-Z]+)', ocr_norm)
            if w_part:
                prefixed_ocr = f"048-TL-{w_part.group(1)}"
                if prefixed_ocr == excel_norm:
                    return True
    
    # 3. 处理OCR常见错误 - ALGIN专用增强版本
    correction_pairs = [
        # 数字混淆
        ('9', '6'), ('6', '9'),  # 6和9混淆 - OPAC-9应该是OPAC-6
        ('5', '6'), ('6', '5'),  # 5和6混淆
        ('0', 'O'), ('O', '0'),  # 0和O混淆
        ('1', 'I'), ('I', '1'),  # 1和I混淆
        ('5', 'S'), ('S', '5'),  # 5和S混淆
        ('8', 'B'), ('B', '8'),  # 8和B混淆
        ('G', '6'), ('6', 'G'),  # G和6混淆
        ('D', 'B'), ('B', 'D'),  # D和B混淆
        ('Q', 'O'), ('O', 'Q'),  # Q和O混淆
        ('Z', '2'), ('2', 'Z'),  # Z和2混淆
        # 特殊的ALGIN OCR错误
        ('9H', '6H'), ('9B', '6'),  # OPAC-9H -> OPAC-6H, OPAC-9B -> OPAC-6
        ('5KWDS', '8KWD'),  # W5KWDS -> W8KWD
        ('9HB', '6H'),  # OPAC-9HB -> OPAC-6H
    ]
    
    # 尝试不同的纠错组合
    for wrong, correct in correction_pairs:
        ocr_corrected = ocr_norm.replace(wrong, correct)
        if ocr_corrected == excel_norm:
            return True
    
    # 4. 核心部分匹配（去除特殊字符）
    def extract_core_sku(sku):
        parts = re.findall(r'[A-Z0-9]+', sku)
        return ''.join(parts)
    
    ocr_core = extract_core_sku(ocr_norm)
    excel_core = extract_core_sku(excel_norm)
    
    if ocr_core == excel_core:
        return True
    
    # 5. 特殊处理：OPAC系列的精确匹配 - 修复版本
    if 'OPAC' in ocr_norm and 'OPAC' in excel_norm:
        # 提取OPAC后的数字和字母
        ocr_opac = re.search(r'OPAC[-]?(\d+)([A-Z]*)', ocr_norm)
        excel_opac = re.search(r'OPAC[-]?(\d+)([A-Z]*)', excel_norm)
        
        if ocr_opac and excel_opac:
            ocr_num = ocr_opac.group(1)
            ocr_suffix = ocr_opac.group(2)
            excel_num = excel_opac.group(1)
            excel_suffix = excel_opac.group(2)
            
            # 先检查完全匹配
            if ocr_num == excel_num and ocr_suffix == excel_suffix:
                return True
            
            # 只在特定情况下进行OCR纠错
            # 1. 9被误识别为6的情况（常见OCR错误）
            if ocr_num == '9' and excel_num == '6' and ocr_suffix == excel_suffix:
                return True
            # 2. 6被误识别为9的情况 
            if ocr_num == '6' and excel_num == '9' and ocr_suffix == excel_suffix:
                return True
            # 3. H后缀的特殊处理（HB可能是6H的OCR错误）
            if ocr_num == excel_num and ocr_suffix in ['HB', 'H6'] and excel_suffix == 'H':
                return True
            # 4. B可能是6的OCR错误，但只有在没有H后缀时
            if ocr_num == excel_num and ocr_suffix == 'B' and excel_suffix == '' and excel_num == '6':
                return True
    
    # 6. TFO1S系列特殊处理
    if 'TFO1S' in ocr_norm and 'TFO1S' in excel_norm:
        return True
    
    # 7. 014-HG系列的处理
    if 'HG' in ocr_norm and 'HG' in excel_norm and '014' in excel_norm:
        # 尝试提取HG后的数字部分
        ocr_hg = re.search(r'HG[-]?(\d{5})[-]?([A-Z]*)', ocr_norm)
        excel_hg = re.search(r'HG[-]?(\d{5})[-]?([A-Z]*)', excel_norm)
        
        if ocr_hg and excel_hg:
            if ocr_hg.group(1) == excel_hg.group(1):  # 数字部分匹配
                return True
    
    # 8. 前缀匹配（对于可能被截断的SKU）
    if len(ocr_norm) >= 8 and len(excel_norm) >= 8:
        if excel_norm.startswith(ocr_norm) or ocr_norm.startswith(excel_norm):
            # 确保长度差异合理
            if abs(len(ocr_norm) - len(excel_norm)) <= 3:
                return True
    
    return False