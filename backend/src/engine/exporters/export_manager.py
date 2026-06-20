import os
import random
import copy
import zipfile
import io
from typing import List

from exporters.common import shuffle_contest, generate_answer_key_excel
from exporters.latex_exporter import export_latex
from exporters.pdf_exporter import export_pdf
from exporters.word_exporter import export_word

def export_contest_zip(contest: dict, questions: List[dict], num_shuffles: int, formats: List[str], exam_title: str = "", general_info: str = "", department: str = "", exam_type: str = "", subject: str = "", duration: int = 50, code_type: str = "incremental", starting_code: str = "001", code_step: int = 1, random_length: int = 3) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    
    answer_keys = {} # code -> { q_num: ans }
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Original Exam
        original_code = "000"
        orig_q = copy.deepcopy(questions)
        
        orig_key = {}
        q_c = 1
        for q in orig_q:
            if q['question_type'] == 'st': continue
            ans = ""
            if q['question_type'] == 'mc':
                for idx, opt in enumerate(q.get('options', [])):
                    if opt.get('is_correct'): ans = chr(65+idx); break
            elif q['question_type'] == 'tf':
                ans = ",".join("D" if o.get('is_correct') else "S" for o in q.get('options', []))
            elif q['question_type'] == 'sa':
                ans = q.get('options', [{}])[0].get('content', '') if q.get('options') else ''
            orig_key[q_c] = ans
            q_c += 1
            
        answer_keys[original_code] = orig_key
        
        # Output original exam
        if 'latex' in formats:
            export_latex(contest, orig_q, original_code, exam_title, department, exam_type, subject, duration, general_info, True, zf)
            
        if 'pdf' in formats:
            export_pdf(contest, orig_q, original_code, exam_title, department, exam_type, subject, duration, general_info, True, zf)

        if 'word' in formats:
            export_word(contest, orig_q, original_code, exam_title, department, exam_type, subject, duration, general_info, True, zf)
                
        # Shuffled exams
        used_codes = {original_code}
        for i in range(num_shuffles):
            if code_type == "incremental":
                try:
                    num = int(starting_code) + i * code_step
                    code = str(num).zfill(max(3, len(starting_code)))
                except ValueError:
                    code = f"{starting_code}-{i+1}"
            else:
                min_val = 10 ** (random_length - 1)
                max_val = (10 ** random_length) - 1
                if random_length <= 1:
                    min_val = 0
                    max_val = 9
                code = f"{random.randint(min_val, max_val):0{random_length}d}"
                while code in used_codes:
                    code = f"{random.randint(min_val, max_val):0{random_length}d}"
                used_codes.add(code)

            shuf_q, shuf_key = shuffle_contest(orig_q)
            answer_keys[code] = shuf_key
            
            if 'latex' in formats:
                export_latex(contest, shuf_q, code, exam_title, department, exam_type, subject, duration, general_info, False, zf)
                
            if 'pdf' in formats:
                export_pdf(contest, shuf_q, code, exam_title, department, exam_type, subject, duration, general_info, False, zf)
                
            if 'word' in formats:
                export_word(contest, shuf_q, code, exam_title, department, exam_type, subject, duration, general_info, False, zf)

        # Write Answer Key Excel
        excel_content = generate_answer_key_excel(answer_keys)
        zf.writestr("Bang_Dap_An.xlsx", excel_content)

        if 'latex' in formats:
            current_dir = os.path.dirname(__file__)
            extest_path = os.path.join(current_dir, "ex_test.sty")
            if os.path.exists(extest_path):
                zf.write(extest_path, "ex_test.sty")

    return zip_buffer
