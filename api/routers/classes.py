from fastapi import APIRouter, HTTPException, Depends
from db import get_cursor
from auth import get_current_teacher, get_current_user
from models import ClassCreateRequest, JoinClassRequest, AddStudentRequest
import uuid

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.get("")
def list_classes(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    uid = current_user["user_id"]

    with get_cursor() as (cur, conn):
        if role == "teacher":
            cur.execute(
                """
                SELECT c.*, 
                       COUNT(DISTINCT sc.student_id) as student_count,
                       COUNT(DISTINCT ct.id) as contest_count
                FROM classes c
                LEFT JOIN students_classes sc ON sc.class_id = c.id
                LEFT JOIN contests ct ON ct.class_id = c.id
                WHERE c.teacher_id = %s
                GROUP BY c.id
                ORDER BY c.create_at DESC
                """,
                (uid,)
            )
        else:
            cur.execute(
                """
                SELECT c.*, t.name as teacher_name,
                       COUNT(DISTINCT sc2.student_id) as student_count
                FROM classes c
                JOIN students_classes sc ON sc.class_id = c.id AND sc.student_id = %s
                LEFT JOIN accounts t ON t.id = c.teacher_id
                LEFT JOIN students_classes sc2 ON sc2.class_id = c.id
                GROUP BY c.id, t.name
                ORDER BY c.create_at DESC
                """,
                (uid,)
            )
        return [dict(r) for r in cur.fetchall()]


@router.post("")
def create_class(body: ClassCreateRequest, current_user: dict = Depends(get_current_teacher)):
    with get_cursor() as (cur, conn):
        cur.execute(
            "INSERT INTO classes (teacher_id, class_name, description) VALUES (%s, %s, %s) RETURNING id, public_id",
            (current_user["user_id"], body.class_name, body.description)
        )
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"], "public_id": str(row["public_id"]), "message": "Tạo lớp thành công"}


@router.get("/{class_id}")
def get_class(class_id: int, current_user: dict = Depends(get_current_user)):
    with get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT c.*, t.name as teacher_name
            FROM classes c
            LEFT JOIN accounts t ON t.id = c.teacher_id
            WHERE c.id = %s
            """,
            (class_id,)
        )
        cls = cur.fetchone()
        if not cls:
            raise HTTPException(status_code=404, detail="Lớp không tồn tại")

        cur.execute(
            """
            SELECT a.id, a.name, a.email, sc.create_at as joined_at
            FROM students_classes sc
            JOIN accounts a ON a.id = sc.student_id
            WHERE sc.class_id = %s
            """,
            (class_id,)
        )
        students = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT id, title, status, time_limit FROM contests WHERE class_id = %s ORDER BY id DESC",
            (class_id,)
        )
        contests = [dict(r) for r in cur.fetchall()]

    result = dict(cls)
    result["students"] = students
    result["contests"] = contests
    return result


@router.post("/join")
def join_class(body: JoinClassRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể tham gia lớp")

    with get_cursor() as (cur, conn):
        cur.execute("SELECT id FROM classes WHERE public_id = %s", (body.class_public_id,))
        cls = cur.fetchone()
        if not cls:
            raise HTTPException(status_code=404, detail="Mã lớp không hợp lệ")

        class_id = cls["id"]
        student_id = current_user["user_id"]

        # Kiểm tra đã vào lớp chưa
        cur.execute(
            "SELECT 1 FROM students_classes WHERE student_id = %s AND class_id = %s",
            (student_id, class_id)
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Bạn đã tham gia lớp này rồi")

        cur.execute(
            "INSERT INTO students_classes (student_id, class_id) VALUES (%s, %s)",
            (student_id, class_id)
        )
        conn.commit()

    return {"message": "Tham gia lớp thành công"}


@router.delete("/{class_id}/students/{student_id}")
def remove_student(class_id: int, student_id: int, current_user: dict = Depends(get_current_teacher)):
    with get_cursor() as (cur, conn):
        cur.execute(
            "DELETE FROM students_classes WHERE student_id = %s AND class_id = %s",
            (student_id, class_id)
        )
        conn.commit()
    return {"message": "Đã xóa học sinh khỏi lớp"}


@router.post("/{class_id}/students")
def add_student(class_id: int, body: AddStudentRequest, current_user: dict = Depends(get_current_teacher)):
    with get_cursor() as (cur, conn):
        # Kiểm tra quyền sở hữu lớp
        cur.execute("SELECT 1 FROM classes WHERE id = %s AND teacher_id = %s", (class_id, current_user["user_id"]))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Không có quyền quản lý lớp này")

        # Tìm học sinh
        student_id = None
        ident = body.identifier.strip()
        
        if "@" in ident:
            cur.execute("SELECT id FROM accounts WHERE email = %s AND role = 'student'", (ident,))
            acc = cur.fetchone()
            if acc:
                student_id = acc["id"]
        elif ident.isdigit():
            cur.execute("SELECT id FROM accounts WHERE id = %s AND role = 'student'", (int(ident),))
            acc = cur.fetchone()
            if acc:
                student_id = acc["id"]

        if not student_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy học sinh (ID hoặc Email không hợp lệ)")

        # Kiểm tra xem học sinh đã có trong lớp chưa
        cur.execute("SELECT 1 FROM students_classes WHERE student_id = %s AND class_id = %s", (student_id, class_id))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Học sinh này đã tham gia lớp")

        # Thêm vào lớp
        cur.execute("INSERT INTO students_classes (student_id, class_id) VALUES (%s, %s)", (student_id, class_id))
        conn.commit()

    return {"message": "Đã thêm học sinh vào lớp thành công"}


@router.get("/students/search")
def search_students(q: str, current_user: dict = Depends(get_current_teacher)):
    q_str = f"%{q}%"
    with get_cursor() as (cur, conn):
        cur.execute(
            """
            SELECT a.id, a.name, a.email
            FROM accounts a
            WHERE a.role = 'student'
              AND (CAST(a.id AS TEXT) LIKE %s OR a.email ILIKE %s OR a.name ILIKE %s)
            LIMIT 10
            """,
            (q_str, q_str, q_str)
        )
        return [dict(r) for r in cur.fetchall()]
