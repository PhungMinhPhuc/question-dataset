import os
import io
import zipfile
import tempfile
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from db import get_cursor
from auth import get_current_teacher, optional_user
import sys

# Thêm engine parser vào path
ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "src", "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)

from exporters.export_manager import export_contest_zip

router = APIRouter(prefix="/export", tags=["Export"])

@router.post("/exam/{contest_id}")
def export_exam(
    contest_id: int,
    payload: dict,
    current_user: dict = Depends(get_current_teacher)
):
    # payload: { "formats": ["word", "pdf", "latex"], "num_shuffles": 4, "exam_title": "...", "general_info": "..." }
    formats = payload.get("formats", ["word"])
    num_shuffles = payload.get("num_shuffles", 1)
    exam_title = payload.get("exam_title", "")
    department = payload.get("department", "")
    exam_type = payload.get("exam_type", "")
    subject = payload.get("subject", "")
    duration = payload.get("duration", 50)
    general_info = payload.get("general_info", "")
    code_type = payload.get("code_type", "incremental")
    starting_code = payload.get("starting_code", "001")
    code_step = int(payload.get("code_step", 1))
    random_length = payload.get("random_length", 3)
    
    with get_cursor() as (cur, conn):
        # Lấy thông tin đề thi
        cur.execute("SELECT * FROM contests WHERE id = %s", (contest_id,))
        contest = cur.fetchone()
        if not contest:
            raise HTTPException(status_code=404, detail="Đề thi không tồn tại")
            
        # Lấy danh sách câu hỏi
        cur.execute(
            """
            SELECT q.id, q.question_type, q.layout_type, q.content, q.parent_id, q.solution,
                   q.is_shufflable, cq.original_order
            FROM contests_questions cq
            JOIN questions q ON q.id = cq.question_id
            WHERE cq.contest_id = %s AND q.deleted_at IS NULL
            ORDER BY cq.original_order
            """,
            (contest_id,)
        )
        questions = [dict(r) for r in cur.fetchall()]
        
        q_ids = tuple(q["id"] for q in questions) if questions else tuple()
        
        # Nếu có câu chùm (parent_id), thì ta đã lấy cha chưa?
        # Trong database, contest có chứa câu cha hay câu con?
        # Thường contest chứa câu cha, còn câu con thì fetch theo parent_id
        # Let's check if we need to fetch children
        
        if q_ids:
            cur.execute("SELECT * FROM q_images WHERE question_id IN %s", (q_ids,))
            images = cur.fetchall()
            img_map = {}
            for img in images:
                qid = img["question_id"]
                if qid not in img_map: img_map[qid] = []
                img_map[qid].append(dict(img))
                
            cur.execute("SELECT * FROM q_choice_details WHERE question_id IN %s ORDER BY order_index", (q_ids,))
            mc_opts = cur.fetchall()
            mc_map = {}
            for opt in mc_opts:
                qid = opt["question_id"]
                if qid not in mc_map: mc_map[qid] = []
                mc_map[qid].append(dict(opt))
                
            cur.execute("SELECT * FROM q_truefalse_details WHERE question_id IN %s ORDER BY order_index", (q_ids,))
            tf_opts = cur.fetchall()
            tf_map = {}
            for opt in tf_opts:
                qid = opt["question_id"]
                if qid not in tf_map: tf_map[qid] = []
                tf_map[qid].append(dict(opt))
                
            cur.execute("SELECT * FROM q_shortans_details WHERE question_id IN %s", (q_ids,))
            sa_opts = cur.fetchall()
            sa_map = {}
            for opt in sa_opts:
                qid = opt["question_id"]
                if qid not in sa_map: sa_map[qid] = []
                sa_map[qid].append(dict(opt))
                
            for q in questions:
                qid = q["id"]
                q["images"] = img_map.get(qid, [])
                qtype = q["question_type"]
                if qtype == "mc": q["options"] = mc_map.get(qid, [])
                elif qtype == "tf": q["options"] = tf_map.get(qid, [])
                elif qtype == "sa": q["options"] = sa_map.get(qid, [])
                else: q["options"] = []
                
        # Call export manager
        zip_buffer = export_contest_zip(dict(contest), questions, num_shuffles, formats, exam_title, general_info, department, exam_type, subject, duration, code_type, starting_code, code_step, random_length)
        
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=Export_Contest_{contest_id}.zip"}
        )
