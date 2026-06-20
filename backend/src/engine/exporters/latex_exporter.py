import os
import re
from typing import List, Dict, Any
from .common import fix_soft_newlines
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "api", ".env"))

def replace_img_with_tikz(q: dict, options_tex: str = "", for_pdf_compilation: bool = False) -> str:
    content = q.get('content', '') or ''
    images = q.get('images', [])
    layout = q.get('layout_type', '') or ''
    q_type = q.get('question_type', '')
    
    if layout.startswith('immini') or layout == 'thm':
        img_matches = re.findall(r'(!\[.*?\]\((.*?)\))', content)
        if img_matches:
            image_codes = []
            for full_match, url in img_matches:
                code = replace_img_with_tikz_in_str(full_match, images, for_pdf_compilation)
                image_codes.append(code.strip())
            
            text_content = re.sub(r'!\[.*?\]\((.*?)\)', '', content).strip()
            
            if layout == 'immini_all' and options_tex:
                text_content += "\n    " + options_tex
                
            opt_arg = "[]" if q_type == 'st' else "[thm]"
            img_block = "\n".join(image_codes)
            return f"\\immini{opt_arg}{{\n    {text_content}\n}}{{\n    {img_block}\n}}"
            
    # For normal images, wrap them in center with empty lines before and after
    def replacer(match):
        code = replace_img_with_tikz_in_str(match.group(0), images, for_pdf_compilation).strip()
        return f"\n\n\\begin{{center}}\n{code}\n\\end{{center}}\n\n"
        
    content = re.sub(r'!\[.*?\]\((.*?)\)', replacer, content)
    if options_tex:
        content += "\n    " + options_tex
    return content

