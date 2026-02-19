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
    # full_text = re.sub(r'%.*', '', full_text) # bug
    full_text = re.sub(r'(?<!\\)(?<!\d)%.*', '', full_text) # Đã fix bug

    # 3. Tìm tất cả các khối từ \begin{ex} đến \end{ex}
    # Sử dụng (.*?) - dấu chấm hỏi để nó "dừng đúng chỗ" ở cuối mỗi câu
    question_blocks = re.findall(r'\\begin\{ex\}(.*?)\\end\{ex\}', full_text, re.DOTALL)

    questions = []
    answers = []

    for index, block in enumerate(question_blocks):
        # Tự sinh mã câu hỏi Q0000001, Q0000002..., tạm test, nào sẽ dùng uuid
        q_id = f"Q{str(index + 1).zfill(7)}TF"

        # 2. Xử lý Layout và Hình ảnh
        layout_type = None
        image_tex = ""
        content_tex = ""
        options_part = ""

        if "\\immini" in block:
            immini_pos = block.find("\\immini")
            # Tham số 1 của immini (Nội dung câu hỏi hoặc bao gồm cả choiceTF)
            arg1_start = block.find("{", immini_pos)
            arg1_content, arg1_end = get_bracket_content(block, arg1_start)
            
            # Tham số 2 của immini (Mã hình ảnh)
            arg2_start = block.find("{", arg1_end + 1)
            image_tex, arg2_end = get_bracket_content(block, arg2_start)

            if "\\choiceTF" in arg1_content:
                layout_type = "immini_all" # Trường hợp 2: ChoiceTF nằm trong immini
                # Tách content và choiceTF trong Arg 1
                parts = re.split(r'\\choiceTF', arg1_content, maxsplit=1)
                content_tex = parts[0].strip()
                options_part = arg1_content[len(parts[0]):]
            else:
                layout_type = "immini_content" # Trường hợp 1: ChoiceTF nằm ngoài immini
                content_tex = arg1_content
                options_part = block[arg2_end + 1:]
        
        # elif "\\begin{center}" in block:
        #     layout_type = "center" # Trường hợp 3: Ảnh ở giữa
        #     center_match = re.search(r'\\begin\{center\}(.*?)\\end\{center\}', block, re.DOTALL)
        #     if center_match:
        #         image_tex = center_match.group(1).strip()
        #         block_no_image = block.replace(center_match.group(0), "")
        #         parts = re.split(r'\\choiceTF', block_no_image, maxsplit=1)
        #         content_tex = parts[0].strip()
        #         options_part = block_no_image[len(parts[0]):]
        
        else:
            # Trường hợp NORMAL
            parts = re.split(r'\\choiceTF', block, maxsplit=1)
            content_tex = parts[0].strip()
            options_part = block[len(parts[0]):] if len(parts) > 1 else ""

        # Bóc tách Lời giải
        # solution_match = re.search(r'\\loigiai\{(.*?)\}', block, re.DOTALL) # Ditcu bị lỗi nếu bị lồng ngoặc
        solution_tex = extract_loigiai(block)

        # Bóc tách 4 Lời giải ứng với phương án
        choices = []

        itemchoice_match = re.search(
            r'\\begin\s*\{\s*itemchoice\s*\}(.*?)\\end\s*\{\s*itemchoice\s*\}',
            solution_tex,
            re.DOTALL
        )

        if itemchoice_match:
            item_block = itemchoice_match.group(1)

            # Lời giải chung
            explanation = solution_tex[:itemchoice_match.start()].strip()

            # Tách phương án
            parts = re.split(r'\\itemch', item_block)
            choices = [p.strip() for p in parts[1:]]

        else:
            explanation = None
            choices = None

        # 3. Bóc tách 4 Phương án (Dùng hàm duyệt ngoặc để an toàn tuyệt đối)
        parsed_options = []
        # Tìm tất cả các cặp { } trong phần options_part
        option_search_pos = 0
        opt_index = 1
        while True:
            start_opt = options_part.find("{", option_search_pos)
            if start_opt == -1 or opt_index > 4: break
            
            opt_content, end_opt = get_bracket_content(options_part, start_opt)
            ans_id = f"{q_id}D{opt_index}"
            is_correct = "\\True" in opt_content

            parsed_options.append({
                "id": ans_id,
                "question_id": q_id,
                "content_tex": opt_content.replace("\\True", "").strip(),
                "is_correct": is_correct,
                "order_index": opt_index,
                "explanation_tex": choices[opt_index - 1] if (opt_index - 1) < len(choices) else None,
                "original_order": opt_index,
                "is_shufflable": "true"
            })
            option_search_pos = end_opt + 1
            opt_index += 1
        

        questions.append(
            {
                "teacher_id": teacher_id,
                "id": q_id,
                "subject_id": subject_id,
                "grade": grade,
                "parent_id": None,
                "q_type": "choiceTF",
                "layout_type": layout_type,
                "content_tex": content_tex,
                "image": image_tex, # Trường mới lưu mã LaTeX/url của ảnh
                "solution_tex": explanation,
                "chapter": None,
                "lesson": None,
                "difficulty": None,
                "is_shufflable": True
            },
        )
        answers.extend(
            parsed_options,
        )
    question_count = len(questions)
    questions_data = {
        "questions": questions,
        "question_details": answers
    }
    return questions_data, question_count

# CHẠY THỬ
file_path = r"Sample/sample_TF.tex" 
final_data, count = parse_full_latex_file(file_path, "GV-001", "LY", 11)

with open('Sample/sample_TF.json', 'w', encoding='utf-8') as f:
    json.dump(final_data, f, ensure_ascii=False, indent=4)

print(f"Đã xử lý xong {count} câu hỏi thành công!")