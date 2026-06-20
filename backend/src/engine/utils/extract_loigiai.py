def extract_loigiai(text):
    start = text.find(r'\loigiai{')
    if start == -1:
        return None

    i = start + len(r'\loigiai{')
    brace = 1
    content = ""

    while i < len(text) and brace > 0:
        is_escaped = (i > 0 and text[i-1] == '\\')
        if i > 1 and text[i-1] == '\\' and text[i-2] == '\\':
            is_escaped = False
        if text[i] == '{' and not is_escaped:
            brace += 1
        elif text[i] == '}' and not is_escaped:
            brace -= 1

        if brace > 0:
            content += text[i]
        i += 1

    return content.strip()