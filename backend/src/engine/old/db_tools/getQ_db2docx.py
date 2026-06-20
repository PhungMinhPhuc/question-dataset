import psycopg2
import subprocess
import os
import re
from pdf2image import convert_from_path
from dotenv import load_dotenv

OUTPUT_DIR = "Sample/build"
os.makedirs(OUTPUT_DIR, exist_ok=True)

load_dotenv()  # load file .env

# 1. EXPORT LATEX
def export_to_tex(limit=10):
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()

    # Lấy câu hỏi
    cur.execute(f"""
        SELECT id, content_tex, image, solution_tex
        FROM public.questions
        ORDER BY RANDOM()
        LIMIT {limit}
    """)
    questions = cur.fetchall()

    # Lấy đáp án
    ids = [f"'{q[0]}'" for q in questions]
    id_str = ",".join(ids)
    cur.execute(f"""
        SELECT question_id, content_tex, is_correct, order_index
        FROM public.question_details
        WHERE question_id IN ({id_str})
        ORDER BY question_id, order_index
    """)
    answers_raw = cur.fetchall()
    answers_map = {}
    for qid, content, correct, order in answers_raw:
        answers_map.setdefault(qid, []).append((content, correct))

    tex_path = os.path.join(OUTPUT_DIR, "output.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("\\begin{document}\n\n")

        for i, q in enumerate(questions, 1):
            qid, content, image, solution = q
            opts = answers_map.get(qid, [])

            f.write(f"\\textbf{{Câu {i}:}} {content}\n\n")

            if image:
                f.write(image + "\n\n")

            # đáp án
            for idx, (opt, correct) in enumerate(opts):
                label = chr(65 + idx)
                prefix = f"\\textbf{{{label}}}"
                if correct:
                    prefix = f"\\underline{prefix}"
                f.write(f"{prefix}\\textbf{{.}} {opt}\n\n")

            # lời giải
            if solution:
                f.write("\\centerline{\\textbf{Lời giải}}\n\n " + solution + "\n\n")

        f.write("\\end{document}")

    cur.close()
    conn.close()
    return tex_path


# 2. TikZ → PDF → PNG
def convert_tikz_to_png(tex_path):
    with open(tex_path, "r", encoding="utf-8") as f:
        content = f.read()

    tikz_blocks = re.findall(
        r'\\begin{tikzpicture}.*?\\end{tikzpicture}',
        content,
        re.DOTALL
    )

    for i, tikz in enumerate(tikz_blocks):
        tex_file = os.path.join(OUTPUT_DIR, f"tikz_{i}.tex")
        pdf_file = os.path.join(OUTPUT_DIR, f"tikz_{i}.pdf")
        png_file = os.path.join(OUTPUT_DIR, f"tikz_{i}.png")

        # Tạo standalone TikZ
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(r"""
\documentclass{standalone}
\usepackage{amsmath,amssymb,fancyhdr}
\usepackage[utf8]{vietnam} 
\usepackage{hyperref}
\hypersetup{
    pdftitle={_},
    pdfauthor={Phùng Minh Phúc},
    pdfproducer={Microsoft Print to PDF},
    hidelinks,
}
\usepackage{tikz,tikz-3dplot,tkz-tab}
\usetikzlibrary{arrows,calc,intersections,patterns,angles,shapes.geometric,arrows.meta,shapes.symbols, quotes, decorations.markings}
\usetikzlibrary{calc,patterns}
\usepackage{graphicx}
\graphicspath{ {./extracted_images/} }
\usepackage{fontawesome5}
\usepackage{setspace}
\tikzset{arrow style/.append style = {>={Stealth[length=8pt, width=6pt]}}}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\usepackage{scrextend}
\pagestyle{fancy}
\fancyhf{}
\sloppy
\usepackage{xcolor}
% \color{black}
\setlength{\fboxrule}{0.75pt}
% \renewcommand{\baselinestretch}{1.1}
\renewenvironment{center}{\par\centering}{\par}
\usepackage{ifsym}
\begin{document}
""" + tikz + r"""
\end{document}
""")

        # Compile PDF
        subprocess.run([
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", OUTPUT_DIR,
            tex_file
        ], stdout=subprocess.DEVNULL)

        # PDF → PNG (300 dpi)
        images = convert_from_path(pdf_file, dpi=300)
        images[0].save(png_file, "PNG")

        # Replace TikZ bằng PNG
        content = content.replace(
            tikz,
            f"\\includegraphics[width=0.4\\textwidth]{{{png_file.replace(os.sep, '/')}}}"
        )

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(content)

    return tex_path


# 3. TEX → DOCX
def convert_to_docx(tex_path):
    docx_path = tex_path.replace(".tex", ".docx")
    pandoc_exe = r"E:/Python/Pandoc/pandoc.exe"  # đường dẫn pandoc

    cmd = [
        pandoc_exe,
        tex_path,
        "-o", docx_path,
        "--mathml"
    ]
    reference_docx = r"Sample/template.docx"
    if reference_docx:
        cmd.extend(["--reference-doc", reference_docx])
    
    subprocess.run(cmd)
    return docx_path


# 4. MAIN
def run(limit=50):
    print("Export LaTeX...")
    tex = export_to_tex(limit)

    print("Convert TikZ → PNG...")
    tex = convert_tikz_to_png(tex)

    print("Convert → Word...")
    docx = convert_to_docx(tex)

    print(f"DONE: {docx}")
    print("Mở Word, công thức là Word Equation. Nếu muốn MathType, chạy macro MathType Convert All.")


if __name__ == "__main__":
    run(20)