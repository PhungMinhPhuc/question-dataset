import re
import json

def get_bracket_content(text, start_index):
    # Tìm nội dung bên trong cặp dấu {} tính từ vị trí start_index (vị trí dấu {)
    brace_count = 0
    content = ""
    for i in range(start_index, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
        
        if brace_count > 0:
            if brace_count == 1 and text[i] == '{': continue # Không lấy dấu { ngoài cùng
            content += text[i]
        
        if brace_count == 0 and i > start_index:
            return content.strip(), i # Trả về nội dung và vị trí dấu } kết thúc
    return "", -1

def extract_loigiai(text):
    start = text.find(r'\loigiai{')
    if start == -1:
        return None

    i = start + len(r'\loigiai{')
    brace = 1
    content = ""

    while i < len(text) and brace > 0:
        if text[i] == '{':
            brace += 1
        elif text[i] == '}':
            brace -= 1

        if brace > 0:
            content += text[i]
        i += 1

    return content.strip()

def parse_full_latex_file(file_path, teacher_id, subject_id, grade):
    # 1. Đọc nội dung toàn bộ file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            full_text = f.read()
    except Exception as e:
        return f"Lỗi đọc file: {e}"

    # 2. Xóa bỏ chú thích (%) để tránh nhiễu
    full_text = re.sub(r'(?<!\\)(?<!\d)%.*', '', full_text) # Đã fix bug

    # 3. Tìm tất cả các khối từ \begin{ex} đến \end{ex}
    # Sử dụng (.*?) - dấu chấm hỏi để nó "dừng đúng chỗ" ở cuối mỗi câu
    question_blocks = re.findall(r'\\begin\{ex\}(.*?)\\end\{ex\}', full_text, re.DOTALL)

    questions = []

    for index, block in enumerate(question_blocks):
        # Tự sinh mã câu hỏi Q0000001, Q0000002..., tạm test, nào sẽ dùng uuid
        q_id = f"Q{str(index + 1).zfill(7)}OE"

        # 2. Xử lý Layout và Hình ảnh
        layout_type = None
        image_tex = ""
        content_tex = ""

        if "\\immini" in block:
            immini_pos = block.find("\\immini")
            # Tham số 1 của immini (Nội dung câu hỏi hoặc bao gồm cả choiceTF)
            arg1_start = block.find("{", immini_pos)
            arg1_content, arg1_end = get_bracket_content(block, arg1_start)
            
            # Tham số 2 của immini (Mã hình ảnh)
            arg2_start = block.find("{", arg1_end + 1)
            image_tex, _ = get_bracket_content(block, arg2_start)
            layout_type = "immini_content"
            content_tex = arg1_content
        else:
            # Trường hợp NORMAL
            parts = re.split(r'\\loigiai', block, maxsplit=1)
            # Nội dung câu hỏi là phần trước \loigiai
            content_tex = parts[0].strip()

        # Bóc tách Lời giải
        solution_tex = extract_loigiai(block)

        # Điền nội dung vào file json
        # không cần xuất nội dung question_details

        questions.append(
            {
                "teacher_id": teacher_id,
                "id": q_id,
                "subject_id": subject_id,
                "grade": grade,
                "parent_id": None,
                "q_type": "essay",
                "layout_type": layout_type,
                "content_tex": content_tex,
                "image": image_tex, # Trường mới lưu mã LaTeX/url của ảnh
                "solution_tex": solution_tex,
                "chapter": None,
                "lesson": None,
                "difficulty": None,
                "is_shufflable": True
            },
        )
    question_count = len(questions)
    questions_data = {
        "questions": questions,
    }
    return questions_data, question_count

# CHẠY THỬ
file_path = r"Sample/sample_OE.tex" 
final_data, count = parse_full_latex_file(file_path, "GV-001", "LY", 11)

with open('Sample/sample_OE.json', 'w', encoding='utf-8') as f:
    json.dump(final_data, f, ensure_ascii=False, indent=4)

print(f"Đã xử lý xong {count} câu hỏi thành công!")