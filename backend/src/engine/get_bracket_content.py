def get_bracket_content(text, start_index):
    # Tìm nội dung bên trong cặp dấu {} tính từ vị trí start_index (vị trí dấu {)
    brace_count = 0
    content = ""
    for i in range(start_index, len(text)):
        # Kiểm tra xem dấu ngoặc có bị escape không
        is_escaped = False
        if i > 0 and text[i-1] == '\\':
            backslash_count = 0
            j = i - 1
            while j >= 0 and text[j] == '\\':
                backslash_count += 1
                j -= 1
            if backslash_count % 2 == 1:
                is_escaped = True

        if not is_escaped:
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
        
        if brace_count > 0:
            if brace_count == 1 and text[i] == '{' and not is_escaped:
                continue # Không lấy dấu { ngoài cùng
            content += text[i]
        
        if brace_count == 0 and i > start_index:
            return content.strip(), i # Trả về nội dung và vị trí dấu } kết thúc
    return "", -1
