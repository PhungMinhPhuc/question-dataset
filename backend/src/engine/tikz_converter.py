import os
import subprocess
import tempfile
import shutil

def tikz_to_svg(tikz_code, output_path):
    latex_template = r"""
\documentclass[tikz, border=2pt]{standalone}
\usepackage{amsmath,amssymb,fancyhdr}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\usepackage{unicode-math}
\setmathfont{Cambria Math}
\setmathrm{Cambria Math}
\usepackage{tikz,tikz-3dplot,tkz-tab}
\usetikzlibrary{arrows,calc,intersections,patterns,angles,shapes.geometric,arrows.meta,shapes.symbols,quotes,decorations.markings,decorations.pathmorphing}
\usepackage{graphicx}
\usepackage{fontawesome5}
\usepackage{setspace}
\tikzset{arrow style/.append style = {>={Stealth[length=8pt, width=6pt]}}}
\usepackage{scrextend}
\sloppy
\usepackage{xcolor}
\setlength{\fboxrule}{0.75pt}
\renewenvironment{center}{\par\centering}{\par}
\usepackage{ifsym}

% Custom macros from user
\newcommand{\hoac}[1]{\left[\begin{aligned}#1\end{aligned}\right.}
\newcommand{\heva}[1]{\left\{\begin{aligned}#1\end{aligned}\right.}
\everymath{\displaystyle}

\begin{document}
""" + tikz_code + r"""
\end{document}
"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "tikz2svg_temp.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_template)

        try:
            subprocess.run([
                    "xelatex", "-interaction=nonstopmode", "tikz2svg_temp.tex"],
                cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            pdf_file = os.path.join(tmpdir, "tikz2svg_temp.pdf")
            if os.path.exists(pdf_file):
                subprocess.run(
                    ["pdftocairo", 
                     "-svg", 
                     "tikz2svg_temp.pdf", 
                     "tikz2svg_temp.svg"],
                    cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                
                svg_temp_path = os.path.join(tmpdir, "tikz2svg_temp.svg")
                if os.path.exists(svg_temp_path):
                    shutil.copy2(svg_temp_path, output_path)
                    return True
        except Exception as e:
            print(f"TikZ_Error: {e}")
            
    return False