import json
import re
from parsers.process_mc import process_mc_block
from parsers.process_tf import process_tf_block
from parsers.process_sa import process_sa_block
from parsers.process_oe import process_oe_block
from parsers.process_stimulus import process_stimulus_block
from utils.get_bracket_content import get_bracket_content
from utils.extract_loigiai import extract_loigiai

# Nhận diện loại câu hỏi và gọi hàm xử lý tương ứng
def dispatch_block(block, q_id, parent_id, teacher_id, subject_id, grade, metadata):
    # Đúng/Sai # Xử lý choiceTF trước vì trong choiceTF có choice
    if "\\choiceTF" in block:
        return process_tf_block(block, q_id, parent_id, teacher_id, subject_id, grade, metadata['chapter'], metadata['lesson'], metadata['complexity'], True)
    
    # Trắc nghiệm 4 lựa chọn
    elif "\\choice" in block:
        return process_mc_block(block, q_id, parent_id, teacher_id, subject_id, grade, metadata['chapter'], metadata['lesson'], metadata['complexity'], True)
    
    # Trả lời ngắn
    elif "\\shortans" in block:
        return process_sa_block(block, q_id, parent_id, teacher_id, subject_id, grade, metadata['chapter'], metadata['lesson'], metadata['complexity'], True)
    
    # Tự luận
    else:
        return process_oe_block(block, q_id, parent_id, teacher_id, subject_id, grade, metadata['chapter'], metadata['lesson'], metadata['complexity'], True)
    

# Bắt đầu diệt mồi
def parse_latex_to_json(file_path, teacher_id, subject_id, grade, chapter=None, lesson=None, complexity=None):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            full_text = f.read()
    except:
        return f"Lỗi đọc file: {Exception}", 0

    # Tiền xử lý: Xóa comment %
    full_text = re.sub(r'(?<!\\)(?<!\d)%.*', '', full_text) # Đã fix bug
    
    # Tìm các khối \begin{ex} ... \end{ex}
    question_blocks = re.findall(r'\\begin\{ex\}(.*?)\\end\{ex\}', full_text, re.DOTALL)

    all_questions = []
    all_answers = []
    q_counter = 1
    count = {
        "choice": 0,
        "truefalse": 0,
        "shortans": 0,
        "essay": 0,
        "stimulus": 0
    }
    metadata = {'chapter': chapter, 'lesson': lesson, 'complexity': complexity}

    for block in question_blocks:
        # KIỂM TRA CẤU TRÚC CÂU HỎI CHÙM (\sochc)
        sochc_match = re.search(r'\\sochc\s*\{(\d+)\}\s*\{', block)
        
        if sochc_match:
            # Xử lý câu hỏi CHA (Stimulus)
            parent_id = f"Q{str(q_counter).zfill(7)}"
            q_counter += 1
            stim_content, _ = get_bracket_content(block, sochc_match.end() - 1)
            stim_data = process_stimulus_block(stim_content, parent_id, None,teacher_id, subject_id, grade, chapter, lesson, complexity, False)
            all_questions.append(stim_data)
            count['stimulus'] += 1 # Đếm số câu dẫn
            
            # Xử lý các câu con (\begin{chc})
            chc_blocks = re.findall(r'\\begin\{chc\}(.*?)\\end\{chc\}', block, re.DOTALL)
            for chc_content in chc_blocks:
                child_id = f"Q{str(q_counter).zfill(7)}"
                
                # Gọi dispatcher cho câu con
                q_data, a_data, _ = dispatch_block(chc_content, child_id, parent_id, teacher_id, subject_id, grade, metadata)
                
                all_questions.append(q_data)
                all_answers.extend(a_data)
                q_counter += 1
                count[q_data['q_type']] += 1
        
        else:
            # XỬ LÝ CÂU ĐƠN
            q_id = f"Q{str(q_counter).zfill(7)}"
            
            q_data, a_data, _ = dispatch_block(block, q_id, None, teacher_id, subject_id, grade, metadata)
            
            all_questions.append(q_data)
            all_answers.extend(a_data)
            q_counter += 1
            count[q_data['q_type']] += 1

    # Xuất kết quả cuối cùng
    result = {
        "questions": all_questions,
        "question_details": all_answers
    }
    
    return result, q_counter - 1, count

# CHẠY THỬ
if __name__ == "__main__":
    file_path = "Sample/data_test.tex"
    data, q_count, count = parse_latex_to_json(file_path, "GV-001", "LY", 11)
    with open('Sample/data_test.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"MC: {count['choice']}; TF: {count['truefalse']}; SA: {count['shortans']}; OE: {count['essay']}; ST: {count['stimulus']}")
    print(f"Đã xử lý xong {q_count} câu hỏi")