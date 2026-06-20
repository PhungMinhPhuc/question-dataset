import os
from fastapi import APIRouter, Query, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from typing import Optional
from db import get_cursor
from auth import get_current_teacher, get_current_user
from models import QuestionUpdateRequest

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("")
def list_questions(
    subject: Optional[str] = Query(None),
    grade: Optional[int] = Query(None),
    chapter: Optional[str] = Query(None),
    lesson: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    complexity: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    conditions = ["q.deleted_at IS NULL", "q.parent_id IS NULL"]
    params = []

    # Teacher chỉ xem câu hỏi của mình; admin xem tất
    if current_user.get("role") == "teacher":
        conditions.append("q.teacher_id = %s")
        params.append(current_user["user_id"])

    if subject:
        conditions.append("q.subject = %s")
        params.append(subject)
    if grade:
        conditions.append("q.grade = %s")
        params.append(grade)
    if chapter:
        conditions.append("q.chapter = %s")
        params.append(chapter)
    if lesson:
        conditions.append("q.lesson = %s")
        params.append(lesson)
    if question_type:
        if question_type == 'st':
            conditions.append("q.question_type = 'st'")
        else:
            conditions.append("(q.question_type = %s OR (q.question_type = 'st' AND EXISTS (SELECT 1 FROM questions child WHERE child.parent_id = q.id AND child.question_type = %s)))")
            params.extend([question_type, question_type])
    if complexity:
        conditions.append("q.complexity = %s")
        params.append(complexity)
    if search:
        if search.isdigit():
            conditions.append("(q.content ILIKE %s OR q.id = %s OR EXISTS (SELECT 1 FROM questions child WHERE child.parent_id = q.id AND child.content ILIKE %s))")
            params.extend([f"%{search}%", int(search), f"%{search}%"])
        else:
            conditions.append("(q.content ILIKE %s OR EXISTS (SELECT 1 FROM questions child WHERE child.parent_id = q.id AND child.content ILIKE %s))")
            params.extend([f"%{search}%", f"%{search}%"])

    where_clause = " AND ".join(conditions)
    offset = (page - 1) * page_size

    with get_cursor() as (cur, conn):
        # Đếm tổng mục (top-level)
        cur.execute(f"SELECT COUNT(*) as total FROM questions q WHERE {where_clause}", params)
        total = cur.fetchone()["total"]

        # Đếm tổng số câu hỏi thực tế (đếm con nếu là st, đếm 1 nếu là câu đơn)
        cur.execute(f"""
            SELECT COALESCE(SUM(
                CASE 
                    WHEN q.question_type = 'st' THEN (SELECT COUNT(*) FROM questions child WHERE child.parent_id = q.id AND child.deleted_at IS NULL)
                    ELSE 1
                END
            ), 0) as total_questions
            FROM questions q WHERE {where_clause}
        """, params)
        total_questions = cur.fetchone()["total_questions"]

        # Lấy dữ liệu với phân trang
        cur.execute(
            f"""
            SELECT q.id, q.public_id, q.subject, q.grade, q.parent_id,
                   q.question_type, q.layout_type, q.content, q.solution,
                   q.chapter, q.lesson, q.complexity, q.is_shufflable,
                   t.name as teacher_name
            FROM questions q
            LEFT JOIN accounts t ON q.teacher_id = t.id
            WHERE {where_clause}
            ORDER BY q.id DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset]
        )
        questions = [dict(row) for row in cur.fetchall()]

        if questions:
            q_ids = tuple(q["id"] for q in questions)
            
            # Map id -> object for fast lookup (will include children soon)
            q_map = {q["id"]: q for q in questions}

            # Lấy children cho st
            cur.execute(
                """
                SELECT id, parent_id, question_type, content, solution, complexity, subject, grade, chapter 
                FROM questions 
                WHERE parent_id IN %s
                ORDER BY id ASC
                """, 
                (q_ids,)
            )
            children = cur.fetchall()
            child_ids = []
            for child in children:
                c_dict = dict(child)
                child_ids.append(c_dict["id"])
                q_map[c_dict["id"]] = c_dict
                
                parent = q_map.get(c_dict["parent_id"])
                if parent:
                    if "children" not in parent: parent["children"] = []
                    parent["children"].append(c_dict)

            all_q_ids = tuple(list(q_ids) + child_ids)

            if all_q_ids:
                # Lấy images
                cur.execute("SELECT question_id, storage_path, img_scale FROM q_images WHERE question_id IN %s", (all_q_ids,))
                for img in cur.fetchall():
                    q = q_map.get(img["question_id"])
                    if q:
                        if "images" not in q: q["images"] = []
                        q["images"].append(dict(img))

                # Lấy mc options
                cur.execute("SELECT id, question_id, content, is_correct FROM q_choice_details WHERE question_id IN %s", (all_q_ids,))
                for opt in cur.fetchall():
                    q = q_map.get(opt["question_id"])
                    if q:
                        if "options" not in q: q["options"] = []
                        q["options"].append(dict(opt))

                # Lấy tf options
                cur.execute("SELECT id, question_id, content, is_correct, order_index, explaination FROM q_truefalse_details WHERE question_id IN %s ORDER BY order_index", (all_q_ids,))
                for opt in cur.fetchall():
                    q = q_map.get(opt["question_id"])
                    if q:
                        if "options" not in q: q["options"] = []
                        q["options"].append(dict(opt))

                # Lấy sa options
                cur.execute("SELECT question_id, content FROM q_shortans_details WHERE question_id IN %s", (all_q_ids,))
                for sa in cur.fetchall():
                    q = q_map.get(sa["question_id"])
                    if q:
                        if "options" not in q: q["options"] = []
                        q["options"].append(dict(sa))

    return {
        "total": total,
        "total_questions": total_questions,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "data": questions
    }


@router.get("/metadata/filters")
def get_metadata_filters(current_user: dict = Depends(get_current_teacher)):
    """Lấy danh sách chapter, lesson hiện có của giáo viên để làm gợi ý tự động điền"""
    with get_cursor() as (cur, conn):
        cur.execute(
            "SELECT DISTINCT chapter FROM questions WHERE teacher_id = %s AND deleted_at IS NULL AND chapter IS NOT NULL AND chapter != ''",
            (current_user["user_id"],)
        )
        chapters = [r["chapter"] for r in cur.fetchall()]
        
        cur.execute(
            "SELECT DISTINCT lesson FROM questions WHERE teacher_id = %s AND deleted_at IS NULL AND lesson IS NOT NULL AND lesson != ''",
            (current_user["user_id"],)
        )
        lessons = [r["lesson"] for r in cur.fetchall()]
        
    return {"chapters": chapters, "lessons": lessons}

@router.get("/subjects/list")
def get_subjects():
    """Trả danh sách môn học & chương/bài từ curriculum.py"""
    import sys, os
    engine_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "src", "engine")
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)
    from data.curriculum import DATA
    return DATA

@router.get("/{question_id}")
def get_question(question_id: int, current_user: dict = Depends(get_current_user)):
    with get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT q.*, t.name as teacher_name
            FROM questions q
            LEFT JOIN accounts t ON q.teacher_id = t.id
            WHERE q.id = %s AND q.deleted_at IS NULL
            """,
            (question_id,)
        )
        question = cur.fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="Câu hỏi không tồn tại")

        question = dict(question)

        # Lấy images
        cur.execute("SELECT * FROM q_images WHERE question_id = %s", (question_id,))
        question["images"] = [dict(r) for r in cur.fetchall()]

        # Lấy details theo loại
        q_type = question["question_type"]
        if q_type == "mc":
            cur.execute(
                "SELECT * FROM q_choice_details WHERE question_id = %s ORDER BY order_index",
                (question_id,)
            )
            question["details"] = [dict(r) for r in cur.fetchall()]
        elif q_type == "tf":
            cur.execute(
                "SELECT * FROM q_truefalse_details WHERE question_id = %s ORDER BY order_index",
                (question_id,)
            )
            question["details"] = [dict(r) for r in cur.fetchall()]
        elif q_type == "sa":
            cur.execute(
                "SELECT * FROM q_shortans_details WHERE question_id = %s",
                (question_id,)
            )
            question["details"] = [dict(r) for r in cur.fetchall()]
        else:
            question["details"] = []

        # Nếu là câu stimulus, lấy câu con
        if q_type == "st":
            cur.execute(
                "SELECT * FROM questions WHERE parent_id = %s AND deleted_at IS NULL ORDER BY id ASC",
                (question_id,)
            )
            children = [dict(r) for r in cur.fetchall()]
            
            if children:
                c_ids = tuple(c["id"] for c in children)
                
                # Hàm lấy details cho children
                def attach_details(c_list, c_ids_tuple):
                    # MC
                    cur.execute("SELECT * FROM q_choice_details WHERE question_id IN %s ORDER BY order_index", (c_ids_tuple,))
                    for opt in cur.fetchall():
                        c = next((x for x in c_list if x["id"] == opt["question_id"]), None)
                        if c:
                            if "details" not in c: c["details"] = []
                            c["details"].append(dict(opt))
                    
                    # TF
                    cur.execute("SELECT * FROM q_truefalse_details WHERE question_id IN %s ORDER BY order_index", (c_ids_tuple,))
                    for opt in cur.fetchall():
                        c = next((x for x in c_list if x["id"] == opt["question_id"]), None)
                        if c:
                            if "details" not in c: c["details"] = []
                            c["details"].append(dict(opt))
                    
                    # SA
                    cur.execute("SELECT * FROM q_shortans_details WHERE question_id IN %s", (c_ids_tuple,))
                    for opt in cur.fetchall():
                        c = next((x for x in c_list if x["id"] == opt["question_id"]), None)
                        if c:
                            if "details" not in c: c["details"] = []
                            c["details"].append(dict(opt))
                
                attach_details(children, c_ids)

            question["children"] = children

    return question


