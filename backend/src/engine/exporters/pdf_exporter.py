import os
import subprocess
import tempfile
import io
import zipfile
from typing import List, Dict, Any
from .latex_exporter import get_raw_latex

def export_pdf(contest: dict, questions: List[dict], code: str, exam_title: str, department: str, exam_type: str, subject: str, duration: int, general_info: str, include_solution: bool, zf: zipfile.ZipFile):
    raw_tex_header = get_raw_latex(
        contest, questions, 
        include_header=True, 
        use_minipage=True if code != "000" else False, 
        exam_title=exam_title, 
        general_info=general_info, 
        code=code, 
        department=department, 
        exam_type=exam_type, 
        subject=subject, 
        duration=duration, 
        include_solution=include_solution,
        for_pdf_compilation=True
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, f"{code}.tex")
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(raw_tex_header)
            
        import shutil
        current_dir = os.path.dirname(__file__)
        extest_path = os.path.join(current_dir, "ex_test.sty")
        if os.path.exists(extest_path):
            shutil.copy(extest_path, os.path.join(tmpdir, "ex_test.sty"))
            
        try:
            compiler = "xelatex"
            # First pass
            proc1 = subprocess.run([compiler, "-interaction=nonstopmode", "-halt-on-error", f"{code}.tex"], cwd=tmpdir, check=False, capture_output=True, text=True, timeout=300)
            if proc1.returncode != 0:
                print(f"PDF compilation with xelatex failed (Code {proc1.returncode}). Trying lualatex...")
                compiler = "lualatex"
                proc1 = subprocess.run([compiler, "-interaction=nonstopmode", "-halt-on-error", f"{code}.tex"], cwd=tmpdir, check=False, capture_output=True, text=True, timeout=300)
                if proc1.returncode != 0:
                    print(f"PDF compilation with lualatex also failed (Code {proc1.returncode}).")
                    print("Last 1000 chars of output:")
                    print(proc1.stdout[-1000:] if proc1.stdout else "No output")
                    return

            # Second pass (for references)
            proc2 = subprocess.run([compiler, "-interaction=nonstopmode", "-halt-on-error", f"{code}.tex"], cwd=tmpdir, check=False, capture_output=True, text=True, timeout=300)
            
            pdf_path = os.path.join(tmpdir, f"{code}.pdf")
            if os.path.exists(pdf_path):
                zf.write(pdf_path, f"{code}.pdf")
        except subprocess.TimeoutExpired as e:
            print(f"PDF error: TimeoutExpired. Compilation took longer than {e.timeout} seconds.")
        except Exception as e:
            print(f"PDF error: {e}")
