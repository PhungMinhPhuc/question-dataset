import os
import re
import copy
import random
import csv
import io
from typing import List, Dict, Any
import xml.etree.ElementTree as ET



def fix_soft_newlines(text: str) -> str:
    if not text: return text
    # Split by LaTeX/Math blocks to protect them
    pattern = r'(\$\$[\s\S]*?\$\$|\$[^\$]*?\$|\\\[[\s\S]*?\\\]|\\\(.*?\\\)|\\begin\{.*?\}[\s\S]*?\\end\{.*?\})'
    parts = re.split(pattern, text)
    for i in range(0, len(parts), 2):
        # Replace <br> and soft newlines with double newlines
        parts[i] = re.sub(r'<br\s*/?>', '\n\n', parts[i])
        # Replace \\ (double backslashes outside math) with double newlines
        parts[i] = parts[i].replace('\\\\', '\n\n')
        parts[i] = re.sub(r'(?<!\n)\n(?!\n)', '\n\n', parts[i])
    return "".join(parts)

def get_svg_native_width_inches(filepath: str, default_inches: float = 2.6) -> float:
    try:
        import xml.etree.ElementTree as ET
        import re
        tree = ET.parse(filepath)
        root = tree.getroot()
        w_str = root.attrib.get('width', '')
        if not w_str:
            vb_str = root.attrib.get('viewBox', '')
            if vb_str:
                parts = vb_str.split()
                if len(parts) >= 4:
                    w_str = parts[2]
        if w_str:
            m = re.search(r'([\d.]+)', w_str)
            if m:
                return float(m.group(1)) / 96.0
    except Exception:
        pass
    return default_inches

def shuffle_contest(questions: List[dict]) -> tuple[List[dict], dict]:
    # Returns (shuffled_questions, mapping)
    # Mapping: { old_q_id: new_position_index }
    
    # We group by type: mc, tf, sa, oe
    groups = {'mc': [], 'tf': [], 'sa': [], 'oe': [], 'st': []}
    
    # Find all top-level questions
    top_level = [q for q in questions if not q.get('parent_id')]
    children = {q['id']: [] for q in questions if q.get('question_type') == 'st'}
    for q in questions:
        if q.get('parent_id'):
            if q['parent_id'] in children:
                children[q['parent_id']].append(q)
                
    for q in top_level:
        if q.get('question_type') == 'st':
            ch_list = children.get(q['id'], [])
            if ch_list:
                eff_type = ch_list[0].get('question_type', 'st')
                if eff_type in groups:
                    groups[eff_type].append(q)
                else:
                    groups['st'].append(q)
            else:
                groups['st'].append(q)
        else:
            q_type = q.get('question_type')
            if q_type in groups:
                groups[q_type].append(q)
            else:
                groups['mc'].append(q)
        
    shuffled_questions = []
    
    # The order must be MC -> TF -> SA -> OE. (ST can contain these too, usually ST are kept together but we just append them where they belong or at the end).
    # For now, let's keep ST at the end or intermixed? Usually ST is separate. Let's append ST at the end.
    
    type_order = ['mc', 'tf', 'sa', 'oe', 'st']
    
    for t in type_order:
        group_qs = groups[t]
        # Shuffle top-level questions if they are shufflable
        # Wait, for simplicity let's shuffle all top level in the group
        random.shuffle(group_qs)
        
        for q in group_qs:
            new_q = copy.deepcopy(q)
            if new_q['question_type'] == 'mc' and new_q.get('is_shufflable', True):
                # Shuffle options
                opts = new_q.get('options', [])
                random.shuffle(opts)
                new_q['options'] = opts
            
            shuffled_questions.append(new_q)
            # if it's ST, append its children
            if new_q['id'] in children:
                ch_list = copy.deepcopy(children[new_q['id']])
                random.shuffle(ch_list)
                for ch in ch_list:
                    if ch['question_type'] == 'mc' and ch.get('is_shufflable', True):
                        opts = ch.get('options', [])
                        random.shuffle(opts)
                        ch['options'] = opts
                    shuffled_questions.append(ch)
                    
    # Generate Answer Key mapping for this shuffled version
    # Answer Key typically looks like: Q1: A, Q2: B...
    answer_key = {}
    q_counter = 1
    
    for q in shuffled_questions:
        if q['question_type'] == 'st': continue
        
        q_type = q['question_type']
        ans_str = ""
        
        if q_type == 'mc':
            for idx, opt in enumerate(q['options']):
                if opt.get('is_correct'):
                    ans_str = chr(65 + idx)
                    break
        elif q_type == 'tf':
            ans_str = ",".join("D" if opt.get('is_correct') else "S" for opt in q['options'])
        elif q_type == 'sa':
            ans_str = q['options'][0].get('content', '') if q['options'] else ''
            
        answer_key[q_counter] = ans_str
        q_counter += 1
        
    return shuffled_questions, answer_key

def generate_answer_key_excel(answer_keys: Dict[str, Dict[int, str]]) -> bytes:
    if not answer_keys: return b""
    import openpyxl
    from openpyxl.styles import Alignment
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Đáp Án"
    
    max_q = 0
    for k, v in answer_keys.items():
        if v: max_q = max(max_q, max(v.keys()))
        
    header = ["Câu/Mã đề"] + list(answer_keys.keys())
    ws.append(header)
    
    for i in range(1, max_q + 1):
        row = [str(i)]
        for code in answer_keys.keys():
            row.append(str(answer_keys[code].get(i, '')))
        ws.append(row)
        
    center_align = Alignment(horizontal='center', vertical='center')
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = center_align
            cell.number_format = '@'
            
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

