import streamlit as st
import json
import uuid
import os
import tempfile
import re
import zipfile
import shutil
from logic_manager import run_parser
from curriculum import DATA

# Đường dẫn mặc định nếu chỉ upload file .tex lẻ
source_img_path_default = r"E:\Downloads\Test_latex\extracted_figures"
destination_img_path = r"E:\Downloads\database_question_dataset\Sample\storage"

# --- 1. CẤU HÌNH GIAO DIỆN & CSS (Giữ nguyên) ---
st.set_page_config(page_title="Hệ thống Biên tập Đề thi Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border: 1px solid #ced4da !important;
        border-radius: 12px !important;
        padding: 25px !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        margin-bottom: 2.5rem !important;
    }
    .q-number { color: #0000FF; font-weight: bold; font-size: 1.25rem; }
    .digit-box {
        display: inline-block;
        width: 32px; height: 32px;
        border: 1.5px solid #0000FF;
        text-align: center; line-height: 32px;
        margin-right: 4px; color: #0000FF; font-weight: bold;
    }
    .sol-header { 
        color: #0000FF; font-weight: bold; text-align: center; 
        margin: 20px 0; font-size: 1.1rem; border-top: 1px solid #eee; padding-top: 15px;
    }
    .correct-ans { color: #FF0000; font-weight: bold; }
    table { width: 100% !important; border-collapse: collapse; margin: 15px 0; }
    th, td { border: 1px solid #dee2e6 !important; padding: 10px !important; text-align: center !important; }
    th { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# --- 2. HÀM XỬ LÝ NỘI DUNG & BẢNG (Giữ nguyên các hàm của bạn) ---
def latex_table_to_markdown(latex_text):
    if not latex_text: return ""
    latex_text = re.sub(r'\\begin\{center\}|\\end\{center\}|\\centering', '', latex_text)
    pattern = r'\\begin\{(?:tabular|array)\}(?:\{.*?\})?(.*?)\\end\{(?:tabular|array)\}'
    match = re.search(pattern, latex_text, re.DOTALL)
    if not match: return latex_text
    raw_body = match.group(1).strip()
    raw_body = re.sub(r'\\hline|\\cline\{.*?\}|\\toprule|\\midrule|\\bottomrule', '', raw_body)
    raw_rows = [r.strip() for r in raw_body.split(r'\\') if r.strip()]
    md_table_data = []
    max_cols = 0
    for row in raw_rows:
        raw_cells = row.split('&')
        processed_row_cells = []
        for cell in raw_cells:
            cell = cell.strip()
            mc_match = re.search(r'\\multicolumn\s*\{(\d+)\}\s*\{[^}]*\}\s*\{([^}]*)\}', cell)
            if mc_match:
                n_span = int(mc_match.group(1)); content = mc_match.group(2)
                processed_row_cells.append(content)
                for _ in range(n_span - 1): processed_row_cells.append("")
            else: processed_row_cells.append(cell)
        md_table_data.append(processed_row_cells)
        max_cols = max(max_cols, len(processed_row_cells))
    final_md_rows = []
    for idx, row in enumerate(md_table_data):
        while len(row) < max_cols: row.append("")
        final_md_rows.append("| " + " | ".join(row) + " |")
        if idx == 0: final_md_rows.append("| " + " | ".join(['---'] * max_cols) + " |")
    md_table_str = "\n\n" + "\n".join(final_md_rows) + "\n\n"
    res = re.sub(r'\\begin\{(?:tabular|array)\}(?:\{.*?\})?.*?\\end\{(?:tabular|array)\}', lambda m: md_table_str, latex_text, flags=re.DOTALL)
    return res

def render_content(text):
    if not text: return
    text = text.replace("undefined", r" \\ ")
    text = re.sub(r'\\begin\{center\}|\\end\{center\}|\\centering', '', text)
    try: text = latex_table_to_markdown(text)
    except: pass
    math_blocks = []
    def save_math(match):
        math_blocks.append(match.group(0))
        return f"__MATH_BLOCK_{len(math_blocks)-1}__"
    masked_text = re.sub(r'(\$\$.*?\$\$|\$.*?\$)', save_math, text, flags=re.DOTALL)
    masked_text = masked_text.replace(r"\\", "\n\n")
    for i, block in enumerate(math_blocks):
        masked_text = masked_text.replace(f"__MATH_BLOCK_{i}__", block)
    clean_lines = [line.lstrip() for line in masked_text.split('\n')]
    st.markdown("\n".join(clean_lines))

if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []

def main():
    st.title("Xử lý câu hỏi trước khi đưa vào database")
    
    with st.sidebar:
        st.header("Nhập dữ liệu")
        t_id = st.number_input("ID Giáo viên", value=1)
        sub = st.selectbox("Môn học", list(DATA.keys()))
        grade = st.selectbox("Khối lớp", ["10", "11", "12"], index=2)
        # Metadata mặc định để Apply All
        chaps = list(DATA.get(sub, {}).get(grade, {}).keys())
        chap_side = st.selectbox("Chương mặc định", chaps if chaps else ["-"])
        
        less_list_side = DATA.get(sub, {}).get(grade, {}).get(chap_side, [])
        less_side = st.selectbox("Bài học mặc định", less_list_side if less_list_side else ["-"])
        
        diff_dict = {1: "Nhận biết", 2: "Thông hiểu", 3: "Vận dụng", 4: "Vận dụng cao"}
        comp_side = st.selectbox("Mức độ mặc định", options=[1, 2, 3, 4], format_func=lambda x: diff_dict[x])
        uploaded_file = st.file_uploader(
            "Upload .tex, .zip, or .docx file",
            type=["tex", "zip", "docx"],
        )

        if st.button("NEXT", width='stretch', type="primary"):
            if uploaded_file:
                # Tạo thư mục đích nếu chưa có
                if not os.path.exists(destination_img_path):
                    os.makedirs(destination_img_path)

                # Sử dụng TemporaryDirectory để tự động dọn dẹp sau khi xử lý
                with tempfile.TemporaryDirectory() as tmp_dir:
                    final_tex_path = ""
                    current_source_path = source_img_path_default

                    if uploaded_file.name.endswith(".docx"):
                        # --- DOCX (bao gồm MathType) ---
                        docx_path = os.path.join(tmp_dir, "input.docx")
                        with open(docx_path, "wb") as f:
                            f.write(uploaded_file.getvalue())

                        media_dir = os.path.join(tmp_dir, "media_extract")
                        os.makedirs(media_dir, exist_ok=True)

                        from parse_docx import convert_docx_to_tex

                        n_equations = sum(
                            1 for name in zipfile.ZipFile(docx_path).namelist()
                            if name.startswith("word/media/") and name.endswith(".wmf")
                        )
                        if n_equations:
                            msg = (
                                f"Đang chuyển đổi {n_equations} phương trình MathType "
                                f"sang LaTeX (pix2tex) — có thể mất vài phút…"
                            )
                        else:
                            msg = "Đang xử lý file DOCX…"

                        with st.spinner(msg):
                            final_tex_path = convert_docx_to_tex(docx_path, media_dir)

                        current_source_path = media_dir

                    elif uploaded_file.name.endswith(".zip"):
                        # --- ZIP chứa .tex ---
                        zip_path = os.path.join(tmp_dir, "upload.zip")
                        with open(zip_path, "wb") as f:
                            f.write(uploaded_file.getvalue())

                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(tmp_dir)

                        tex_files = [
                            os.path.join(root, fname)
                            for root, _dirs, files in os.walk(tmp_dir)
                            for fname in files if fname.endswith(".tex")
                        ]

                        if not tex_files:
                            st.error("Không tìm thấy file .tex trong file ZIP.")
                            return

                        final_tex_path = tex_files[0]
                        current_source_path = os.path.dirname(final_tex_path)

                    else:
                        # --- TEX lẻ ---
                        final_tex_path = os.path.join(tmp_dir, "input.tex")
                        with open(final_tex_path, "wb") as f:
                            f.write(uploaded_file.getvalue())

                    # Chạy Parser
                    results = run_parser(
                        final_tex_path,
                        t_id,
                        sub,
                        grade,
                        chap_side,
                        "",
                        1,
                        destination_img_path,
                    )
                    st.session_state.processed_data = results
                    st.rerun()

    # --- PHẦN HIỂN THỊ (Giữ nguyên) ---
        # --- NÚT APPLY CHO TẤT CẢ ---
        st.divider()
        if st.button("Apply for all", width='content'):
            if st.session_state.processed_data:
                for idx, item in enumerate(st.session_state.processed_data):
                    # 1. Cập nhật dữ liệu gốc
                    item['table_question']['chapter'] = chap_side
                    item['table_question']['lesson'] = less_side
                    item['table_question']['complexity'] = comp_side
                    # 2. Cập nhật trạng thái widget (selectbox) bằng key
                    st.session_state[f"ch_{idx}"] = chap_side
                    st.session_state[f"ls_{idx}"] = less_side
                    st.session_state[f"df_{idx}"] = comp_side
                st.success("Đã cập nhật toàn bộ Chương, Bài và Mức độ")
                st.rerun()
            else:
                st.warning("Chưa có dữ liệu để áp dụng.")

    if not st.session_state.processed_data:
        st.info("Tải file LaTeX để bắt đầu")
        return

    q_count = 1
    to_delete = []

    for idx, item in enumerate(st.session_state.processed_data):
        # ... (Toàn bộ phần code hiển thị câu hỏi bên dưới của bạn giữ nguyên 100%)
        q = item['table_question']
        details = item['table_details']['records']
        images = item.get('table_images', [])
        q_type = q['question_type']
        
        edit_key = f"edit_{idx}"
        if edit_key not in st.session_state: st.session_state[edit_key] = False

        with st.container(border=True):
            col_main, col_meta = st.columns([3, 1], gap="large")

            with col_main:
                if q_type == 'st':
                    st.markdown("**Thông tin dùng chung:**")
                else:
                    st.markdown(f'<span class="q-number">Câu {q_count}:</span>', unsafe_allow_html=True)

                if st.session_state[edit_key]:
                    q['content'] = st.text_area("Mã TeX", q['content'], key=f"tx_{idx}", height=150)
                else:
                    render_content(q['content'])

                if images:
                    for img in images:
                        if os.path.exists(img['storage_path']):
                            st.image(img['storage_path'], width=450)

                if q_type == "mc":
                    st.write("")
                    for i, opt in enumerate(details):
                        lbl, is_c = chr(65+i), opt.get('is_correct')
                        if st.session_state[edit_key]:
                            opt['content'] = st.text_input(f"Lựa chọn {lbl}", opt['content'], key=f"mc_{idx}_{i}")
                        else:
                            style = 'class="correct-ans"' if is_c else ""
                            st.markdown(f"**{lbl}.** <span {style}>{opt['content']}</span>", unsafe_allow_html=True)

                elif q_type == "tf":
                    st.write("")
                    for i, opt in enumerate(details):
                        lbl = f"{chr(97+i)})"
                        if st.session_state[edit_key]:
                            c1, c2 = st.columns([4, 1])
                            opt['content'] = c1.text_input(f"Nhận định {lbl}", opt['content'], key=f"tf_{idx}_{i}")
                            opt['is_correct'] = c2.checkbox("Đúng", value=opt.get('is_correct'), key=f"chk_{idx}_{i}")
                            opt['explaination'] = st.text_area(f"Giải thích {lbl}", opt.get('explaination', ''), key=f"tf_exp_{idx}_{i}", height=70)
                        else:
                            style = 'class="correct-ans"' if opt.get('is_correct') else ""
                            st.markdown(f"**{lbl}** <span {style}>{opt['content']}</span>", unsafe_allow_html=True)
                            if opt.get('explaination'):
                                with st.container():
                                    st.markdown(f"*Giải thích {lbl}:*")
                                    render_content(opt['explaination'])
                    q_count += 1

                elif q_type == "sa":
                    st.markdown("**Trả lời ngắn:**")
                    ans = str(details[0]['content']) if details else ""
                    boxes = "".join([f'<div class="digit-box">{c}</div>' for c in ans])
                    boxes += "".join(['<div class="digit-box">&nbsp;</div>' for _ in range(max(0, 4-len(ans)))])
                    st.markdown(boxes, unsafe_allow_html=True)
                    if st.session_state[edit_key]:
                        details[0]['content'] = st.text_input("Sửa đáp số", details[0]['content'], key=f"sa_{idx}")

                if q_type != 'st':
                    st.markdown('<div class="sol-header">Lời giải</div>', unsafe_allow_html=True)
                    if st.session_state[edit_key]:
                        q['solution'] = st.text_area("Mã giải", q['solution'] if q['solution'] else "", key=f"sol_in_{idx}", height=120)
                    else:
                        render_content(q['solution'])

                if st.session_state[edit_key]:
                    if st.button("Save", key=f"sv_{idx}"):
                        st.session_state[edit_key] = False
                        st.rerun()
                else:
                    st.button("Chỉnh sửa", key=f"ed_{idx}", on_click=lambda k=edit_key: st.session_state.update({k: True}))

            with col_meta:
                st.markdown('<div class="meta-box">', unsafe_allow_html=True)
                st.markdown("**Phân loại**")
                ch_list = list(DATA.get(sub, {}).get(grade, {}).keys())
                q['chapter'] = st.selectbox("Chương", ch_list, index=ch_list.index(q['chapter']) if q['chapter'] in ch_list else 0, key=f"ch_{idx}")
                ls_list = DATA.get(sub, {}).get(grade, {}).get(q['chapter'], [])
                q['lesson'] = st.selectbox("Bài", ls_list, index=ls_list.index(q['lesson']) if q['lesson'] in ls_list else 0, key=f"ls_{idx}")
                diff = {1: "Nhận biết", 2: "Thông hiểu", 3: "Vận dụng", 4: "Vận dụng cao"}
                q['complexity'] = st.selectbox("Mức độ", options=[1, 2, 3, 4], format_func=lambda x: diff[x], index=q['complexity']-1 if 1<=q['complexity']<=4 else 0, key=f"df_{idx}")
                st.divider()
                if st.button("Xóa câu hỏi", key=f"dl_{idx}", width='stretch'):
                    to_delete.append(idx)
                st.markdown('</div>', unsafe_allow_html=True)
        if q_type != 'st': q_count += 1

    if to_delete:
        for i in sorted(to_delete, reverse=True): st.session_state.processed_data.pop(i)
        st.rerun()

    st.divider()
    if st.button("XUẤT DỮ LIỆU JSON", type="primary", width='stretch'):
        if st.session_state.processed_data:
            # Vòng lặp cuối cùng để chốt ID và Grade từ sidebar vào data
            for item in st.session_state.processed_data:
                item['table_question']['teacher_id'] = t_id
                item['table_question']['grade'] = int(grade)
                item['table_question']['subject'] = sub

            st.download_button("TẢI JSON", data=json.dumps(st.session_state.processed_data, indent=4, ensure_ascii=False), file_name="export_.json", mime="application/json")
        else:
            st.error("Không có dữ liệu để xuất!")

if __name__ == "__main__":
    main()