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

def parse_full_latex_file(file_path, teacher_id, subject_id, grade):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            full_text = f.read()
    except:
        return f"Lỗi đọc file: {Exception}", 0

    # full_text = re.sub(r'%.*', '', full_text) # Gây lỗi công thức khi có kiểu như 90% (do tham lam quá =)))
    full_text = re.sub(r'(?<!\\)(?<!\d)%.*', '', full_text) # Đã fix bug
    question_blocks = re.findall(r'\\begin\{ex\}(.*?)\\end\{ex\}', full_text, re.DOTALL)

    questions = []
    answers = []

    for index, block in enumerate(question_blocks):
        q_id = f"Q{str(index + 1).zfill(7)}"
        
        # 1. Bóc tách Lời giải (Luôn lấy phần này trước và xóa khỏi block để xử lý phần trên dễ hơn)
        solution_tex = ""
        loigiai_match = re.search(r'\\loigiai\s*\{', block)
        if loigiai_match:
            solution_tex, _ = get_bracket_content(block, loigiai_match.end() - 1)
            block = block[:loigiai_match.start()].strip() # Cắt bỏ phần lời giải khỏi block

        # 2. Xử lý Layout và Hình ảnh
        layout_type = None
        image_tex = ""
        content_tex = ""
        options_part = ""

        if "\\immini" in block:
            immini_pos = block.find("\\immini")
            # Tham số 1 của immini (Nội dung câu hỏi hoặc bao gồm cả choice)
            arg1_start = block.find("{", immini_pos)
            arg1_content, arg1_end = get_bracket_content(block, arg1_start)
            
            # Tham số 2 của immini (Mã hình ảnh)
            arg2_start = block.find("{", arg1_end + 1)
            image_tex, arg2_end = get_bracket_content(block, arg2_start)

            if "\\choice" in arg1_content:
                layout_type = "immini_all" # Trường hợp 2: Choice nằm trong immini
                # Tách content và choice trong Arg 1
                parts = re.split(r'\\choice', arg1_content, maxsplit=1)
                content_tex = parts[0].strip()
                options_part = arg1_content[len(parts[0]):]
            else:
                layout_type = "immini_content" # Trường hợp 1: Choice nằm ngoài immini
                content_tex = arg1_content
                options_part = block[arg2_end + 1:]
        
        # Đoạn này chắc bỏ vì nhúng trực tiếp img vào luôn phần content tex, khi convert word thì pandoc vẫn hiểu được, còn immini thì phải dùng một thuộc tính khác để lưu
        # elif "\\begin{center}" in block:
        #     layout_type = "center" # Trường hợp 3: Ảnh ở giữa
        #     center_match = re.search(r'\\begin\{center\}(.*?)\\end\{center\}', block, re.DOTALL)
        #     if center_match:
        #         image_tex = center_match.group(1).strip()
        #         block_no_image = block.replace(center_match.group(0), "")
        #         parts = re.split(r'\\choice', block_no_image, maxsplit=1)
        #         content_tex = parts[0].strip()
        #         options_part = block_no_image[len(parts[0]):]
        
        else:
            # Trường hợp NORMAL
            parts = re.split(r'\\choice', block, maxsplit=1)
            content_tex = parts[0].strip()
            options_part = block[len(parts[0]):] if len(parts) > 1 else ""

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
                "explanation_tex": None,
                "original_order": opt_index,
                "is_shufflable": True
            })
            option_search_pos = end_opt + 1
            opt_index += 1

        # 4. Đẩy vào danh sách tổng
        questions.append({
            "teacher_id": teacher_id,
            "id": q_id,
            "subject_id": subject_id,
            "grade": grade,
            "parent_id": None,
            "q_type": "choice",
            "layout_type": layout_type,
            "content_tex": content_tex,
            "image": image_tex, # Trường mới lưu mã LaTeX/url của ảnh
            "solution_tex": solution_tex,
            "chapter": None,
            "lesson": None,
            "difficulty": None,
            "is_shufflable": True,
        })
        answers.extend(parsed_options)

    return {"questions": questions, "question_details": answers}, len(questions)

# CHẠY THỬ
file_path = r"Sample/sample_MC.tex" 
final_data, count = parse_full_latex_file(file_path, "GV-001", "LY", 11)

with open('Sample/sample_MC.json', 'w', encoding='utf-8') as f:
    json.dump(final_data, f, ensure_ascii=False, indent=4)

print(f"Đã xử lý xong {count} câu hỏi thành công!")