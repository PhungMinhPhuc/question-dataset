import json
import uuid
from fastapi import APIRouter, HTTPException, Depends, Body
from db import get_cursor
from auth import get_current_teacher, get_current_user, optional_user
from models import ContestCreateRequest, ContestSubmitRequest, StartContestRequest, RandomContestRequest, ContestUpdateRequest

router = APIRouter(prefix="/contests", tags=["Contests"])

# Thang điểm mặc định (theo quy chế thi THPT): TN 0.25/câu, ĐS 1.0/câu,
# TLN 0.5/câu, TL 1.0/câu. Dùng khi đề không lưu scoring_config.
DEFAULT_SCORING = {"mc": 0.25, "tf": 1.0, "sa": 0.5, "oe": 1.0}

# Câu Đúng/Sai (tf) chấm theo số ý đúng: 1 ý = 10%, 2 ý = 25%, 3 ý = 50%,
# 4 ý = 100% số điểm tối đa của câu (quy chế THPT, áp dụng cho câu có 4 ý).
TF_LADDER_4 = {0: 0.0, 1: 0.1, 2: 0.25, 3: 0.5, 4: 1.0}


def tf_score_fraction(match_count: int, total: int) -> float:
    """Tỉ lệ điểm (0..1) của một câu Đúng/Sai theo số ý trả lời đúng."""
    if total <= 0:
        return 0.0
    if total == 4:
        return TF_LADDER_4.get(match_count, 0.0)
    # Số ý khác 4: nội suy tuyến tính theo tỉ lệ ý đúng.
    return match_count / total


def weight_for_type(scoring_config: dict, qtype: str) -> float:
    """Số điểm tối đa của một câu theo loại, lấy từ scoring_config của đề."""
    if qtype == "st":
        return 0.0  # câu 'chung giả thiết' không tính điểm, điểm nằm ở câu con
    config = scoring_config or {}
    try:
        return float(config.get(qtype, DEFAULT_SCORING.get(qtype, 1.0)))
    except (TypeError, ValueError):
        return DEFAULT_SCORING.get(qtype, 1.0)


