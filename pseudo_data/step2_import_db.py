import psycopg2
from psycopg2.extras import execute_values
import random
import uuid
import json
import bcrypt
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "api", ".env"))

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

NUM_TEACHERS = 3000
NUM_STUDENTS = 99999

def generate_names(count, names_data):
    first = names_data["ten"]
    middle = names_data["dem"]
    last = names_data["ho"]
    return [f"{random.choice(last)} {random.choice(middle)} {random.choice(first)}" for _ in range(count)]

def shuffle_with_locked_positions(items, is_shufflable_key=lambda x: x.get("is_shufflable", True)):
    shuffled = list(items)
    shufflable_indices = []
    shufflable_items = []
    for i, item in enumerate(items):
        if is_shufflable_key(item):
            shufflable_indices.append(i)
            shufflable_items.append(item)
    
    random.shuffle(shufflable_items)
    
    for i, item in zip(shufflable_indices, shufflable_items):
        shuffled[i] = item
        
    return shuffled

def import_db():
    try:
        with open("pseudo_data/curriculum.json", "r", encoding="utf-8") as f:
            curriculum = json.load(f)
        with open("pseudo_data/names.json", "r", encoding="utf-8") as f:
            names_data = json.load(f)
        with open("pseudo_data/questions.json", "r", encoding="utf-8") as f:
            raw_pool = json.load(f)
            
            global_pools = {}
            children_map = {}
            top_level_questions = []
            
            for q in raw_pool:
                tq = q["table_question"]
                p_id = tq.get("parent_id")
                if p_id:
                    if p_id not in children_map:
                        children_map[p_id] = []
                    children_map[p_id].append(q)
                else:
                    top_level_questions.append(q)
                    
            for q in top_level_questions:
                tq = q["table_question"]
                sub = tq.get("subject")
                if not sub: sub = "Vật Lí"
                q_type = tq.get("question_type", "mc")
                pub_id = tq.get("public_id")
                
                if sub not in global_pools:
                    global_pools[sub] = {"mc": [], "tf": [], "sa": [], "st": [], "oe": []}
                
                if q_type == "mc": global_pools[sub]["mc"].append(q)
                elif q_type == "tf": global_pools[sub]["tf"].append(q)
                elif q_type == "sa": global_pools[sub]["sa"].append(q)
                elif q_type == "st":
                    if pub_id in children_map and len(children_map[pub_id]) >= 2:
                        global_pools[sub]["st"].append(q)
                elif q_type == "oe":
                    global_pools[sub]["oe"].append(q)
            
            for sub in global_pools:
                if not global_pools[sub]["st"]:
                    global_pools[sub]["st"] = global_pools[sub]["oe"] if global_pools[sub]["oe"] else global_pools[sub]["mc"]
            
    except Exception as e:
        print(f"[!] Lỗi đọc file JSON: {e}")
        return

    all_subjects = list(curriculum.keys())

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
    except Exception as e:
        print(f"[!] Lỗi kết nối DB: {e}")
        return

    try:
        # 1. TRUNCATE DB
        print("[*] Đang xóa toàn bộ dữ liệu (TRUNCATE)...")
        cur.execute("TRUNCATE TABLE accounts, teachers, students, classes, students_classes, questions, q_images, q_choice_details, q_truefalse_details, q_shortans_details, contests, students_contests, contests_questions, contest_results, student_option_submissions RESTART IDENTITY CASCADE;")
        conn.commit()

        # 2. HASH PASSWORD
        print("[*] Đang pre-compute password hash...")
        hashed_pw = bcrypt.hashpw(b"00000000", bcrypt.gensalt()).decode("utf-8")
        
        # 3. GENERATE ACCOUNTS
        print("[*] Đang tạo Accounts...")
        total_accounts = NUM_TEACHERS + NUM_STUDENTS
        acc_data = []
        for i in range(1, total_accounts + 1):
            role = "teacher" if i <= NUM_TEACHERS else "student"
            email = f"teacher{i}@email.com" if role == "teacher" else f"student{i - NUM_TEACHERS}@email.com"
            acc_data.append((str(uuid.uuid4()), email, hashed_pw, role))
        
        execute_values(cur, "INSERT INTO accounts (public_id, email, password, role) VALUES %s", acc_data, page_size=10000)
        
        # 4. GENERATE TEACHERS & STUDENTS
        print("[*] Đang tạo Teachers và Students...")
        teacher_names = generate_names(NUM_TEACHERS, names_data)
        teacher_data = [(i, teacher_names[i-1], "HUST") for i in range(1, NUM_TEACHERS + 1)]
        execute_values(cur, "INSERT INTO teachers (id, name, organization) VALUES %s", teacher_data, page_size=10000)

        teacher_subjects_map = {}
        for i in range(1, NUM_TEACHERS + 1):
            teacher_subjects_map[i] = random.sample(all_subjects, random.randint(1, 3))

        student_names = generate_names(NUM_STUDENTS, names_data)
        student_data = [(i + NUM_TEACHERS, student_names[i-1]) for i in range(1, NUM_STUDENTS + 1)]
        execute_values(cur, "INSERT INTO students (id, name) VALUES %s", student_data, page_size=10000)

        # 5. GENERATE CLASSES
        print("[*] Đang tạo Classes...")
        class_data = []
        class_teacher_map = {}
        teacher_classes_map = {t_id: [] for t_id in range(1, NUM_TEACHERS + 1)}
        c_id = 1
        for t_id in range(1, NUM_TEACHERS + 1):
            num_classes = random.randint(2, 3)
            for _ in range(num_classes):
                class_teacher_map[c_id] = t_id
                teacher_classes_map[t_id].append(c_id)
                class_data.append((c_id, t_id, str(uuid.uuid4()), f"Class {c_id}", f"Description for Class {c_id}"))
                c_id += 1
        NUM_CLASSES = c_id - 1
        execute_values(cur, "INSERT INTO classes (id, teacher_id, public_id, class_name, description) VALUES %s", class_data, page_size=2000)

        student_class_data = []
        student_class_map = {cid: [] for cid in range(1, NUM_CLASSES + 1)}
        
        student_pool = list(range(1 + NUM_TEACHERS, NUM_STUDENTS + NUM_TEACHERS + 1))
        random.shuffle(student_pool)
        student_idx = 0
        
        for cid in range(1, NUM_CLASSES + 1):
            is_large = random.random() < 0.1
            num_stu = random.randint(90, 110) if is_large else random.randint(30, 40)
            
            assigned_students = []
            for _ in range(num_stu):
                assigned_students.append(student_pool[student_idx])
                student_idx = (student_idx + 1) % len(student_pool)
                
            for s_id in assigned_students:
                student_class_data.append((s_id, cid))
                student_class_map[cid].append(s_id)
                
        execute_values(cur, "INSERT INTO students_classes (student_id, class_id) VALUES %s", student_class_data, page_size=20000)

        # 6. GENERATE CONTESTS AND QUESTIONS IN BATCHES
        print("[*] Đang tạo Bank Câu hỏi (~3 triệu câu), Contests và Submissions...")
        current_q_id = 1
        current_choice_id = 1
        current_tf_id = 1
        current_sa_id = 1
        cr_id_counter = 1
        contest_id = 1
        
        BATCH_SIZE = 50
        
        for batch_start in range(1, NUM_TEACHERS + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, NUM_TEACHERS + 1)
            
            q_insert_data = []
            q_choices_mc = []
            q_choices_tf = []
            q_choices_sa = []
            q_images_data = []
            contest_data = []
            contest_questions_data = []
            contest_results_data = []
            submissions_data = []
            
            for t_id in range(batch_start, batch_end):
                allowed_subjects = teacher_subjects_map[t_id]
                t_classes = teacher_classes_map[t_id]
                
                # Bank for this teacher
                teacher_bank = {sub: {"mc": [], "tf": [], "sa": [], "st": [], "oe": []} for sub in allowed_subjects}
                
                # Generate 1000 - 1050 questions for this teacher
                num_bank_qs = random.randint(1000, 1050)
                q_types_map = {}
                q_choices_data_map = {}
                
                def process_details_local(template, db_id, type_str):
                    nonlocal current_choice_id, current_tf_id, current_sa_id
                    if template.get("table_details"):
                        records = template["table_details"].get("records", [])
                        mapped_records = []
                        if type_str == "mc":
                            for c in records:
                                q_choices_mc.append((current_choice_id, db_id, c["content"], c["is_correct"], c["order_index"], c.get("is_shufflable", True)))
                                mapped_records.append({"id": current_choice_id, "content": c["content"], "is_correct": c["is_correct"], "is_shufflable": c.get("is_shufflable", True)})
                                current_choice_id += 1
                        elif type_str == "tf":
                            for c in records:
                                q_choices_tf.append((current_tf_id, db_id, c["content"], c["is_correct"], c.get("explaination", ""), c["order_index"], c.get("is_shufflable", True)))
                                mapped_records.append({"id": current_tf_id, "content": c["content"], "is_correct": c["is_correct"], "is_shufflable": c.get("is_shufflable", True)})
                                current_tf_id += 1
                        elif type_str == "sa":
                            for c in records:
                                q_choices_sa.append((current_sa_id, db_id, c["content"]))
                                mapped_records.append({"content": c["content"]})
                                current_sa_id += 1
                        q_choices_data_map[db_id] = mapped_records
                                
                    for img in template.get("table_images", []):
                        q_images_data.append((db_id, img["storage_path"], img["img_type"], img["img_scale"], img["raw_code"]))

                for _ in range(num_bank_qs):
                    sub = random.choice(allowed_subjects)
                    q_type = random.choices(["mc", "tf", "sa", "st", "oe"], weights=[0.6, 0.1, 0.1, 0.1, 0.1])[0]
                    
                    pool = global_pools.get(sub, {}).get(q_type, [])
                    if not pool:
                        fallback_sub = "Vật Lí" if "Vật Lí" in global_pools else list(global_pools.keys())[0]
                        pool = global_pools[fallback_sub].get(q_type, [])
                        
                    q_template = random.choice(pool) if pool else {"table_question": {"question_type": q_type, "content": "Sample content", "layout_type": "default", "is_shufflable": True}}
                    tq = q_template["table_question"]
                    
                    actual_sub = tq.get("subject", sub)
                    if not actual_sub: actual_sub = "Vật Lí"
                    
                    if actual_sub in curriculum:
                        grades = list(curriculum[actual_sub].keys())
                        gr = random.choice(grades)
                        chap = random.choice(list(curriculum[actual_sub][gr].keys()))
                        les = random.choice(curriculum[actual_sub][gr][chap])
                    else:
                        gr = tq.get("grade", 12)
                        chap = tq.get("chapter", "Chapter 1")
                        les = tq.get("lesson", "Lesson 1")
                        
                    complexity = tq.get("complexity", random.randint(1, 4))
                    
                    parent_db_id = current_q_id
                    is_shufflable = False if q_type in ("st", "oe") else tq.get("is_shufflable", True)
                    
                    q_insert_data.append((parent_db_id, t_id, str(uuid.uuid4()), actual_sub, int(gr), q_type, tq.get("layout_type", "default"), tq.get("content", "Sample"), tq.get("solution", ""), chap, les, complexity, is_shufflable, None))
                    q_types_map[parent_db_id] = q_type
                    
                    process_details_local(q_template, parent_db_id, q_type)
                    current_q_id += 1
                    
                    if q_type == "st":
                        pub_id = tq.get("public_id")
                        children = children_map.get(pub_id, [])
                        group = [{"id": parent_db_id, "is_shufflable": False, "weight": 0.0, "type": "st"}]
                        for child_q in children:
                            c_tq = child_q["table_question"]
                            c_type = c_tq.get("question_type", "mc")
                            c_db_id = current_q_id
                            
                            q_insert_data.append((c_db_id, t_id, str(uuid.uuid4()), actual_sub, int(gr), c_type, c_tq.get("layout_type", "default"), c_tq.get("content", "Sample"), c_tq.get("solution", ""), chap, les, complexity, False, parent_db_id))
                            q_types_map[c_db_id] = c_type
                            
                            process_details_local(child_q, c_db_id, c_type)
                            group.append({"id": c_db_id, "is_shufflable": False, "weight": 1.0, "type": c_type})
                            current_q_id += 1
                        teacher_bank[sub]["st"].append(group)
                    else:
                        teacher_bank[sub][q_type].append({"id": parent_db_id, "is_shufflable": is_shufflable, "weight": 1.0, "type": q_type})

                # Create 2-3 Contests
                num_contests = random.randint(2, 3)
                for _ in range(num_contests):
                    sub = random.choice(allowed_subjects)
                    c_id_for_contest = random.choice(t_classes) if t_classes else None
                    
                    scoring_config = json.dumps({"mc": 1.0, "tf": 1.0, "sa": 1.0, "st": 1.0, "oe": 1.0})
                    contest_data.append((contest_id, c_id_for_contest, t_id, str(uuid.uuid4()), f"Contest {contest_id}", random.choice([45, 60, 90]), scoring_config, "active"))
                    
                    num_mc = random.randint(12, 30)
                    num_tf = 4
                    num_sa = 6
                    num_st = random.randint(1, 3)
                    
                    picked_questions = []
                    
                    def pick_from_bank(qt, count):
                        pool = teacher_bank[sub][qt]
                        if not pool:
                            for other_sub in allowed_subjects:
                                if teacher_bank[other_sub][qt]:
                                    pool = teacher_bank[other_sub][qt]
                                    break
                        if not pool: return
                        
                        samples = random.sample(pool, min(count, len(pool)))
                        if qt == "st":
                            for group in samples: picked_questions.extend(group)
                        else:
                            picked_questions.extend(samples)

                    pick_from_bank("mc", num_mc)
                    pick_from_bank("tf", num_tf)
                    pick_from_bank("sa", num_sa)
                    pick_from_bank("st", num_st)
                    
                    for order, q_obj in enumerate(picked_questions):
                        contest_questions_data.append((q_obj["id"], contest_id, order+1, q_obj["weight"], None))
                        
                    # GENERATE STUDENT SUBMISSIONS
                    if c_id_for_contest and c_id_for_contest in student_class_map:
                        students_in_class = student_class_map[c_id_for_contest]
                        participating_students = random.sample(students_in_class, int(len(students_in_class) * 0.8))
                        
                        for s_id in participating_students:
                            total_score = 0.0
                            wrong_answers = 0
                            
                            shuffled_qs = shuffle_with_locked_positions(picked_questions, lambda x: x["is_shufflable"])
                            display_order = ",".join(str(q["id"]) for q in shuffled_qs)
                            
                            for q_obj in shuffled_qs:
                                q_id = q_obj["id"]
                                pw = q_obj["weight"]
                                c_q_type = q_obj["type"]
                                
                                if c_q_type == "st": continue
                                    
                                is_correct = random.random() > 0.3
                                earned_point = float(pw) if is_correct else 0.0
                                total_score += earned_point
                                if not is_correct: wrong_answers += 1
                                
                                q_records = q_choices_data_map.get(q_id, [])
                                option_display_order = ""
                                
                                if c_q_type == "mc":
                                    if q_records:
                                        shuffled_opts = shuffle_with_locked_positions(q_records, lambda x: x["is_shufflable"])
                                        option_display_order = ",".join(str(opt["id"]) for opt in shuffled_opts)
                                        correct_choices = [c["content"] for c in q_records if c["is_correct"]]
                                        wrong_choices = [c["content"] for c in q_records if not c["is_correct"]]
                                        if is_correct and correct_choices:
                                            student_choice = random.choice(correct_choices)
                                        elif not is_correct and wrong_choices:
                                            student_choice = random.choice(wrong_choices)
                                        else:
                                            student_choice = random.choice(q_records)["content"]
                                    else:
                                        student_choice = "A"
                                elif c_q_type == "tf":
                                    if q_records:
                                        shuffled_opts = shuffle_with_locked_positions(q_records, lambda x: x["is_shufflable"])
                                        option_display_order = ",".join(str(opt["id"]) for opt in shuffled_opts)
                                        correct_tf = "".join(["T" if c["is_correct"] else "F" for c in q_records])
                                        if is_correct:
                                            student_choice = correct_tf
                                        else:
                                            tf_list = list(correct_tf)
                                            flip_count = random.randint(1, max(1, len(tf_list) - 1)) if len(tf_list) > 1 else 1
                                            flip_indices = random.sample(range(len(tf_list)), flip_count)
                                            for idx in flip_indices:
                                                tf_list[idx] = "F" if tf_list[idx] == "T" else "T"
                                            student_choice = "".join(tf_list)
                                    else:
                                        student_choice = "TTTT" if is_correct else "TFTF"
                                elif c_q_type == "sa":
                                    if q_records:
                                        student_choice = q_records[0]["content"] if is_correct else str(random.randint(0, 100)) + ".00"
                                    else:
                                        student_choice = "1.23" if is_correct else "0.00"
                                else:
                                    student_choice = "Bài làm tự luận..."
                                
                                submissions_data.append((cr_id_counter, q_id, student_choice, option_display_order, is_correct, earned_point))
                            
                            contest_results_data.append((cr_id_counter, s_id, contest_id, datetime.now(), datetime.now(), total_score, wrong_answers, display_order))
                            cr_id_counter += 1
                    
                    contest_id += 1

            # INSERT BATCH TO DB
            execute_values(cur, """
                INSERT INTO questions (id, teacher_id, public_id, subject, grade, question_type, layout_type, content, solution, chapter, lesson, complexity, is_shufflable, parent_id)
                VALUES %s
            """, q_insert_data, page_size=10000)
            
            if q_choices_mc: execute_values(cur, "INSERT INTO q_choice_details (id, question_id, content, is_correct, order_index, is_shufflable) VALUES %s", q_choices_mc, page_size=10000)
            if q_choices_tf: execute_values(cur, "INSERT INTO q_truefalse_details (id, question_id, content, is_correct, explaination, order_index, is_shufflable) VALUES %s", q_choices_tf, page_size=10000)
            if q_choices_sa: execute_values(cur, "INSERT INTO q_shortans_details (id, question_id, content) VALUES %s", q_choices_sa, page_size=10000)
            if q_images_data: execute_values(cur, "INSERT INTO q_images (question_id, storage_path, img_type, img_scale, raw_code) VALUES %s", q_images_data, page_size=10000)
            
            execute_values(cur, "INSERT INTO contests (id, class_id, teacher_id, public_id, title, time_limit, scoring_config, status) VALUES %s", contest_data, page_size=5000)
            execute_values(cur, "INSERT INTO contests_questions (question_id, contest_id, original_order, point_weight, group_id) VALUES %s", contest_questions_data, page_size=10000)
            
            if contest_results_data:
                execute_values(cur, "INSERT INTO contest_results (id, student_id, contest_id, start_time, end_time, total_score, count_wrong_answers, display_order) VALUES %s", contest_results_data, page_size=10000)
                execute_values(cur, "INSERT INTO student_option_submissions (contest_result_id, question_id, student_choice, option_display_order, is_correct, earned_point) VALUES %s", submissions_data, page_size=20000)

            print(f"  - Đã insert {len(q_insert_data)} câu hỏi cho batch teachers: {batch_end-1}/{NUM_TEACHERS}")

        # Cập nhật students_contests map
        cur.execute("INSERT INTO students_contests (student_id, contest_id) SELECT student_id, contest_id FROM contest_results;")
        
        # 8. UPDATE SEQUENCES
        print("[*] Cập nhật lại các Sequences (tránh lỗi duplicate id)...")
        tables_with_id = ['classes', 'questions', 'q_choice_details', 'q_truefalse_details', 'q_shortans_details', 'contests', 'contest_results']
        for table in tables_with_id:
            cur.execute(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}));")

        conn.commit()
        print("[+] SUCCESS: Đã gen xong dữ liệu vào DB!")
    
    except Exception as e:
        conn.rollback()
        print(f"[!] ERROR trong quá trình Insert: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import_db()