def regrade_question_submissions(question_id: int):
    """
    Chấm lại điểm cho tất cả bài làm liên quan đến câu hỏi này
    do đáp án/nội dung có thể đã thay đổi.
    """
    with get_cursor() as (cur, conn):
        # 1. Lấy thông tin cơ bản và đáp án đúng mới của câu hỏi
        cur.execute("SELECT question_type FROM questions WHERE id = %s", (question_id,))
        row = cur.fetchone()
        if not row:
            return
        q_type = row["question_type"]

        correct_content = ""
        correct_tf_str = ""
        
        if q_type == "mc":
            cur.execute("SELECT content FROM q_choice_details WHERE question_id = %s AND is_correct = true", (question_id,))
            correct_row = cur.fetchone()
            correct_content = correct_row["content"] if correct_row else ""
        elif q_type == "tf":
            cur.execute("SELECT order_index, is_correct FROM q_truefalse_details WHERE question_id = %s ORDER BY order_index", (question_id,))
            statements = cur.fetchall()
            correct_tf_str = "".join("T" if s["is_correct"] else "F" for s in statements)
        elif q_type == "sa":
            cur.execute("SELECT content FROM q_shortans_details WHERE question_id = %s", (question_id,))
            correct_row = cur.fetchone()
            correct_content = correct_row["content"] if correct_row else ""

        # 2. Tìm tất cả các submissions liên quan đến câu hỏi này
        cur.execute(
            """
            SELECT sos.id as submission_id, sos.student_choice, sos.contest_result_id,
                   cq.point_weight
            FROM student_option_submissions sos
            JOIN contest_results cr ON cr.id = sos.contest_result_id
            JOIN contests_questions cq ON cq.contest_id = cr.contest_id AND cq.question_id = sos.question_id
            WHERE sos.question_id = %s
            """,
            (question_id,)
        )
        submissions = cur.fetchall()

        affected_result_ids = set()

        # 3. Đánh giá lại điểm cho từng submission
        for sub in submissions:
            sub_id = sub["submission_id"]
            student_choice = sub["student_choice"] or ""
            weight = float(sub["point_weight"] or 1.0)
            earned = 0.0
            is_correct = False

            if q_type == "mc":
                is_correct = (student_choice.strip() == correct_content.strip())
                earned = weight if is_correct else 0.0
            elif q_type == "tf":
                match_count = sum(1 for a, b in zip(student_choice, correct_tf_str) if a == b)
                if len(correct_tf_str) > 0:
                    ratio = match_count / len(correct_tf_str)
                    earned = round(weight * ratio, 4)
                    is_correct = (match_count == len(correct_tf_str))
            elif q_type == "sa":
                is_correct = (student_choice.strip().lower() == correct_content.strip().lower())
                earned = weight if is_correct else 0.0

            cur.execute(
                """
                UPDATE student_option_submissions
                SET is_correct = %s, earned_point = %s
                WHERE id = %s
                """,
                (is_correct, earned, sub_id)
            )
            affected_result_ids.add(sub["contest_result_id"])

        # 4. Tính toán lại tổng điểm cho các bài làm bị ảnh hưởng
        if affected_result_ids:
            for result_id in affected_result_ids:
                cur.execute(
                    """
                    SELECT 
                        COALESCE(SUM(sos.earned_point), 0) as new_total,
                        COUNT(CASE WHEN sos.is_correct = false AND q.question_type IN ('mc', 'tf', 'sa') THEN 1 END) as new_wrong
                    FROM student_option_submissions sos
                    JOIN questions q ON q.id = sos.question_id
                    WHERE sos.contest_result_id = %s
                    """,
                    (result_id,)
                )
                agg = cur.fetchone()
                cur.execute(
                    """
                    UPDATE contest_results
                    SET total_score = %s, count_wrong_answers = %s
                    WHERE id = %s
                    """,
                    (agg["new_total"], agg["new_wrong"], result_id)
                )

        conn.commit()