@router.get("")
def list_contests(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    uid = current_user["user_id"]

    with get_cursor() as (cur, conn):
        if role == "teacher":
            cur.execute(
                """
                SELECT ct.*, cl.class_name,
                       COALESCE(SUM(CASE WHEN q.question_type != 'st' THEN 1 ELSE 0 END), 0) as question_count
                FROM contests ct
                LEFT JOIN classes cl ON cl.id = ct.class_id
                LEFT JOIN contests_questions cq ON cq.contest_id = ct.id
                LEFT JOIN questions q ON q.id = cq.question_id
                WHERE ct.teacher_id = %s AND ct.status != 'deleted'
                GROUP BY ct.id, cl.class_name
                ORDER BY ct.id DESC
                """,
                (uid,)
            )
        else:
            # Student: xem đề thi của lớp mình + đề public
            cur.execute(
                """
                SELECT ct.*, cl.class_name,
                       COALESCE(SUM(CASE WHEN q.question_type != 'st' THEN 1 ELSE 0 END), 0) as question_count,
                       (
                           SELECT json_agg(json_build_object(
                               'id', cr.id,
                               'start_time', cr.start_time,
                               'end_time', cr.end_time,
                               'total_score', cr.total_score
                           ) ORDER BY cr.id ASC)
                           FROM contest_results cr 
                           WHERE cr.contest_id = ct.id AND cr.student_id = %s AND cr.end_time IS NOT NULL
                       ) as attempts
                FROM contests ct
                LEFT JOIN classes cl ON cl.id = ct.class_id
                LEFT JOIN contests_questions cq ON cq.contest_id = ct.id
                LEFT JOIN questions q ON q.id = cq.question_id
                WHERE (ct.class_id IN (
                    SELECT class_id FROM students_classes WHERE student_id = %s
                ) OR ct.class_id IS NULL)
                AND ct.status = 'active'
                GROUP BY ct.id, cl.class_name
                ORDER BY ct.id DESC
                """,
                (uid, uid)
            )
        return [dict(r) for r in cur.fetchall()]


@router.post("")
def create_contest(body: ContestCreateRequest, current_user: dict = Depends(get_current_teacher)):
    with get_cursor() as (cur, conn):
        cur.execute(
            """
            INSERT INTO contests (class_id, teacher_id, title, time_limit, scoring_config, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, public_id
            """,
            (
                body.class_id, current_user["user_id"], body.title, body.time_limit,
                json.dumps(body.scoring_config), body.status
            )
        )
        contest = cur.fetchone()
        contest_id = contest["id"]

        # Validate ST questions have at least 2 children
        st_parent_ids = []
        child_parent_ids = []
        qtype_map = {}
        if body.question_ids:
            cur.execute("SELECT id, question_type, parent_id FROM questions WHERE id = ANY(%s)", (body.question_ids,))
            qs = cur.fetchall()
            for q in qs:
                qtype_map[q["id"]] = q["question_type"]
                if q["question_type"] == "st":
                    st_parent_ids.append(q["id"])
                if q["parent_id"] is not None:
                    child_parent_ids.append(q["parent_id"])

            for st_id in st_parent_ids:
                if child_parent_ids.count(st_id) < 2:
                    raise HTTPException(status_code=400, detail="Mỗi câu chung giả thiết phải có ít nhất 2 câu hỏi con đi kèm!")

        # Thêm câu hỏi vào đề — gán điểm tối đa từng câu theo loại + thang điểm
        for order, q_id in enumerate(body.question_ids, 1):
            weight = weight_for_type(body.scoring_config, qtype_map.get(q_id))
            cur.execute(
                """
                INSERT INTO contests_questions (contest_id, question_id, original_order, point_weight)
                VALUES (%s, %s, %s, %s)
                """,
                (contest_id, q_id, order, weight)
            )
        conn.commit()

    return {"id": contest_id, "public_id": str(contest["public_id"]), "message": "Tạo đề thi thành công"}


@router.post("/random")
def create_random_contest(body: RandomContestRequest, current_user: dict = Depends(get_current_teacher)):
    """Tự động bốc ngẫu nhiên `count` câu hỏi từ ngân hàng của giáo viên và tạo đề thi.

    Phiên bản đầu (tạm): chỉ bốc các câu đơn (không phải 'st' chung giả thiết) để
    tránh phải kéo theo câu con. Sau này có thể mở rộng theo ma trận đề thi.
    """
    if body.count < 1:
        raise HTTPException(status_code=400, detail="Số câu phải lớn hơn 0")

    with get_cursor() as (cur, conn):
        conditions = [
            "teacher_id = %s", "deleted_at IS NULL",
            "parent_id IS NULL", "question_type <> 'st'",
        ]
        params = [current_user["user_id"]]
        if body.subject:
            conditions.append("subject = %s"); params.append(body.subject)
        if body.grade:
            conditions.append("grade = %s"); params.append(body.grade)
        if body.question_type:
            conditions.append("question_type = %s"); params.append(body.question_type)
        if body.complexity:
            conditions.append("complexity = %s"); params.append(body.complexity)
        where = " AND ".join(conditions)

        # Bốc ngẫu nhiên, rồi sắp xếp theo loại (mc → tf → sa → oe) cho gọn đề
        cur.execute(
            f"""
            SELECT id, question_type
            FROM questions
            WHERE {where}
            ORDER BY RANDOM()
            LIMIT %s
            """,
            params + [body.count],
        )
        picked = cur.fetchall()
        if not picked:
            raise HTTPException(status_code=400, detail="Không có câu hỏi nào phù hợp để tạo đề")

        type_order = {"mc": 1, "tf": 2, "sa": 3, "oe": 4}
        picked = sorted(picked, key=lambda r: type_order.get(r["question_type"], 99))
        question_ids = [r["id"] for r in picked]
        qtype_map = {r["id"]: r["question_type"] for r in picked}

        cur.execute(
            """
            INSERT INTO contests (class_id, teacher_id, title, time_limit, scoring_config, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, public_id
            """,
            (
                body.class_id, current_user["user_id"], body.title, body.time_limit,
                json.dumps(body.scoring_config), body.status,
            ),
        )
        contest = cur.fetchone()
        contest_id = contest["id"]

        for order, q_id in enumerate(question_ids, 1):
            weight = weight_for_type(body.scoring_config, qtype_map.get(q_id))
            cur.execute(
                """
                INSERT INTO contests_questions (contest_id, question_id, original_order, point_weight)
                VALUES (%s, %s, %s, %s)
                """,
                (contest_id, q_id, order, weight),
            )
        conn.commit()

    return {
        "id": contest_id,
        "public_id": str(contest["public_id"]),
        "count": len(question_ids),
        "message": f"Đã tạo đề thi ngẫu nhiên với {len(question_ids)} câu",
    }


@router.get("/{contest_id}")
def get_contest(contest_id: int, current_user: dict = Depends(optional_user)):
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM contests WHERE id = %s", (contest_id,))
        contest = cur.fetchone()
        if not contest:
            raise HTTPException(status_code=404, detail="Đề thi không tồn tại")

        cur.execute(
            """
            SELECT q.id, q.question_type, q.layout_type, q.content, q.parent_id,
                   q.is_shufflable, cq.original_order, cq.point_weight
            FROM contests_questions cq
            JOIN questions q ON q.id = cq.question_id
            WHERE cq.contest_id = %s AND q.deleted_at IS NULL
            ORDER BY cq.original_order
            """,
            (contest_id,)
        )
        questions = [dict(r) for r in cur.fetchall()]

        # Với mỗi câu, lấy thêm images và details (không có đáp án đúng)
        for q in questions:
            cur.execute("SELECT storage_path, img_type, img_scale FROM q_images WHERE question_id = %s", (q["id"],))
            q["images"] = [dict(r) for r in cur.fetchall()]

            qtype = q["question_type"]
            if qtype == "mc":
                cur.execute(
                    "SELECT id, content, order_index FROM q_choice_details WHERE question_id = %s ORDER BY order_index",
                    (q["id"],)
                )
                q["options"] = [dict(r) for r in cur.fetchall()]
            elif qtype == "tf":
                cur.execute(
                    "SELECT id, content, order_index FROM q_truefalse_details WHERE question_id = %s ORDER BY order_index",
                    (q["id"],)
                )
                q["options"] = [dict(r) for r in cur.fetchall()]
            else:
                q["options"] = []

    return {"contest": dict(contest), "questions": questions}


@router.post("/{contest_id}/start")
def start_contest(contest_id: int, body: StartContestRequest, current_user: dict = Depends(optional_user)):
    """Tạo contest_result khi bắt đầu làm bài"""
    student_id = None
    if current_user and current_user.get("role") == "student":
        student_id = current_user.get("user_id")
    elif not current_user and not body.guest_name:
        raise HTTPException(status_code=400, detail="Cần đăng nhập hoặc cung cấp tên để thi")

    with get_cursor() as (cur, conn):
        if current_user and current_user.get("role") == "teacher":
            cur.execute("SELECT id FROM contests WHERE id = %s", (contest_id,))
        else:
            cur.execute("SELECT id FROM contests WHERE id = %s AND status = 'active'", (contest_id,))
            
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Đề thi không tồn tại hoặc chưa mở")

        cur.execute(
            """
            INSERT INTO contest_results (student_id, contest_id, guest_name, start_time)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
            """,
            (student_id, contest_id, body.guest_name if not student_id else None)
        )
        result_id = cur.fetchone()["id"]
        conn.commit()

    return {"contest_result_id": result_id}


@router.post("/{contest_id}/submit")
def submit_contest(
    contest_id: int,
    body: ContestSubmitRequest,
    current_user: dict = Depends(optional_user),
):
    """Nộp bài và chấm điểm"""
    with get_cursor() as (cur, conn):
        # Lấy đáp án đúng cho tất cả câu hỏi trong đề
        cur.execute(
            """
            SELECT q.id as question_id, q.question_type,
                   cq.point_weight
            FROM contests_questions cq
            JOIN questions q ON q.id = cq.question_id
            WHERE cq.contest_id = %s
            """,
            (contest_id,)
        )
        questions_meta = {r["question_id"]: dict(r) for r in cur.fetchall()}

        # Điểm tối đa của đề = tổng điểm tối đa từng câu (câu 'st' = 0)
        max_score = round(sum(
            float(m.get("point_weight") or 0.0)
            for m in questions_meta.values()
            if m.get("question_type") != "st"
        ), 2)

        total_score = 0.0
        wrong_count = 0

        for ans in body.answers:
            q_id = ans["question_id"]
            student_choice = ans.get("student_choice", "")
            q_meta = questions_meta.get(q_id, {})
            q_type = q_meta.get("question_type")
            weight = float(q_meta.get("point_weight") or 1.0)
            earned = 0.0
            is_correct = False

            if q_type == "mc":
                # Lấy đáp án đúng
                cur.execute(
                    "SELECT content FROM q_choice_details WHERE question_id = %s AND is_correct = true",
                    (q_id,)
                )
                correct_row = cur.fetchone()
                correct = correct_row["content"] if correct_row else ""
                is_correct = (student_choice.strip() == correct.strip())
                earned = weight if is_correct else 0.0

            elif q_type == "tf":
                # student_choice = "TTFT" (T=True, F=False cho từng statement)
                cur.execute(
                    "SELECT order_index, is_correct FROM q_truefalse_details WHERE question_id = %s ORDER BY order_index",
                    (q_id,)
                )
                statements = cur.fetchall()
                correct_str = "".join("T" if s["is_correct"] else "F" for s in statements)
                match_count = sum(1 for a, b in zip(student_choice, correct_str) if a == b)
                # Chấm theo số ý đúng: 1 ý=10%, 2 ý=25%, 3 ý=50%, 4 ý=100% (quy chế THPT)
                if len(correct_str) > 0:
                    frac = tf_score_fraction(match_count, len(correct_str))
                    earned = round(weight * frac, 4)
                    is_correct = (match_count == len(correct_str))

            elif q_type == "sa":
                cur.execute(
                    "SELECT content FROM q_shortans_details WHERE question_id = %s",
                    (q_id,)
                )
                correct_row = cur.fetchone()
                correct = correct_row["content"] if correct_row else ""
                is_correct = (student_choice.strip().lower() == correct.strip().lower())
                earned = weight if is_correct else 0.0

            if not is_correct and q_type in ("mc", "tf", "sa"):
                wrong_count += 1
            total_score += earned

            # Lưu submission
            cur.execute(
                """
                INSERT INTO student_option_submissions
                (contest_result_id, question_id, student_choice, option_display_order, is_correct, earned_point)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    body.contest_result_id, q_id, student_choice,
                    ans.get("option_display_order", ""), is_correct, earned
                )
            )

        # Cập nhật contest_result
        cur.execute(
            """
            UPDATE contest_results
            SET end_time = NOW(), total_score = %s, count_wrong_answers = %s
            WHERE id = %s
            """,
            (total_score, wrong_count, body.contest_result_id)
        )
        conn.commit()

    return {
        "total_score": total_score,
        "max_score": max_score,
        "wrong_count": wrong_count,
        "contest_result_id": body.contest_result_id
    }


@router.get("/results/{result_id}")
def get_result(result_id: int, current_user: dict = Depends(optional_user)):
    with get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT cr.*, ct.title, ct.scoring_config, ct.time_limit, s.name as student_name
            FROM contest_results cr
            JOIN contests ct ON ct.id = cr.contest_id
            LEFT JOIN accounts s ON s.id = cr.student_id
            WHERE cr.id = %s
            """,
            (result_id,)
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Kết quả không tồn tại")

        cur.execute(
            """
            SELECT sos.*, q.content, q.question_type, q.solution
            FROM student_option_submissions sos
            JOIN questions q ON q.id = sos.question_id
            WHERE sos.contest_result_id = %s
            """,
            (result_id,)
        )
        submissions = [dict(r) for r in cur.fetchall()]

        # Fetch all questions with answers for this contest
        cur.execute(
            """
            SELECT q.id, q.question_type, q.layout_type, q.content, q.parent_id, q.solution,
                   q.is_shufflable, cq.original_order, cq.point_weight
            FROM contests_questions cq
            JOIN questions q ON q.id = cq.question_id
            WHERE cq.contest_id = %s AND q.deleted_at IS NULL
            ORDER BY cq.original_order
            """,
            (result["contest_id"],)
        )
        questions = [dict(r) for r in cur.fetchall()]

        for q in questions:
            cur.execute("SELECT storage_path, img_type, img_scale FROM q_images WHERE question_id = %s", (q["id"],))
            q["images"] = [dict(r) for r in cur.fetchall()]

            qtype = q["question_type"]
            if qtype == "mc":
                cur.execute(
                    "SELECT id, content, is_correct, order_index FROM q_choice_details WHERE question_id = %s ORDER BY order_index",
                    (q["id"],)
                )
                q["options"] = [dict(r) for r in cur.fetchall()]
            elif qtype == "tf":
                cur.execute(
                    "SELECT id, content, is_correct, order_index, explaination FROM q_truefalse_details WHERE question_id = %s ORDER BY order_index",
                    (q["id"],)
                )
                q["options"] = [dict(r) for r in cur.fetchall()]
            elif qtype == "sa":
                cur.execute(
                    "SELECT id, content FROM q_shortans_details WHERE question_id = %s",
                    (q["id"],)
                )
                q["options"] = [dict(r) for r in cur.fetchall()]
            else:
                q["options"] = []

        # Điểm tối đa của đề (tổng điểm tối đa từng câu, bỏ câu 'st')
        max_score = round(sum(
            float(q.get("point_weight") or 0.0)
            for q in questions
            if q.get("question_type") != "st"
        ), 2)

    result_data = dict(result)
    result_data["max_score"] = max_score
    return {"result": result_data, "submissions": submissions, "questions": questions}


@router.delete("/results/{result_id}")
def delete_result(result_id: int, current_user: dict = Depends(get_current_teacher)):
    with get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT cr.id FROM contest_results cr
            JOIN contests ct ON ct.id = cr.contest_id
            WHERE cr.id = %s AND ct.teacher_id = %s
            """,
            (result_id, current_user["user_id"])
        )
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Không có quyền xóa bài thi này")
        
        cur.execute("DELETE FROM student_option_submissions WHERE contest_result_id = %s", (result_id,))
        cur.execute("DELETE FROM contest_results WHERE id = %s", (result_id,))
        conn.commit()
    return {"message": "Đã xóa bài thi"}

@router.get("/{contest_id}/submissions")
def get_contest_submissions(contest_id: int, current_user: dict = Depends(get_current_teacher)):
    with get_cursor() as (cur, conn):
        cur.execute("SELECT id FROM contests WHERE id = %s AND teacher_id = %s", (contest_id, current_user["user_id"]))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Không có quyền truy cập đề thi này")
        
        cur.execute(
            """
            SELECT cr.id as result_id, cr.start_time, cr.end_time, cr.total_score, cr.count_wrong_answers,
                   s.name as student_name, cr.guest_name
            FROM contest_results cr
            LEFT JOIN accounts s ON s.id = cr.student_id
            WHERE cr.contest_id = %s
            ORDER BY cr.id DESC
            """,
            (contest_id,)
        )
        results = [dict(r) for r in cur.fetchall()]
        for r in results:
            r["student_name"] = r["student_name"] or r["guest_name"] or "Khách ẩn danh"
            
        return {"submissions": results}


@router.patch("/{contest_id}/status")
def update_contest_status(
    contest_id: int,
    status: str,
    current_user: dict = Depends(get_current_teacher),
):
    if status not in ("active", "inactive", "deleted"):
        raise HTTPException(status_code=400, detail="Status phải là active, inactive hoặc deleted")

    with get_cursor() as (cur, conn):
        cur.execute(
            "UPDATE contests SET status = %s WHERE id = %s AND teacher_id = %s RETURNING id",
            (status, contest_id, current_user["user_id"])
        )
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Không có quyền cập nhật đề thi này")
        conn.commit()
    msg = "Đã xóa đề thi" if status == 'deleted' else f"Đề thi đã được {'mở' if status == 'active' else 'đóng'}"
    return {"message": msg}


@router.put("/{contest_id}")
def update_contest(
    contest_id: int,
    body: ContestUpdateRequest,
    current_user: dict = Depends(get_current_teacher),
):
    updates = []
    params = []
    if body.title is not None:
        updates.append("title = %s")
        params.append(body.title)
    if body.time_limit is not None:
        updates.append("time_limit = %s")
        params.append(body.time_limit)
    if body.status is not None:
        updates.append("status = %s")
        params.append(body.status)

    if not updates:
        raise HTTPException(status_code=400, detail="Không có trường nào để cập nhật")

    query = f"UPDATE contests SET {', '.join(updates)} WHERE id = %s AND teacher_id = %s RETURNING id"
    params.extend([contest_id, current_user["user_id"]])

    with get_cursor() as (cur, conn):
        cur.execute(query, params)
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Không có quyền cập nhật đề thi này hoặc đề thi không tồn tại")
        conn.commit()
        
    return {"message": "Cập nhật đề thi thành công"}

