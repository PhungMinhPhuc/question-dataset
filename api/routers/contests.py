import json
import uuid
from fastapi import APIRouter, HTTPException, Depends, Body
from db import get_cursor
from auth import get_current_teacher, get_current_user, optional_user
from models import ContestCreateRequest, ContestSubmitRequest, StartContestRequest

router = APIRouter(prefix="/contests", tags=["Contests"])


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
        if body.question_ids:
            cur.execute("SELECT id, question_type, parent_id FROM questions WHERE id = ANY(%s)", (body.question_ids,))
            qs = cur.fetchall()
            for q in qs:
                if q["question_type"] == "st":
                    st_parent_ids.append(q["id"])
                if q["parent_id"] is not None:
                    child_parent_ids.append(q["parent_id"])
                    
            for st_id in st_parent_ids:
                if child_parent_ids.count(st_id) < 2:
                    raise HTTPException(status_code=400, detail="Mỗi câu chung giả thiết phải có ít nhất 2 câu hỏi con đi kèm!")

        # Thêm câu hỏi vào đề
        for order, q_id in enumerate(body.question_ids, 1):
            cur.execute(
                """
                INSERT INTO contests_questions (contest_id, question_id, original_order, point_weight)
                VALUES (%s, %s, %s, %s)
                """,
                (contest_id, q_id, order, 1.0)
            )
        conn.commit()

    return {"id": contest_id, "public_id": str(contest["public_id"]), "message": "Tạo đề thi thành công"}


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
                # Chấm theo số statement đúng (0, 25%, 50%, 75%, 100%)
                if len(correct_str) > 0:
                    ratio = match_count / len(correct_str)
                    earned = round(weight * ratio, 4)
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

    return {"result": dict(result), "submissions": submissions, "questions": questions}


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
