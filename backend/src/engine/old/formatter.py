import json
import re
from pathlib import Path


def json_to_raw_tex(json_path, output_input_tex_path):
    json_path = Path(json_path)
    output_input_tex_path = Path(output_input_tex_path)

    with open(json_path, "r", encoding="utf-8") as f:
        pages_data = json.load(f)

    raw_content = []
    for question in pages_data.get("questions", []):
        latex = question.get("latex_code", "")
        processed_latex = re.sub(r'\\n(?![a-zA-Z])', '\n', latex) # Đoạn code này hơi lỗi tí
        raw_content.append(processed_latex)
        raw_content.append("\n")

    # Ghi nội dung thô ra file input.tex
    with open(output_input_tex_path, "w", encoding="utf-8") as f:
        f.write("\n".join(raw_content))
    
    return output_input_tex_path