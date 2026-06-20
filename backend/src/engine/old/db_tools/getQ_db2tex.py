import psycopg2
import os
from dotenv import load_dotenv
import uuid
from psycopg2.extras import RealDictCursor

load_dotenv()

def connect_to_db():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cur


def get_root_questions(cur, limit=100, subject_id=None, grade=None, chapter=None, lesson=None, difficulty=None):
    query = """
        SELECT *
        FROM questions
        WHERE parent_id IS NULL
    """
    conditions = []
    if subject_id:
        conditions.append(f"subject_id = '{subject_id}'")
    if grade:
        conditions.append(f"grade = '{grade}'")
    if chapter:
        conditions.append(f"chapter = '{chapter}'")
    if lesson:
        conditions.append(f"lesson = '{lesson}'")
    if difficulty:
        conditions.append(f"difficulty = '{difficulty}'")
    if conditions:
        query += " AND " + " AND ".join(conditions)
    query += f" ORDER BY RANDOM() LIMIT {limit}"

    cur.execute(query)
    return cur.fetchall()


def get_child_questions(cur, parent_id):
    if not parent_id:
        return {} # If parent_id is empty, returns an empty dict
    # PSQL supports = ANY(%s) for lists/arrays
    query = """
        SELECT *
        FROM questions
        WHERE parent_id = ANY(%s)
        ORDER BY id
    """
    cur.execute(query, (parent_id,))
    children_raw = cur.fetchall()
    # Fetch all child questions of all parents in one query. Then, group them by parent_id into children_map. Its faster. 

    # Convert results to a dict {parent_id: [child_questions]}
    children_map = {}
    for child in children_raw:
        p_id = child['parent_id'] # parent_id column of the child question in the database
        if p_id not in children_map:
            children_map[p_id] = []
        children_map[p_id].append(child)
    return children_map


def get_answers(cur, question_id):
    if not question_id:
        return {}
    # Select specific columns to avoid unpacking errors
    query = """
        SELECT question_id, content_tex, is_correct, explanation_tex, is_shufflable 
        FROM question_details 
        WHERE question_id = ANY(%s)
        ORDER BY order_index
    """
    cur.execute(query, (question_id,))
    answers_map = {}
    for row in cur.fetchall():
        qid = row['question_id']
        if qid not in answers_map:
            answers_map[qid] = []
        answers_map[qid].append(row)
    return answers_map



def get_questions_by_type(root_questions, question_type): # Except stimulus
    return [q for q in root_questions if q['question_type'] == question_type and q['question_type'] != 'stimulus']


# def generate_exam_from_matrix(cur, matrix_data):



def get_exam_blueprint(cur, question_type, target_count):
    """
    Rút ra danh sách ID 'gốc' (Single hoặc Stimulus) sao cho tổng số câu con = target_count.
    Logic: Ưu tiên chùm (mỗi chùm tính là 2), thiếu thì bù đơn.
    """
    sql = f"""
    WITH Pool AS (
        -- Lấy câu đơn
        SELECT id, 'SINGLE' as unit_type, 1 as weight
        FROM questions 
        WHERE parent_id IS NULL AND question_type = %s
        
        UNION ALL
        
        -- Lấy câu chùm (chỉ lấy những chùm có ít nhất 2 câu con loại này)
        SELECT id, 'STIMULUS' as unit_type, 2 as weight
        FROM questions p
        WHERE question_type = 'stimulus' 
        AND (SELECT COUNT(*) FROM questions WHERE parent_id = p.id AND question_type = %s) >= 2
    ),
    Randomized AS (
        SELECT *, SUM(weight) OVER (ORDER BY RANDOM()) as running_total
        FROM Pool
    )
    SELECT id, unit_type, weight 
    FROM Randomized 
    WHERE running_total <= %s;
    """
    cur.execute(sql, (question_type, question_type, target_count))
    return cur.fetchall()



