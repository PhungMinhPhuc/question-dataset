import os
import random
import copy
import zipfile
import io
from typing import List

from exporters.common import shuffle_contest, generate_answer_key_excel, min_pages
from exporters.latex_exporter import export_latex
from exporters.pdf_exporter import export_pdf, export_pdf_combined, measure_unit_heights
from exporters.word_exporter import export_word

def export_contest_zip(contest: dict, questions: List[dict], num_shuffles: int, formats: List[str], exam_title: str = "", general_info: str = "", department: str = "", exam_type: str = "", subject: str = "", duration: int = 50, code_type: str = "incremental", starting_code: str = "001", code_step: int = 1, random_length: int = 3, progress_callback=None, shuffle_order: bool = True, shuffle_options: bool = True) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    
    answer_keys = {} # code -> { q_num: ans }
    pdf_buffers = [] # list of bytes of generated pdfs
    
    total_steps = 1 + num_shuffles
    current_step = 0
    
    if progress_callback:
        progress_callback(current_step, total_steps, "Khởi tạo xuất đề...")
    
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
            
        # Note: Do not add original exam to answer_keys or pdf_buffers as requested
            
        # Output original exam
        if progress_callback:
            progress_callback(current_step, total_steps, f"Đang xuất đề gốc...")
            
        if 'latex' in formats:
            export_latex(contest, orig_q, original_code, exam_title, department, exam_type, subject, duration, general_info, True, zf)
            
        if 'pdf' in formats:
            export_pdf(contest, orig_q, original_code, exam_title, department, exam_type, subject, duration, general_info, True, zf)

        if 'word' in formats:
            # Đề gốc: in phần đề trước, rồi mới đến phần đề kèm đáp án + lời giải chi tiết
            export_word(contest, orig_q, original_code, exam_title, department, exam_type, subject, duration, general_info, True, zf, dual_section=True)

        current_step += 1
        
        # Shuffled exams
        used_codes = {original_code}
        pdf_codes_data = []  # gom (code, shuf_q) để compile PDF gộp 1 lần

        # Chỉ xếp trang lấp đầy + đồng bộ khi CÓ đảo thứ tự câu (đảo đề). Nếu chỉ
        # đảo phương án (đảo câu) thì giữ nguyên thứ tự -> mọi mã cùng bố cục, tự đồng bộ.
        unit_heights = {}
        target_pages = None
        if shuffle_order and 'pdf' in formats and num_shuffles > 0:
            if progress_callback:
                progress_callback(current_step, total_steps, "Đang đo bố cục để đồng bộ số trang...")
            unit_heights = measure_unit_heights(contest, orig_q, exam_title, department, exam_type, subject, duration, general_info)
            target_pages = min_pages(orig_q, unit_heights)

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
                
            if progress_callback:
                progress_callback(current_step, total_steps, f"Đang xuất mã đề {code} ({i+1}/{num_shuffles})...")

            shuf_q, shuf_key = shuffle_contest(
                orig_q, pack=shuffle_order, heights=unit_heights, target_pages=target_pages,
                shuffle_order=shuffle_order, shuffle_options=shuffle_options,
            )
            answer_keys[code] = shuf_key
            
            if 'latex' in formats:
                export_latex(contest, shuf_q, code, exam_title, department, exam_type, subject, duration, general_info, False, zf)
                
            if 'pdf' in formats:
                # Gom lại, compile gộp 1 lần sau vòng lặp (an toàn server yếu + nhanh)
                pdf_codes_data.append((code, shuf_q))

            if 'word' in formats:
                export_word(contest, shuf_q, code, exam_title, department, exam_type, subject, duration, general_info, False, zf)
                
            current_step += 1

        # Write Answer Key Excel
        if progress_callback:
            progress_callback(current_step, total_steps, "Đang đóng gói dữ liệu...")
            
        excel_content = generate_answer_key_excel(answer_keys)
        zf.writestr("Bang_Dap_An.xlsx", excel_content)

        if 'latex' in formats:
            current_dir = os.path.dirname(__file__)
            extest_path = os.path.join(current_dir, "ex_test.sty")
            if os.path.exists(extest_path):
                zf.write(extest_path, "ex_test.sty")
                
        # PDF đề đảo: compile TẤT CẢ mã trong 1 lần chạy (1 tiến trình, 2 lượt)
        if 'pdf' in formats and pdf_codes_data:
            if progress_callback:
                progress_callback(current_step, total_steps, f"Đang compile {len(pdf_codes_data)} mã đề ...")
            export_pdf_combined(
                contest, pdf_codes_data,
                exam_title, department, exam_type, subject, duration, general_info,
                zf, out_name="De_dao.pdf",
            )

    return zip_buffer