@router.patch("/{question_id}")
def update_question(
    question_id: int,
    body: QuestionUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_teacher),
):
    updates = {k: v for k, v in body.dict(exclude={"details"}).items() if v is not None}

    with get_cursor() as (cur, conn):
        cur.execute("SELECT question_type FROM questions WHERE id = %s AND teacher_id = %s", (question_id, current_user["user_id"]))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Câu hỏi không tồn tại hoặc không có quyền")
        q_type = row["question_type"]

        if updates:
            set_clause = ", ".join(f"{k} = %s" for k in updates)
            values = list(updates.values()) + [question_id]
            cur.execute(
                f"UPDATE questions SET {set_clause} WHERE id = %s",
                values
            )

        if body.details:
            table_name = None
            if q_type == "mc": table_name = "q_choice_details"
            elif q_type == "tf": table_name = "q_truefalse_details"
            elif q_type == "sa": table_name = "q_shortans_details"
            
            if table_name:
                for det in body.details:
                    det_updates = {k: v for k, v in det.dict(exclude={"id"}).items() if v is not None}
                    if det_updates:
                        d_set_clause = ", ".join(f"{k} = %s" for k in det_updates)
                        d_values = list(det_updates.values()) + [det.id, question_id]
                        cur.execute(
                            f"UPDATE {table_name} SET {d_set_clause} WHERE id = %s AND question_id = %s",
                            d_values
                        )

        conn.commit()

    background_tasks.add_task(regrade_question_submissions, question_id)

    return {"message": "Cập nhật thành công"}