def export_latex_exam(matrix):
    conn, cur = connect_to_db()
    final_latex = []

    for question_type, total_needed in matrix.items():
        # 1. Lấy "khung" ID từ DB
        blueprint = get_exam_blueprint(cur, question_type, total_needed)
        
        # 2. Với mỗi đơn vị trong khung, lấy nội dung chi tiết
        for unit in blueprint:
            if unit['unit_type'] == 'SINGLE':
                # Lấy nội dung câu đơn
                cur.execute("SELECT * FROM questions WHERE id = %s", (unit['id'],))
                q = cur.fetchone()
                # Lấy đáp án
                cur.execute("SELECT * FROM question_details WHERE question_id = %s ORDER BY order_index", (q['id'],))
                answers = cur.fetchall()
                
                # APPEND LATEX (Gói nội dung vào tag)
                final_latex.append(format_single_latex(q, answers))
                
            else:
                # Lấy nội dung câu chùm
                cur.execute("SELECT * FROM questions WHERE id = %s", (unit['id'],))
                parent = cur.fetchone()
                # Lấy ngẫu nhiên đúng 2 câu con
                cur.execute("SELECT * FROM questions WHERE parent_id = %s AND question_type = %s ORDER BY RANDOM() LIMIT 2", (unit['id'], question_type))
                children = cur.fetchall()
                
                # Với mỗi câu con, lấy đáp án của nó
                child_data = []
                for child in children:
                    cur.execute("SELECT * FROM question_details WHERE question_id = %s ORDER BY order_index", (child['id'],))
                    child_answers = cur.fetchall()
                    child_data.append({'q': child, 'ans': child_answers})
                
                # APPEND LATEX (Gói vào tag \sochc)
                final_latex.append(format_stimulus_latex(parent, child_data))

    cur.close()
    conn.close()
    return "\n\n".join(final_latex)

def format_single_latex(q, answers):
    """Hàm bổ sung các tag LaTeX cho câu đơn"""
    tex = "\\begin{ex}\n"
    # Xử lý immini nếu có ảnh
    if q['layout_type'] == 'immini':
        tex += f"    \\immini[thm]{{{q['content_tex']}}}{{{q['image'] or ''}}}\n"
    else:
        tex += f"    {q['content_tex']}\n"
    
    # Render đáp án dựa trên loại câu
    if q['question_type'] == 'choice':
        tex += "    \\choice\n"
        for a in answers:
            mark = "\\True " if a['is_correct'] else ""
            tex += f"    {{{mark}{a['content_tex']}}}\n"
    elif q['question_type'] == 'choiceTF':
        tex += "    \\choiceTF\n"
        for a in answers:
            mark = "\\True " if a['is_correct'] else ""
            tex += f"    {{{mark}{a['content_tex']}}}\n"
    
    tex += "    \\loigiai{...}\n\\end{ex}"
    return tex

def format_stimulus_latex(parent, child_data):
    """Hàm bổ sung các tag LaTeX cho câu chùm"""
    tex = "\\begin{ex}\n"
    tex += f"\\sochc{{2}}{{{parent['content_tex']}}}\n" # Mặc định 2 câu con
    
    for item in child_data:
        q = item['q']
        ans = item['ans']
        tex += "    \\begin{chc}\n"
        tex += f"        {q['content_tex']}\n"
        # Thêm logic choice/choiceTF cho câu con tương tự như câu đơn ở đây...
        tex += "        \\loigiai{...}\n"
        tex += "    \\end{chc}\n"
    
    tex += "\\end{ex}"
    return tex


def export(output):
    conn, cur = connect_to_db()
    root_questions = get_root_questions(cur, limit=10, subject_id=None, grade=None, chapter=None, lesson=None, difficulty=None)
    if not root_questions:
        print("Error")
        cur.close()
        conn.close()
        exit()
    
    root_ids = [q['id'] for q in root_questions]
    children_map = get_child_questions(cur, root_ids)

    all_question_ids = root_ids + [c['id'] for children in children_map.values() for c in children]
    answers_map = get_answers(cur, all_question_ids)

    choice_questions = get_questions_by_type(root_questions, "choice")
    choiceTF_questions = get_questions_by_type(root_questions, "choiceTF")
    shortans_questions = get_questions_by_type(root_questions, "shortans")
    essay_questions = get_questions_by_type(root_questions, "essay")



    res = ""
    

    # with open(output, "w", encoding="utf-8") as f:

        # f.write(choiceTF_questions)
        # f.write(shortans_questions)
        # f.write(essay_questions)
        # f.close()
    cur.close()
    conn.close()

