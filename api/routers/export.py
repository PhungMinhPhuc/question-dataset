import os
import io
import zipfile
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from db import get_cursor
from auth import get_current_teacher, optional_user
import sys

# Thêm engine parser vào path
ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "src", "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)

from exporters.export_manager import export_contest_zip

router = APIRouter(prefix="/export", tags=["Export"])

# In-Memory Queue State
executor = ThreadPoolExecutor(max_workers=2)
export_tasks = {}

def update_task_progress(task_id, progress, total, message):
    if task_id in export_tasks:
        export_tasks[task_id]["progress"] = progress
        export_tasks[task_id]["total"] = total
        export_tasks[task_id]["message"] = message

def run_export_task(task_id, contest_id, contest, questions, num_shuffles, formats, exam_title, general_info, department, exam_type, subject, duration, code_type, starting_code, code_step, random_length, shuffle_order=True, shuffle_options=True):
    try:
        export_tasks[task_id]["status"] = "processing"

        def progress_callback(progress, total, message):
            update_task_progress(task_id, progress, total, message)

        zip_buffer = export_contest_zip(
            contest, questions, num_shuffles, formats,
            exam_title, general_info, department, exam_type, subject, duration,
            code_type, starting_code, code_step, random_length,
            progress_callback=progress_callback,
            shuffle_order=shuffle_order, shuffle_options=shuffle_options,
        )
        
        # Save zip to file
        _default_storage = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
        storage_path = os.getenv("IMG_STORAGE_PATH", _default_storage)
        exports_dir = os.path.join(storage_path, "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        file_path = os.path.join(exports_dir, f"Export_{task_id}.zip")
        with open(file_path, "wb") as f:
            f.write(zip_buffer.getvalue())
            
        export_tasks[task_id]["status"] = "completed"
        export_tasks[task_id]["file_path"] = file_path
        export_tasks[task_id]["progress"] = 1 + num_shuffles
        export_tasks[task_id]["message"] = "Hoàn tất!"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        export_tasks[task_id]["status"] = "error"
        export_tasks[task_id]["message"] = str(e)


@router.post("/exam/{contest_id}")
def export_exam(
    contest_id: int,
    payload: dict,
    current_user: dict = Depends(get_current_teacher)
):
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
    # Chế độ đảo: 'shuffle_mode' = 'order' (đảo đề) | 'options' (đảo câu) | 'both' (đề+câu, mặc định)
    shuffle_mode = payload.get("shuffle_mode", "both")
    shuffle_order = shuffle_mode in ("order", "both")
    shuffle_options = shuffle_mode in ("options", "both")

    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM contests WHERE id = %s", (contest_id,))
        contest = cur.fetchone()
        if not contest:
            raise HTTPException(status_code=404, detail="Đề thi không tồn tại")
            
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
                
        task_id = str(uuid.uuid4())
        export_tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "total": 1 + num_shuffles,
            "message": "Đang xếp hàng chờ...",
            "file_path": None,
            "contest_id": contest_id
        }
        
        executor.submit(
            run_export_task,
            task_id, contest_id, dict(contest), questions, num_shuffles, formats,
            exam_title, general_info, department, exam_type, subject, duration,
            code_type, starting_code, code_step, random_length,
            shuffle_order, shuffle_options,
        )
        
        return {"task_id": task_id, "status": "pending", "message": "Task queued successfully"}

@router.get("/status/{task_id}")
def get_export_status(task_id: str):
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return export_tasks[task_id]

@router.get("/download/{task_id}")
def download_export(task_id: str, background_tasks: BackgroundTasks):
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_info = export_tasks[task_id]
    if task_info["status"] != "completed" or not task_info["file_path"]:
        raise HTTPException(status_code=400, detail="Task is not completed yet")
        
    file_path = task_info["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    def cleanup():
        try:
            os.remove(file_path)
            del export_tasks[task_id]
        except Exception:
            pass
            
    background_tasks.add_task(cleanup)
    
    return FileResponse(
        path=file_path,
        media_type="application/zip",
        filename=f"Export_Contest_{task_info.get('contest_id', 'Unknown')}.zip"
    )