def replace_img_with_tikz_in_str(content: str, images: list, for_pdf_compilation: bool = False) -> str:
    def replacer(match):
        import urllib.parse
        url = urllib.parse.unquote(match.group(1))
        scale_factor = 1
        for img in images:
            if img.get('storage_path') == url:
                sc = img.get('img_scale')
                if sc is not None:
                    try: scale_factor = float(sc)
                    except: pass
                    
                if img.get('img_type') == 'tikz' and img.get('raw_code'):
                    if for_pdf_compilation:
                        if "/static/images/" in url:
                            rel = url.split("/static/images/")[-1]
                        else:
                            rel = url.split("/")[-1]
                        sp = os.getenv("IMG_STORAGE_PATH", "./storage")
                        ap = os.path.abspath(os.path.join(sp, rel)).replace('\\', '/')
                        pdf = ap.replace('.svg', '.pdf')
                        if os.path.exists(pdf):
                            return f"\\includegraphics[scale={scale_factor:.2f}]{{{pdf}}}"
                    return "\n" + img.get('raw_code') + "\n"
        
        if "/static/images/" in url:
            rel_path = url.split("/static/images/")[-1]
        else:
            rel_path = url.split("/")[-1]
        
        sp = os.getenv("IMG_STORAGE_PATH", "./storage")
        local_path = os.path.join(sp, rel_path)
        abs_path = os.path.abspath(local_path).replace('\\', '/')
        
        ext = os.path.splitext(abs_path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg']:
            return f"\\includegraphics[width={scale_factor:.2f}\\textwidth]{{{abs_path}}}"
        else:
            return f"\\includegraphics[scale={scale_factor:.2f}]{{{abs_path}}}"
    return re.sub(r'!\[.*?\]\((.*?)\)', replacer, content)

def render_options_and_solution_latex(q: dict, include_solution: bool = True, for_pdf_compilation: bool = False) -> tuple[str, str]:
    q_type = q.get('question_type')
    options = q.get('options', [])
    solution = q.get('solution', '') or ''
    solution = replace_img_with_tikz_in_str(solution, q.get('images', []), for_pdf_compilation)
    
    options_lines = []
    
    if q_type == 'mc':
        options_lines.append("\\choice")
        for opt in options:
            mark = "\\True " if opt.get('is_correct') else ""
            opt_content = replace_img_with_tikz_in_str(opt.get('content', ''), q.get('images', []), for_pdf_compilation)
            options_lines.append(f"{{{mark}{opt_content}}}")
            
    elif q_type == 'tf':
        options_lines.append("\\choiceTF[1]")
        for opt in options:
            mark = "\\True " if opt.get('is_correct') else ""
            opt_content = replace_img_with_tikz_in_str(opt.get('content', ''), q.get('images', []), for_pdf_compilation)
            options_lines.append(f"{{{mark}{opt_content}}}")
            
        # Explanations for TF
        if any(opt.get('explaination') for opt in options):
            expl_lines = ["\\begin{itemchoice}"]
            for opt in options:
                expl = opt.get('explaination', '') or ''
                expl = replace_img_with_tikz_in_str(expl, q.get('images', []), for_pdf_compilation)
                expl_lines.append(f"\\itemch {expl}")
            expl_lines.append("\\end{itemchoice}")
            solution += "\n" + "\n".join(expl_lines)
            
    elif q_type == 'sa':
        correct_ans = options[0].get('content', '') if options else ''
        options_lines.append(f"\\shortans{{{correct_ans}}}")
        
    solution_lines = []
    if include_solution:
        solution_lines.append(f"\\loigiai{{{solution}}}")
    return "\n".join(options_lines), "\n".join(solution_lines)

def get_raw_latex(contest: dict, questions: List[dict], include_header: bool = True, use_minipage: bool = True, exam_title: str = "", general_info: str = "", code: str = "000", department: str = "", exam_type: str = "", subject: str = "", duration: int = 50, include_solution: bool = True, for_pdf_compilation: bool = False) -> str:
    lines = []
    
    # Calculate section counts
    total_mc = 0; total_tf = 0; total_sa = 0; total_oe = 0
    for q in questions:
        if q.get('question_type') == 'mc': total_mc += 1
        elif q.get('question_type') == 'tf': total_tf += 1
        elif q.get('question_type') == 'sa': total_sa += 1
        elif q.get('question_type') == 'oe': total_oe += 1
    
    if include_header:
        # Default fallback
        if not exam_title: exam_title = contest.get('title', 'Đề thi')
            
        header_tex = f"""\\documentclass[12pt, a4paper]{{article}}
\\usepackage{{amsmath,amssymb,fancyhdr}}
\\usepackage[top=1.2cm, bottom=2cm, left=1.5cm, right=1.2cm]{{geometry}}
\\usepackage[solcolor]{{ex_test}}
\\usepackage[utf8]{{vietnam}} 
\\usepackage{{fontspec}}
\\setmainfont{{Times New Roman}}
\\usepackage{{unicode-math}}
\\setmathfont{{CambriaMath}}
\\setmathrm{{CambriaMath}}
\\setmathfont{{XITS Math}}[range={{cal,bfcal}}]
\\usepackage{{hyperref}}
\\hypersetup{{
    pdftitle={{}},
    hidelinks,
}}
\\usepackage{{tikz,tikz-3dplot,tkz-tab}}
\\usetikzlibrary{{arrows,calc,intersections,patterns,angles,shapes.geometric,arrows.meta,shapes.symbols, quotes, decorations.pathmorphing,backgrounds}}
\\usepackage{{fontawesome5}}
\\usepackage{{setspace}}
\\newcommand{{\\hoac}}[1]{{\\left[\\begin{{aligned}}#1\\end{{aligned}}\\right.}}
\\newcommand{{\\heva}}[1]{{\\left\\{{\\begin{{aligned}}#1\\end{{aligned}}\\right.}}
\\tikzset{{arrow style/.append style = {{>={{Stealth[length=8pt, width=6pt]}}}}}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\footrulewidth}}{{0pt}}
\\usepackage{{scrextend}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\sloppy
\\usepackage{{xcolor}}
\\setlength{{\\fboxrule}}{{0.75pt}}
\\everymath{{\\displaystyle}}
\\usepackage{{enumitem}}
\\setlist{{noitemsep}}
\\setlist{{nosep}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\multicolsep}}{{0pt}}
\\let\\oldfrac\\frac
\\renewcommand{{\\frac}}[2]{{%
    \\mathchoice
        {{\\oldfrac{{#1}}{{#2}}\\rule[-2ex]{{0pt}}{{0pt}}\\rule{{0pt}}{{3.5ex}}}} 
        {{\\oldfrac{{#1}}{{#2}}\\rule[-2ex]{{0pt}}{{0pt}}\\rule{{0pt}}{{3.5ex}}}}
        {{\\oldfrac{{#1}}{{#2}}}}
        {{\\oldfrac{{#1}}{{#2}}}}
}}
\\usepackage{{ifsym}}
\\renewenvironment{{center}}{{\\par\\centering}}{{\\par}}

\\begin{{document}}
\\begin{{center}}
    \\noindent\\setstretch{{1.2}}{{
      %Trái
      \\begin{{minipage}}[b]{{5cm}}
      \\setstretch{{1.3}}\\centerline{{\\fontsize{{12}}{{0}}\\textbf{{{department}}}}}
      \\centerline{{\\fontsize{{12}}{{0}} $\\overline{{\\text{{{exam_type}}}}}$}}
      \\setstretch{{1.1}}\\centerline{{\\fontsize{{12}}{{0}}\\textit{{(Đề thi có 0\\pageref{{mylt}} trang)}}}}
      \\end{{minipage}}\\hspace{{1cm}}
      %Phải
      \\begin{{minipage}}[b]{{12cm}}
      \\setstretch{{1.2}}\\centerline{{\\fontsize{{12}}{{0}}\\textbf{{{exam_title}}}}}
      \\centerline{{\\fontsize{{12}}{{0}}\\textbf{{Môn thi: {subject}}}}}
      \\centerline{{\\fontsize{{12}}{{0}}\\textit{{Thời gian \\underline{{làm bài: {duration} phút, không kể thời gian}} phát đề}}}}
      \\end{{minipage}}\\\\
      %Họ tên
      \\begin{{minipage}}[b]{{11cm}}
      \\vspace{{12pt}}\\textbf{{Họ, tên thí sinh: }}{{\\small\\dotfill}}\\\\
      \\textbf{{Số báo danh: }}{{\\small\\dotfill}}
      \\end{{minipage}}\\hfill
      %Mã đề
      \\begin{{minipage}}[b]{{6.5cm}}
      \\flushright\\fbox{{\\bf \\hspace{{1cm}} Mã đề: {code} \\hspace{{1cm}}}}
      \\vspace{{0.25cm}}
      \\end{{minipage}}\\hfill\\\\
    }}
\\end{{center}}
\\rfoot{{Trang \\thepage/\\pageref{{mylt}} - Mã đề thi {code}}}
\\setstretch{{1.15}}
"""
        if general_info:
            gi_lines = general_info.strip().split('\n')
            gi_tex = '\n\n'.join(f"\\noindent\\textit{{{line.strip()}}}" for line in gi_lines if line.strip())
            header_tex += f"{gi_tex}\n\\vspace{{0.5cm}}\n"
        lines.append(header_tex)
    
    # Map questions by ID
    q_map = {q['id']: q for q in questions}
    
    # Process them in logical groups (single or stimulus)
    processed_ids = set()
    
    # Track section headers printed
    printed_mc = False
    printed_tf = False
    printed_sa = False
    printed_oe = False
    
    for q in questions:
        if q['id'] in processed_ids:
            continue
            
        q_type = q.get('question_type')
        if q_type == 'mc' and not printed_mc:
            lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN I. Câu trắc nghiệm nhiều phương án lựa chọn. Thí sinh trả lời từ câu 1 đến câu {total_mc}. Mỗi câu hỏi thí sinh chỉ chọn một phương án.}}\\par\n\\setcounter{{ex}}{{0}}")
            printed_mc = True
        elif q_type == 'tf' and not printed_tf:
            lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN II. Câu trắc nghiệm đúng sai. Thí sinh trả lời từ câu 1 đến câu {total_tf}. Trong mỗi ý a), b), c), d) ở mỗi câu hỏi, thí sinh chọn đúng hoặc sai.}}\\par\n\\setcounter{{ex}}{{0}}")
            printed_tf = True
        elif q_type == 'sa' and not printed_sa:
            lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN III. Câu trắc nghiệm trả lời ngắn. Thí sinh trả lời từ câu 1 đến câu {total_sa}.}}\\par\n\\setcounter{{ex}}{{0}}")
            printed_sa = True
        elif q_type == 'oe' and not printed_oe:
            lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN IV. Câu tự luận. Thí sinh trả lời từ câu 1 đến câu {total_oe}.}}\\par\n\\setcounter{{ex}}{{0}}")
            printed_oe = True
            
        # Also handle stimulus type which can contain MC/TF/SA
        if q_type == 'st':
            children = [c for c in questions if c.get('parent_id') == q['id']]
            if children:
                child_type = children[0].get('question_type')
                if child_type == 'mc' and not printed_mc:
                    lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN I. Câu trắc nghiệm nhiều phương án lựa chọn. Thí sinh trả lời từ câu 1 đến câu {total_mc}. Mỗi câu hỏi thí sinh chỉ chọn một phương án.}}\\par\n\\setcounter{{ex}}{{0}}")
                    printed_mc = True
                elif child_type == 'tf' and not printed_tf:
                    lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN II. Câu trắc nghiệm đúng sai. Thí sinh trả lời từ câu 1 đến câu {total_tf}. Trong mỗi ý a), b), c), d) ở mỗi câu hỏi, thí sinh chọn đúng hoặc sai.}}\\par\n\\setcounter{{ex}}{{0}}")
                    printed_tf = True
                elif child_type == 'sa' and not printed_sa:
                    lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN III. Câu trắc nghiệm trả lời ngắn. Thí sinh trả lời từ câu 1 đến câu {total_sa}.}}\\par\n\\setcounter{{ex}}{{0}}")
                    printed_sa = True
                elif child_type == 'oe' and not printed_oe:
                    lines.append(f"\\par\\addvspace{{5pt}}\\noindent\\textbf{{PHẦN IV. Câu tự luận. Thí sinh trả lời từ câu 1 đến câu {total_oe}.}}\\par\n\\setcounter{{ex}}{{0}}")
                    printed_oe = True

            if use_minipage: lines.append("\\par\\noindent\\begin{minipage}{\\linewidth}")
            lines.append("\\begin{ex}")
            content = replace_img_with_tikz(q, "", for_pdf_compilation)
            lines.append(f"\\sochc{{{len(children)}}}{{{content}}}")
            
            for child in children:
                lines.append("    \\begin{chc}")
                options_tex, solution_tex = render_options_and_solution_latex(child, include_solution, for_pdf_compilation)
                lines.append("        " + replace_img_with_tikz(child, options_tex, for_pdf_compilation))
                if solution_tex:
                    lines.append("        " + solution_tex)
                lines.append("    \\end{chc}")
                processed_ids.add(child['id'])
                
            lines.append("\\end{ex}\n")
            if use_minipage: lines.append("\\end{minipage}\\par\\vspace{1ex}\n")
            processed_ids.add(q['id'])
            
        elif not q.get('parent_id'): # single question
            if use_minipage: lines.append("\\par\\noindent\\begin{minipage}{\\linewidth}")
            lines.append("\\begin{ex}")
            options_tex, solution_tex = render_options_and_solution_latex(q, include_solution, for_pdf_compilation)
            lines.append("    " + replace_img_with_tikz(q, options_tex, for_pdf_compilation))
            if solution_tex:
                lines.append("    " + solution_tex)
            lines.append("\\end{ex}\n")
            if use_minipage: lines.append("\\end{minipage}\\par\\vspace{1ex}\n")
            processed_ids.add(q['id'])

    if include_header:
        lines.append("\\centerline{\\textbf{-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt- HẾT -\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-\\kern0pt-}}")
        lines.append("\\label{mylt}")
        lines.append("\\end{document}")
    return "\n".join(lines)


import zipfile

def export_latex(contest: dict, questions: list, code: str, exam_title: str, department: str, exam_type: str, subject: str, duration: int, general_info: str, include_solution: bool, zf: zipfile.ZipFile):
    raw_tex = get_raw_latex(
        contest, questions, 
        include_header=False, 
        use_minipage=True if code != "000" else False, 
        exam_title=exam_title, 
        general_info=general_info, 
        code=code, 
        department=department, 
        exam_type=exam_type, 
        subject=subject, 
        duration=duration, 
        include_solution=include_solution
    )
    
    import re
    import os
    
    def repl(m):
        full_match = m.group(0)
        options = m.group(1) or ""
        img_path = m.group(2)
        
        if os.path.exists(img_path):
            basename = os.path.basename(img_path)
            arcname = f"figure/{basename}"
            if arcname not in zf.namelist():
                zf.write(img_path, arcname)
            return f"\\includegraphics{options}{{figure/{basename}}}"
        return full_match
        
    raw_tex = re.sub(r'\\includegraphics(\[.*?\])?\{(.*?)\}', repl, raw_tex)
    
    zf.writestr(f"{code}.tex", raw_tex)