if __name__ == "__main__":
    # 1. Định nghĩa ma trận đề mong muốn
    my_matrix = {
        "choice": 20,    # 5 câu trắc nghiệm
        "choiceTF": 20,  # 3 câu Đúng/Sai
        "shortans": 20  # 2 câu điền đáp án ngắn
    }
    
    # 2. Gọi hàm thực thi
    result = export_latex_exam(my_matrix)
    
    # 3. Xuất kết quả ra file hoặc màn hình
    with open("Sample/output.tex", "w", encoding="utf-8") as f:
        f.write(result)
        
    print("Đã tạo đề thi thành công vào file output.tex!")
    


# import psycopg2
# import os
# from dotenv import load_dotenv

# load_dotenv()

# def export_to_tex(output_file, limit=10, subject_id=None, grade=None):
#     conn = psycopg2.connect(
#         dbname=os.getenv("DB_NAME"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT")
#     )
#     cur = conn.cursor()
#     # 1. LẤY DANH SÁCH CÂU HỎI GỐC (Parent_id IS NULL)
#     # Bao gồm cả câu đơn và câu Stimulus (cha của nhóm câu hỏi)
#     query = """
#         SELECT id, content_tex, image, solution_tex, layout_type, question_type, is_shufflable
#         FROM public.questions
#         WHERE parent_id IS NULL
#     """
#     conditions = []
#     if subject_id: conditions.append(f"subject_id = '{subject_id}'")
#     if grade: conditions.append(f"grade = {grade}")
#     if conditions: query += " AND " + " AND ".join(conditions)
#     query += f" ORDER BY question_type, RANDOM() LIMIT {limit}"

#     cur.execute(query)
#     root_questions = cur.fetchall()

#     if not root_questions:
#         print("Không có câu hỏi phù hợp")
#         return

#     # Lấy IDs để truy vấn câu hỏi con và đáp án
#     root_ids = [q[0] for q in root_questions]
#     format_root_ids = ",".join([f"'{qid}'" for qid in root_ids])

#     # 2. LẤY CÂU HỎI CON (Cho trường hợp \sochc)
#     cur.execute(f"""
#         SELECT id, parent_id, content_tex, image, solution_tex, layout_type, question_type 
#         FROM public.questions 
#         WHERE parent_id IN ({format_root_ids})
#         ORDER BY parent_id, id
#     """)
#     children_raw = cur.fetchall()
#     children_map = {}
#     all_question_ids = list(root_ids)
#     for c in children_raw:
#         pid = c[1]
#         if pid not in children_map: children_map[pid] = []
#         children_map[pid].append(c)
#         all_question_ids.append(c[0])

#     # 3. LẤY ĐÁP ÁN
#     format_all_ids = ",".join([f"'{qid}'" for qid in all_question_ids])
#     cur.execute(f"""
#         SELECT question_id, content_tex, is_correct, order_index, explanation_tex, is_shufflable
#         FROM public.question_details
#         WHERE question_id IN ({format_all_ids})
#         ORDER BY question_id, order_index
#     """)
#     answers_map = {}
#     for qid, content, is_correct, order, expl, is_shuf in cur.fetchall():
#         if qid not in answers_map: answers_map[qid] = []
#         answers_map[qid].append({
#             'content': content, 
#             'is_correct': is_correct, 
#             'explanation': expl,
#             'is_shufflable': is_shuf
#         })

#     # 4. HÀM PHỤ TRỢ XỬ LÝ NỘI DUNG CÂU HỎI (CHO TỪNG LOẠI)
#     def render_question_content(q_data, options):
#         qid, content, image, solution, layout, question_type = q_data[:6]
#         res = ""
        
#         # Tiền xử lý nội dung có immini
#         main_body = content.strip()
        
#         # Xử lý các loại câu hỏi
#         if question_type == "choice": # Trắc nghiệm
#             opt_str = "\\choice\n"
#             for opt in options:
#                 prefix = "\\True " if opt['is_correct'] else ""
#                 fix = "\\fix " if not opt['is_shufflable'] else ""
#                 opt_str += "{" + prefix + fix + opt['content'].strip() + "}\n"
            