@router.delete("/all")
def delete_all_questions(
    current_user: dict = Depends(get_current_teacher),
):
    """Soft-delete every question owned by the current teacher (parents and children).

    Declared BEFORE the /{question_id} route on purpose: FastAPI matches routes in
    order, and "all" would otherwise be captured by /{question_id} and fail int
    validation. Uses the same soft-delete (deleted_at) as single deletion so existing
    contests keep working and nothing is physically removed.
    """
    with get_cursor() as (cur, conn):
        cur.execute(
            "UPDATE questions SET deleted_at = NOW() WHERE teacher_id = %s AND deleted_at IS NULL",
            (current_user["user_id"],),
        )
        count = cur.rowcount
        conn.commit()
    return {"message": f"Đã xóa {count} câu hỏi", "count": count}


@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    current_user: dict = Depends(get_current_teacher),
):
    with get_cursor() as (cur, conn):
        cur.execute(
            "UPDATE questions SET deleted_at = NOW() WHERE id = %s AND teacher_id = %s",
            (question_id, current_user["user_id"])
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Câu hỏi không tồn tại hoặc không có quyền")
        conn.commit()
    return {"message": "Đã xóa câu hỏi"}


@router.post("/images/edit")
async def edit_image(
    img_path: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    img_storage = os.path.abspath(os.getenv("IMG_STORAGE_PATH", "./storage"))
    safe = os.path.normpath(img_path.lstrip("/\\"))
    dest = os.path.abspath(os.path.join(img_storage, safe))
    if not dest.startswith(img_storage + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    # Ảnh SVG không được rasterize-ghi đè (sẽ làm hỏng file). Chỉ chỉnh tỉ lệ qua img_scale.
    if dest.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Ảnh SVG được thay đổi bằng tỉ lệ, không ghi đè file")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = await file.read()
    with open(dest, "wb") as f:
        f.write(data)
    return {"ok": True}


@router.post("/images/scale")
def update_image_scale(
    img_path: str = Form(...),
    scale: float = Form(...),
    current_user=Depends(get_current_user),
):
    # Ảnh SVG: chỉ lưu tỉ lệ hiển thị vào DB, không đụng tới file.
    base = os.path.basename(img_path.replace("\\", "/"))
    if not base:
        raise HTTPException(status_code=400, detail="Invalid path")
    with get_cursor() as (cur, conn):
        cur.execute(
            "UPDATE q_images SET img_scale = %s WHERE storage_path LIKE %s",
            (scale, f"%{base}"),
        )
        conn.commit()
    return {"ok": True}

