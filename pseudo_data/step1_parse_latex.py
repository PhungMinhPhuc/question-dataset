import os
import re
import json
import sys
import uuid

# Thêm đường dẫn tới backend engine để sử dụng parser chuẩn của dự án
sys.path.append(r"E:\Downloads\database_question_dataset\backend\src\engine")
from logic_manager import dispatch_block
from process_stimulus import process_stimulus_block
from get_bracket_content import get_bracket_content

TEX_FOLDER = r"E:\Downloads\database_question_dataset\pseudo_data"
OUTPUT_JSON = r"pseudo_data\questions.json"

def clean_latex_comments(content):
    # Chỉ xóa comment % bên trong khối (không phải \%)
    return re.sub(r'(?<!\\)(?<!\d)(?<!\\\\)%[^\n]*', '', content)

def parse_latex_files(folder_path):
    print(f"[*] Đang quét thư mục {folder_path}...")
    final_db_ready_data = []
    
    # Fake metadata for parsing
    teacher_id = 1
    grade_int = 12
    chapter = "Chapter 1"
    lesson = "Lesson 1"
    complexity = 1
    target_img_dir = "./storage"
    os.makedirs(target_img_dir, exist_ok=True)
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".tex"):
                file_path = os.path.join(root, file)
                
                content = None
                for enc in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            content = f.read()
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                if not content: continue
                
                doc_match = re.search(r'\\begin\{document\}(.*?)(?:\\end\{document\}|$)', content, re.DOTALL)
                if doc_match:
                    content = doc_match.group(1)
                    
                blocks = content.split(r'\begin{ex}')
                for i in range(1, len(blocks)):
                    block = blocks[i]
                    prefix_block = blocks[i-1]
                    
                    # 1. Extract % Môn
                    subject = "Vật Lí" # Default
                    lines = prefix_block.split('\n')
                    for line in reversed(lines):
                        line = line.strip()
                        if not line: continue
                        if not line.startswith('%'): break
                        match = re.search(r'%\s*môn\s*[:\-]?\s*(.*)', line, re.IGNORECASE)
                        if match:
                            subject = match.group(1).strip()
                            break
                            
                    # 2. Extract till \end{ex}
                    end_idx = block.find(r'\end{ex}')
                    if end_idx != -1:
                        block = block[:end_idx]
                        
                    # 3. Clean comments in block
                    block = clean_latex_comments(block)
                    metadata = {'chapter': chapter, 'lesson': lesson, 'complexity': complexity}
                    
                    # 4. Use logic_manager's dispatch logic!
                    sochc_match = re.search(r'\\sochc\s*\{(\d+)\}\s*\{', block)
                    temp_blocks_to_process = []
                    
                    if sochc_match:
                        # STIMULUS
                        parent_uuid = str(uuid.uuid4())
                        stim_content, stim_end = get_bracket_content(block, sochc_match.end() - 1)
                        stim_data = process_stimulus_block(stim_content, teacher_id, parent_uuid, subject, grade_int, None, chapter, lesson, complexity, False, file_path, target_img_dir)
                        temp_blocks_to_process.append((stim_data, []))
                        
                        chc_blocks = re.findall(r'\\begin\{chc\}(.*?)\\end\{chc\}', block, re.DOTALL)
                        for chc_content in chc_blocks:
                            child_uuid = str(uuid.uuid4())
                            questions_data, options_data, _ = dispatch_block(chc_content, teacher_id, child_uuid, parent_uuid, subject, grade_int, metadata, file_path, target_img_dir)
                            temp_blocks_to_process.append((questions_data, options_data))
                    else:
                        # NORMAL
                        question_public_id = str(uuid.uuid4())
                        questions_data, options_data, _ = dispatch_block(block, teacher_id, question_public_id, None, subject, grade_int, metadata, file_path, target_img_dir)
                        temp_blocks_to_process.append((questions_data, options_data))
                        
                    # 5. Format to logic_manager standard
                    for questions_data, options_data in temp_blocks_to_process:
                        if not questions_data: continue
                        
                        question_record = {
                            "teacher_id": teacher_id,
                            "public_id": questions_data.get('public_id'),
                            "subject": subject,
                            "grade": grade_int,
                            "parent_id": questions_data.get('parent_id'),
                            "question_type": questions_data.get('question_type'), 
                            "layout_type": questions_data.get('layout_type'),
                            "content": questions_data.get('content'), 
                            "solution": questions_data.get('solution'),
                            "chapter": chapter, 
                            "lesson": lesson, 
                            "complexity": int(complexity),
                            "is_shufflable": questions_data.get('is_shufflable', True)
                        }

                        images_records = []
                        for img in questions_data.get('image', []):
                            images_records.append({
                                "storage_path": img.get('storage_path'),
                                "img_type": img.get('img_type'),
                                "img_scale": img.get('img_scale'),
                                "raw_code": img.get('raw_code')
                            })
                            
                        details_table = {
                            "mc": "q_choice_details", 
                            "tf": "q_truefalse_details", 
                            "sa": "q_shortans_details",
                        }.get(questions_data.get('question_type'))
                        
                        final_db_ready_data.append({
                            "table_question": question_record,
                            "table_images": images_records,
                            "table_details": {
                                "target_table": details_table, 
                                "records": options_data
                            }
                        })
                        
    print(f"[+] Đã xử lý xong. Lọc được {len(final_db_ready_data)} questions/sub-questions.")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_db_ready_data, f, ensure_ascii=False, indent=4)
    print(f"[+] Đã lưu vào {OUTPUT_JSON}")

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    
    try:
        import torch
        import cv2
        torch.set_num_threads(1)
        cv2.setNumThreads(0)
        from parse_visuals import init_latex_ocr
        init_latex_ocr()
    except Exception:
        pass

    parse_latex_files(TEX_FOLDER)
