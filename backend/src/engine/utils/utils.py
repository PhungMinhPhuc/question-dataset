def replace_math_macros(s: str) -> str:
    if not s: return s
    def replace_macro(macro_name, start_replacement, end_replacement, text):
        macro_str = '\\' + macro_name + '{'
        while True:
            idx = text.find(macro_str)
            if idx == -1:
                break
            brace_count = 0
            start_content = idx + len(macro_str)
            end_content = -1
            for i in range(start_content, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    if brace_count == 0:
                        end_content = i
                        break
                    brace_count -= 1
            if end_content != -1:
                inner = text[start_content:end_content]
                text = text[:idx] + start_replacement + inner + end_replacement + text[end_content+1:]
            else:
                break
        return text

    s = replace_macro('hoac', r'\left[\begin{aligned}', r'\end{aligned}\right.', s)
    s = replace_macro('heva', r'\left\{\begin{aligned}', r'\end{aligned}\right.', s)
    return s