#             if layout == "immini_all":
#                 res += f"\\immini[thm]{{\n{main_body}\n{opt_str}}}{{\n{image}\n}}\n"
#             elif layout == "immini_content":
#                 res += f"\\immini[thm]{{\n{main_body}\n}}{{\n{image}\n}}\n{opt_str}"
#             else:
#                 res += f"{main_body}\n{opt_str}"

#         elif question_type == "choiceTF": # Đúng Sai
#             opt_str = "\\choiceTF\n"
#             for opt in options:
#                 prefix = "\\True " if opt['is_correct'] else ""
#                 opt_str += "{" + prefix + opt['content'].strip() + "}\n"
            
#             # Giải thích đúng sai (itemchoice)
#             expl_str = ""
#             if any(opt['explanation'] for opt in options):
#                 expl_str = "\\begin{itemchoice}\n"
#                 for opt in options:
#                     expl_str += f"\\itemch {opt['explanation'] if opt['explanation'] else ''}\n"
#                 expl_str += "\\end{itemchoice}"

#             if layout == "immini_all":
#                 res += f"\\immini[thm]{{\n{main_body}\n{opt_str}}}{{\n{image}\n}}\n"
#             elif layout == "immini_content":
#                 res += f"\\immini[thm]{{\n{main_body}\n}}{{\n{image}\n}}\n{opt_str}"
#             else:
#                 res += f"{main_body}\n{opt_str}"
            
#             # Lời giải cho Đúng/Sai
#             full_sol = solution.strip() if solution else ""
#             if expl_str:
#                 full_sol = (full_sol + "\n" + expl_str).strip()
#             solution = full_sol # Cập nhật lại để dùng chung phần loigiai phía dưới

#         elif question_type == "shortans": # Trả lời ngắn
#             ans_val = options[0]['content'] if options else ""
#             ans_str = f"\\shortans{{{ans_val}}}\n"
#             if layout in ["immini_all", "immini_content"]:
#                 res += f"\\immini[thm]{{\n{main_body}\n}}{{\n{image}\n}}\n{ans_str}"
#             else:
#                 res += f"{main_body}\n{ans_str}"

#         elif question_type == "essay": # Tự luận (essay)
#             if layout in ["immini_all", "immini_content"]:
#                 res += f"\\immini[thm]{{\n{main_body}\n}}{{\n{image}\n}}\n"
#             else:
#                 res += f"{main_body}\n"
#         else:
#             if layout in ["immini_all", "immini_content"]:
#                 res += "\\vspace{-17.5pt}\n" 
#                 res += f"\\immini[]{{\n{main_body}\n}}{{\n{image}\n}}\n"
#             else:
#                 res += f"{main_body}\n"

#         if solution and question_type != "choiceTF": # loigiai được xử lý chung
#             res += f"\\loigiai{{{solution.strip()}}}\n"
        
#         return res

#     # 5. GHI FILE
#     with open(output_file, "w", encoding="utf-8") as f:
#         for q in root_questions:
#             qid, content, image, solution, layout, question_type, is_shuf = q
            
#             f.write("\\begin{ex}\n")
            
#             if question_type == "stimulus": # Câu hỏi chùm
#                 children = children_map.get(qid, [])
#                 # Viết stimulus dẫn
#                 stim_text = content.strip()
#                 if image:
#                     f.write(f"\\sochc{{{len(children)}}}{{\\immini[]{{{stim_text}}}{{{image.strip()}}}\n}}\n")
#                 else:
#                     f.write(f"\\sochc{{{len(children)}}}{{{stim_text}\n}}\n")
                
#                 # Viết các câu con
#                 for child in children:
#                     f.write("    \\begin{chc}\n")
#                     child_opts = answers_map.get(child[0], [])
#                     # Render nội dung câu con (bỏ ex/end ex)
#                     f.write(render_question_content(child, child_opts))
#                     f.write("    \\end{chc}\n")
#             else:
#                 # Câu hỏi đơn
#                 opts = answers_map.get(qid, [])
#                 f.write(render_question_content(q, opts))

#             f.write("\\end{ex}\n\n")

#     cur.close()
#     conn.close()
#     print(f"Đã xuất thành công {len(root_questions)} câu hỏi vào {output_file}")

# # Chạy thử
# if __name__ == "__main__":
#     export_to_tex("Sample/output.tex", limit=30)
