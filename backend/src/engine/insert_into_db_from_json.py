import os
import json
import psycopg2
from dotenv import load_dotenv

# Load các biến môi trường từ file .env
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "api", ".env")
if not os.path.exists(_ENV_PATH):
    # Fallback: thử path cũ trong venv
    _ENV_PATH = r"e:\Downloads\database_question_dataset\backend\venv\.env"
load_dotenv(dotenv_path=_ENV_PATH)

def insert_questions_from_json(json_file_path):
    conn = None
    cur = None
    try:
        # 1. Kết nối đến PostgreSQL sử dụng biến môi trường
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()

        # 2. Đọc dữ liệu từ file JSON
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Map lưu trữ: public_id (UUID) -> id (bigint tự tăng trong DB)
        # Mục đích: Để gán parent_id cho câu hỏi con trong câu chùm
        id_map = {}

        for item in data:
            q = item['table_question']
            
            # Xử lý lấy parent_id nội bộ dựa trên UUID trong JSON
            internal_parent_id = id_map.get(q['parent_id']) if q.get('parent_id') else None

            # --- 3. Chèn vào bảng questions ---
            insert_q_query = """
            INSERT INTO questions (
                teacher_id, public_id, subject, grade, parent_id, 
                question_type, layout_type, content, solution, 
                chapter, lesson, complexity, is_shufflable
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            
            cur.execute(insert_q_query, (
                q['teacher_id'], q['public_id'], q['subject'], q['grade'], internal_parent_id,
                q['question_type'], q['layout_type'], q['content'], q['solution'],
                q['chapter'], q['lesson'], q['complexity'], q['is_shufflable']
            ))
            
            # Lấy ID (bigint) vừa tạo để làm khóa ngoại cho các bảng con
            new_question_id = cur.fetchone()[0]
            id_map[q['public_id']] = new_question_id

            # --- 4. Chèn vào bảng q_images ---
            if item.get('table_images'):
                img_query = """
                INSERT INTO q_images (question_id, storage_path, img_type, img_scale, raw_code)
                VALUES (%s, %s, %s, %s, %s)
                """
                for img in item['table_images']:
                    cur.execute(img_query, (
                        new_question_id, img['storage_path'], img['img_type'], 
                        img['img_scale'], img['raw_code']
                    ))

            # --- 5. Chèn vào các bảng chi tiết (Details) ---
            details_data = item.get('table_details', {})
            target_table = details_data.get('target_table')
            records = details_data.get('records', [])

            if target_table == "q_choice_details":
                mc_query = """
                INSERT INTO q_choice_details (question_id, content, is_correct, order_index, is_shufflable)
                VALUES (%s, %s, %s, %s, %s)
                """
                for rec in records:
                    cur.execute(mc_query, (
                        new_question_id, rec['content'], rec['is_correct'], 
                        rec['order_index'], rec.get('is_shufflable', True)
                    ))

            elif target_table == "q_truefalse_details":
                tf_query = """
                INSERT INTO q_truefalse_details (question_id, content, is_correct, explaination, order_index, is_shufflable)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                for rec in records:
                    expl = rec.get('explanation') or rec.get('explaination')
                    cur.execute(tf_query, (
                        new_question_id, rec['content'], rec['is_correct'], expl,
                        rec['order_index'], rec.get('is_shufflable', True)
                    ))

            elif target_table == "q_shortans_details":
                sa_query = """
                INSERT INTO q_shortans_details (question_id, content)
                VALUES (%s, %s)
                """
                for rec in records:
                    cur.execute(sa_query, (new_question_id, rec['content']))

        # Commit giao dịch
        conn.commit()
        print(f"Thành công: Đã chèn {len(data)} bản ghi vào Database.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Đã xảy ra lỗi: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    # Thay 'data.json' bằng tên file json của bạn
    insert_questions_from_json("E:/Downloads/export_ (33).json")