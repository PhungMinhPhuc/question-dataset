import re

def strip_pandocbounded(text):
    # \pandocbounded{\includegraphics[...]{...}} -> \includegraphics[...]{...}
    # This might be tricky if there are nested braces, but pandocbounded usually wraps a single includegraphics
    return re.sub(r'\\pandocbounded\{(\\includegraphics[^}]*\}|\\includegraphics[^\]]*\]\{[^}]*\})\}', r'\1', text)

def process_standard_to_btpro(tex_content):
    # Clean up pandocbounded
    tex_content = strip_pandocbounded(tex_content)
    
    # Remove quote blocks pandoc might have added
    tex_content = re.sub(r'\\begin\{quote\}', '', tex_content)
    tex_content = re.sub(r'\\end\{quote\}', '', tex_content)
    
    # Clean up some common LaTeX tags that interfere with parsing
    # Pandoc sometimes adds \textbf{} around \ul{} or vice versa.
    # Handle formats where option content is inside textbf/ul (TogTeX style) first.
    # Pattern allows one level of nested braces (e.g. \text{...}, subscripts) in content.
    _inner = r'(?:[^{}]|\{[^{}]*\})+'
    
    # 1. Handle \textcolor{...}{...} (often red for correct answers)
    tex_content = re.sub(r'\\textcolor\{[^}]+\}\{\\textbf\{([A-D])\.\s*(' + _inner + r')\}\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\textbf\{\\textcolor\{[^}]+\}\{([A-D])\.\s*(' + _inner + r')\}\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\textcolor\{[^}]+\}\{([A-D])\.\s*(' + _inner + r')\}', r'__TRUE__\1. \2', tex_content)
    
    tex_content = re.sub(r'\\textcolor\{[^}]+\}\{\\textbf\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\textbf\{\\textcolor\{[^}]+\}\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\textcolor\{[^}]+\}\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)

    # 2. Handle \ul{...} and \underline{...} (Underline)
    tex_content = re.sub(r'\\textbf\{\\ul\{([A-D])\.\s*(' + _inner + r')\}\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\ul\{\\textbf\{([A-D])\.\s*(' + _inner + r')\}\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\textbf\{\\underline\{([A-D])\.\s*(' + _inner + r')\}\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\underline\{\\textbf\{([A-D])\.\s*(' + _inner + r')\}\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\ul\{([A-D])\.\s*(' + _inner + r')\}', r'__TRUE__\1. \2', tex_content)
    tex_content = re.sub(r'\\underline\{([A-D])\.\s*(' + _inner + r')\}', r'__TRUE__\1. \2', tex_content)

    tex_content = re.sub(r'\\textbf\{\\ul\{([A-D])\.\}\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\ul\{\\textbf\{([A-D])\.\}\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\textbf\{\\underline\{([A-D])\.\}\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\underline\{\\textbf\{([A-D])\.\}\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\textbf\{\\ul\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\ul\{\\textbf\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\textbf\{\\underline\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\underline\{\\textbf\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\ul\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)
    tex_content = re.sub(r'\\underline\{([A-D])\}\.?\}', r'__TRUE__\1.', tex_content)

    # Normal options
    tex_content = re.sub(r'\\textbf\{([A-D])\.\s*(' + _inner + r')\}', r'__OPT__\1. \2', tex_content)
    tex_content = re.sub(r'\\textbf\{([A-D])\.\}', r'__OPT__\1.', tex_content)
    tex_content = re.sub(r'\\textbf\{([A-D])\}\.', r'__OPT__\1.', tex_content)

    # True/False options clean up (a), b), c), d))
    tex_content = re.sub(r'\\textbf\{([a-d])\)\}', r'__TF__\1)', tex_content)
    
    # Split by questions
    questions = re.split(r'\\textbf\{Câu\s+\d+\}[\.:]?|\\textbf\{Câu\s+\d+[\.:]?\}', tex_content, flags=re.IGNORECASE)
    
    final_tex = ""
    for q_content in questions[1:]:
        if not q_content.strip():
            continue

        # Split into main part and solution part.
        # Matches: \textbf{Hướng dẫn}, \textbf{Lời giải}, \textbf{LỜI GIẢI}, or
        # bare "LỜI GIẢI" / "Lời giải" when not wrapped in \textbf{}.
        parts = re.split(
            r'\\textbf\{[Hh]ướng\s+[Dd]ẫn\}'
            r'|\\textbf\{[Ll]ời\s+[Gg]iải\}'
            r'|\\textbf\{LỜI\s+GIẢI\}'
            r'|\bLỜI\s+GIẢI\b'
            r'|\b[Ll]ời\s+[Gg]iải\b',
            q_content,
        )

        main_part = parts[0]
        solution_part = parts[1] if len(parts) > 1 else ""

        # Save any __TRUE__ hint from solution BEFORE cleaning (used as MC correct-answer fallback)
        _sol_true_match = re.search(r'__TRUE__([A-D])', solution_part)
        _sol_correct_hint = _sol_true_match.group(1) if _sol_true_match else None

        # Remove option tokens from solution (they come from \textbf{a)}, \textbf{A.} etc.
        # in the solution explanation section — convert back to plain labels)
        solution_part = re.sub(r'__TF__([a-d])', r'\1', solution_part)
        solution_part = re.sub(r'__(OPT|TRUE)__([A-D])', r'\2', solution_part)

        # Strip leftover \textbf{} from both parts.  Answer-label markers (A., B., …,
        # a), b), …) were already converted to __OPT__/__TF__ tokens above, so this is
        # safe and removes bold formatting that the frontend would otherwise show literally.
        main_part = re.sub(r'\\textbf\{((?:[^{}\\]|\\.)*)\}', r'\1', main_part)
        solution_part = re.sub(r'\\textbf\{((?:[^{}\\]|\\.)*)\}', r'\1', solution_part)
        
        # Strip leftover \ul{} and \underline{}
        main_part = re.sub(r'\\(?:ul|underline)\{((?:[^{}\\]|\\.)*)\}', r'\1', main_part)
        solution_part = re.sub(r'\\(?:ul|underline)\{((?:[^{}\\]|\\.)*)\}', r'\1', solution_part)
        
        # Strip leftover \textcolor{...}{}
        main_part = re.sub(r'\\textcolor\{[^}]+\}\{((?:[^{}\\]|\\.)*)\}', r'\1', main_part)
        solution_part = re.sub(r'\\textcolor\{[^}]+\}\{((?:[^{}\\]|\\.)*)\}', r'\1', solution_part)
        
        # Determine question type
        is_short_answer = False
        short_answer_val = ""
        # Check Short Answer
        sa_match = re.search(r'(?:Đáp án|Trả lời ngắn)\s*:\s*([^\n]+)', main_part + "\n" + solution_part, flags=re.IGNORECASE)
        if sa_match:
            is_short_answer = True
            short_answer_val = sa_match.group(1).strip()
            
        # Check True False (look for __TF__a) or just a) )
        is_true_false = False
        if not is_short_answer and (re.search(r'__TF__[a-d]\)', main_part) or re.search(r'(?:\n|^|\s+)([a-d])\)', main_part)):
            is_true_false = True

        if is_short_answer:
            # Xóa dòng Đáp án: khỏi main_part
            main_part = re.sub(r'(?:Đáp án|Trả lời ngắn)\s*:\s*[^\n]+', '', main_part, flags=re.IGNORECASE).strip()
            final_tex += f"\\begin{{ex}}\n{main_part}\n\\shortans{{{short_answer_val}}}\n"

        elif is_true_false:
            # Replace raw a) with __TF__a) if not already
            if not '__TF__' in main_part:
                main_part = re.sub(r'(?:\n|^|\s+)([a-d])\)', r'\n__TF__\1)', main_part)
                
            opts_split = re.split(r'__TF__([a-d])\)', main_part)
            question_text = opts_split[0].strip()
            
            options_dict = {}
            i = 1
            while i < len(opts_split) - 1:
                letter = opts_split[i].lower()
                content = opts_split[i+1].strip() if i+1 < len(opts_split) else ""
                options_dict[letter] = content
                i += 2
                
            final_tex += f"\\begin{{ex}}\n{question_text}\n\\choiceTF\n"
            for letter in ['a', 'b', 'c', 'd']:
                if letter in options_dict:
                    # Mặc định true/false sẽ không biết đáp án từ đề standard nếu ko gạch chân
                    # Cứ điền tạm vào
                    final_tex += f"{{{options_dict[letter]}}}\n"
                else:
                    final_tex += "{}\n"

        else:
            # Multiple Choice (Default)
            opts_split = re.split(r'__(TRUE|OPT)__([A-D])\.', main_part)
            question_text = opts_split[0].strip()
            
            options_dict = {}
            correct_ans = None
            
            i = 1
            while i < len(opts_split) - 1:
                is_true = (opts_split[i] == 'TRUE')
                letter = opts_split[i+1].upper()
                content = opts_split[i+2].strip() if i+2 < len(opts_split) else ""
                options_dict[letter] = content
                if is_true:
                    correct_ans = letter
                i += 3
                
            if not correct_ans and _sol_correct_hint:
                correct_ans = _sol_correct_hint
            if not correct_ans and solution_part:
                match = re.search(r'Chọn\s+([A-D])', solution_part, flags=re.IGNORECASE)
                if match:
                    correct_ans = match.group(1).upper()
                    
            final_tex += f"\\begin{{ex}}\n{question_text}\n\\choice\n"
            for letter in ['A', 'B', 'C', 'D']:
                if letter in options_dict:
                    prefix = "\\True " if letter == correct_ans else ""
                    final_tex += f"{{{prefix}{options_dict[letter]}}}\n"
                else:
                    final_tex += "{}\n"
                
        if solution_part.strip():
            cleaned_solution = re.sub(r'\.?\s*Chọn\s+[A-D]\s*', '', solution_part, flags=re.IGNORECASE).strip()
            # Xóa Đáp án ra khỏi lời giải nếu có
            cleaned_solution = re.sub(r'(?:Đáp án|Trả lời ngắn)\s*:\s*[^\n]+', '', cleaned_solution, flags=re.IGNORECASE).strip()
            if cleaned_solution:
                final_tex += f"\\loigiai{{\n{cleaned_solution}\n}}\n"
            
        final_tex += "\\end{ex}\n\n"
        
    return final_tex

def convert_standard_docx_to_tex(docx_path, tex_path):
    with open(tex_path, "r", encoding="utf-8") as f:
        tex = f.read()
        
    btpro = process_standard_to_btpro(tex)
    
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(btpro)
    
    return tex_path
