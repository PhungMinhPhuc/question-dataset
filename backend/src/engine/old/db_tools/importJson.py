import psycopg2
import json
import os
from dotenv import load_dotenv

#Hướng dẫn nhập thử dùng file này:
## - B1: tạo csdl từ file sql Phi gửi, tạo thêm 1 bảng jsonplaceholder chỉ có đúng một trường là metadata định dạng jonb
## - B2: lưu file all_quesiton.json và paste path đến file đấy vào rootFilePath
## - B3: Nhập đúng thông tin để kết nối vs csdl trên postgres ở chỗ dưới kia
## Rồi chạy là OK

basePath = os.path.dirname(os.path.abspath(__file__))
rootFilePath = "Sample/data_test.json" ##paste đường dẫn tuyệt đối file json chứa data vào đây
tmpTable = "jsonplaceholder"



# Connect to PostgreSQL
load_dotenv()  # load file .env

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Load JSON properly (NOT read as string)
with open(f"{rootFilePath}", "r", encoding="utf-8") as f:
    data = json.load(f)

for key in data:
    for q in data[key]:
        cur.execute(
            f"INSERT INTO {tmpTable} (metadata) VALUES (%s::jsonb)",
            (json.dumps(q),)
        )
    desTable = key
    sql_query = ""
    if(key == 'questions'):
        sql_query= f"""
        INSERT INTO {desTable} (teacher_id, id, subject_id, grade, parent_id, q_type, layout_type, content_tex, image, solution_tex, chapter, lesson, difficulty, is_shufflable)
        SELECT 
            metadata->>'teacher_id',
            metadata->>'id',
            metadata->>'subject_id',
            (NULLIF(metadata->>'grade', ''))::smallint,
            metadata->>'parent_id',
            metadata->>'q_type',
            metadata->>'layout_type',
            metadata->>'content_tex',
            metadata->>'image',
            metadata->>'solution_tex',
            metadata->>'chapter',
            metadata->>'lesson',
            (NULLIF(metadata->>'difficulty', ''))::smallint,
            (NULLIF(metadata->>'is_shufflable', ''))::boolean
        FROM {tmpTable};
        """
    elif(key == 'question_details'):
        sql_query=f"""
        INSERT INTO {desTable} (id, question_id, content_tex, is_correct, order_index,explanation_tex, original_order, is_shufflable)
        SELECT 
            metadata->>'id',
            metadata->>'question_id',
            metadata->>'content_tex',
            (NULLIF(metadata->>'is_correct',''))::boolean,
            (NULLIF(metadata->>'order_index',''))::int,
            metadata->>'explanation_tex',
            (NULLIF(metadata->>'original_order',''))::int,
            (NULLIF(metadata->>'is_shufflable', ''))::boolean
        FROM {tmpTable};
        """
    if(sql_query != ""):
        cur.execute(sql_query)
    cur.execute(
        f"TRUNCATE TABLE {tmpTable}"
    )

# Commit & close
conn.commit()
cur.close()
conn.close()

print("Inserted successfully!")