"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import Sidebar from "@/components/Sidebar";
import LatexRenderer from "@/components/LatexRenderer";
import Combobox from "@/components/Combobox";
import { QuestionEditor, QuestionDetail } from "@/components/QuestionEditor";
import api from "@/lib/api";

const TYPE_COLORS: Record<string, string> = {
  mc: "#6c63ff",
  tf: "#f59e0b",
  sa: "#10b981",
  oe: "#3b82f6",
  st: "#ec4899",
};

type ParsedItem = {
  table_question: Record<string, unknown>;
  table_details: { target_table: string; records: Record<string, unknown>[] };
  table_images: { storage_path?: string; url?: string }[];
};

const TYPE_LABELS: Record<string, string> = {
  mc: "Trắc nghiệm",
  tf: "Đúng/Sai",
  sa: "Trả lời ngắn",
  oe: "Tự luận",
  st: "Chung giả thiết",
};
const COMPLEXITY_LABELS: Record<number, string> = {
  1: "Nhận biết",
  2: "Thông hiểu",
  3: "Vận dụng",
  4: "Vận dụng cao",
};

export default function UploadPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [editModal, setEditModal] = useState<{
    idx: number;
    draft: QuestionDetail;
    isChild: boolean;
    childIndex?: number;
  } | null>(null);

  const mapToDetail = (item: any): QuestionDetail => {
    return {
      id: 0,
      subject: subject,
      grade: Number(grade),
      chapter: item.table_question.chapter || "",
      lesson: item.table_question.lesson || "",
      question_type: item.table_question.question_type,
      complexity: item.table_question.complexity || 1,
      content: item.table_question.content || "",
      solution: item.table_question.solution || "",
      images: item.table_images || [],
      details:
        item.table_details?.records?.map((r: any, i: number) => ({
          id: i,
          content: r.content,
          is_correct: r.is_correct,
        })) || [],
    };
  };

  const mapFromDetail = (qData: QuestionDetail, oldItem: any) => {
    return {
      ...oldItem,
      table_question: {
        ...oldItem.table_question,
        content: qData.content,
        solution: qData.solution,
        chapter: qData.chapter,
        lesson: qData.lesson,
        complexity: qData.complexity,
      },
      table_details: oldItem.table_details
        ? {
            ...oldItem.table_details,
            records:
              qData.details?.map((d: any) => ({
                content: d.content,
                is_correct: d.is_correct,
              })) || [],
          }
        : oldItem.table_details,
    };
  };

  const openEdit = (idx: number, isChild: boolean, childIndex?: number) => {
    setEditModal({ idx, draft: mapToDetail(preview[idx]), isChild, childIndex });
  };

  const saveEdit = () => {
    if (!editModal) return;
    const next = [...preview];
    next[editModal.idx] = mapFromDetail(editModal.draft, next[editModal.idx]);
    setPreview(next);
    setEditModal(null);
  };

  const [success, setSuccess] = useState("");
  const [preview, setPreview] = useState<ParsedItem[]>([]);
  const [subjects, setSubjects] = useState<Record<string, unknown>>({});

  const [subject, setSubject] = useState("Toán");
  const [grade, setGrade] = useState("12");
  const [chapter, setChapter] = useState("");
  const [complexity, setComplexity] = useState(1);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/");
    if (!isLoading && user?.role !== "teacher") router.replace("/dashboard");
  }, [user, isLoading, router]);

  useEffect(() => {
    api
      .getSubjects()
      .then(setSubjects)
      .catch(() => {});
  }, []);

  const subjectList = Object.keys(subjects);
  const gradeList = subject
    ? Object.keys(
        (subjects as Record<string, Record<string, unknown>>)[subject] || {},
      )
    : ["10", "11", "12"];
  const chapterList =
    subject && grade
      ? Object.keys(
          (subjects as Record<string, Record<string, Record<string, unknown>>>)[
            subject
          ]?.[grade] || {},
        )
      : [];

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && (f.name.endsWith(".tex") || f.name.endsWith(".zip") || f.name.endsWith(".docx"))) setFile(f);
  };

  const handleParse = async () => {
    if (!file || !user) return;
    setLoading(true);
    setError("");
    setPreview([]);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("teacher_id", String(user.user_id));
    fd.append("subject", subject);
    fd.append("grade", grade);
    fd.append("chapter", chapter);
    fd.append("complexity", String(complexity));
    try {
      const res = await api.uploadTex(fd);
      if (res.data && res.data.length > 0) {
        setPreview(res.data);
      } else {
        setError("Không tìm thấy câu hỏi nào trong file (định dạng chưa chuẩn). Vui lòng đảm bảo các câu hỏi bắt đầu bằng chữ 'Câu 1.', 'Câu 2:',...");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Lỗi parse file");
    } finally {
      setLoading(false);
    }
  };

  const updateItem = (idx: number, key: string, val: unknown) => {
    setPreview((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      next[idx].table_question[key] = val;
      return next;
    });
  };

  const removeItem = (idx: number) =>
    setPreview((prev) => prev.filter((_, i) => i !== idx));

  const stCount = preview.filter(
    (q: any) => q.table_question?.question_type === "st",
  ).length;
  const actualQCount = preview.length - stCount;
  const countText =
    stCount > 0
      ? `${actualQCount} câu hỏi và ${stCount} chung giả thiết`
      : `${actualQCount} câu hỏi`;

  const handleConfirm = async () => {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      await api.confirmUpload({
        teacher_id: user.user_id,
        subject,
        grade: parseInt(grade),
        data: preview,
      });
      setSuccess(` Đã lưu ${countText} vào database!`);
      setPreview([]);
      setFile(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Lỗi lưu database");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-wrapper">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">Upload câu hỏi LaTeX</h1>
            <p className="page-sub">
              Upload file .tex hoặc .zip chứa câu hỏi định dạng LaTeX chuẩn
            </p>
          </div>
        </div>

        {error && <div className="alert alert-error"> {error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {preview.length === 0 ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1.5rem",
            }}
          >
            {/* Upload zone */}
            <div>
              <div
                className={`upload-zone ${dragging ? "drag-over" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
              >
                <div className="upload-icon"></div>
                <div className="upload-text">
                  Kéo thả hoặc click để chọn file
                </div>
                <div className="upload-sub">Hỗ trợ: .tex, .zip, .docx</div>
                {file && (
                  <div
                    style={{
                      marginTop: "1rem",
                      color: "var(--accent-success)",
                      fontWeight: 600,
                    }}
                  >
                    ✓ {file.name}
                  </div>
                )}
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".tex,.zip,.docx"
                style={{ display: "none" }}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </div>

            {/* Metadata */}
            <div className="card">
              <h3 style={{ marginBottom: "1.25rem" }}>Thông tin câu hỏi</h3>
              <div className="form-group">
                <label className="form-label">Môn học</label>
                <select
                  className="select"
                  value={subject}
                  onChange={(e) => {
                    const newSubj = e.target.value;
                    setSubject(newSubj);
                    const newGrades = Object.keys(
                      (subjects as Record<string, Record<string, unknown>>)[
                        newSubj
                      ] || {},
                    );
                    setGrade(newGrades[0] || "12");
                    setChapter("");
                  }}
                >
                  {subjectList.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Khối lớp</label>
                <select
                  className="select"
                  value={grade}
                  onChange={(e) => {
                    setGrade(e.target.value);
                    setChapter("");
                  }}
                >
                  {gradeList.map((g) => (
                    <option key={g} value={g}>
                      Lớp {g}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Chương (mặc định)</label>
                <select
                  className="select"
                  value={chapter}
                  onChange={(e) => setChapter(e.target.value)}
                >
                  <option value="">— Chọn chương —</option>
                  {chapterList.map((c) => (
                    <option key={c} value={c}>
                      {c.slice(0, 60)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Mức độ mặc định</label>
                <select
                  className="select"
                  value={complexity}
                  onChange={(e) => setComplexity(+e.target.value)}
                >
                  {Object.entries(COMPLEXITY_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="btn btn-primary btn-block"
                onClick={handleParse}
                disabled={!file || loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" /> Đang parse...
                  </>
                ) : (
                  " Parse & Xem trước"
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Preview */
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "1.5rem",
              }}
            >
              <div>
                <h2 style={{ marginBottom: "0.25rem" }}>
                  Xem trước — {countText}
                </h2>
                <p
                  style={{
                    color: "var(--text-secondary)",
                    fontSize: "0.875rem",
                  }}
                >
                  Kiểm tra và chỉnh sửa trước khi lưu vào database
                </p>
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => setPreview([])}
                >
                  ← Hủy
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleConfirm}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" /> Đang lưu...
                    </>
                  ) : (
                    ` Lưu ${countText}`
                  )}
                </button>
              </div>
            </div>

            {(() => {
              const groupedPreview: any[] = [];
              let currentParent: any = null;

              for (let i = 0; i < preview.length; i++) {
                const item = preview[i];
                if (item.table_question.question_type === "st") {
                  const newItem = { ...item, originalIdx: i, children: [] };
                  groupedPreview.push(newItem);
                  currentParent = newItem;
                } else if (
                  item.table_question.parent_id &&
                  currentParent &&
                  currentParent.table_question.public_id ===
                    item.table_question.parent_id
                ) {
                  currentParent.children.push({ ...item, originalIdx: i });
                } else {
                  groupedPreview.push({ ...item, originalIdx: i });
                }
              }

              let displayCounter = 1;

              const renderItem = (
                item: any,
                displayNum: number | string,
                isChild: boolean = false,
              ) => {
                const q = item.table_question;
                const qtype = String(q.question_type);
                const originalIdx = item.originalIdx;
                const options = item.table_details?.records || [];

                const children = isChild ? [] : item.children || [];

                if (qtype === "st") {
                  const children = item.children || [];
                  const stRange =
                    children.length > 0
                      ? `Dựa vào thông tin dưới đây để trả lời từ câu ${Number(displayNum)} đến câu ${Number(displayNum) + children.length - 1}`
                      : null;
                  return (
                    <div
                      key={originalIdx}
                      style={{
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-lg)",
                        background: "var(--bg-card)",
                        overflow: "hidden",
                        marginBottom: "1.5rem",
                      }}
                    >
                      {/* ST header: content + buttons column */}
                      <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem", padding: "1.5rem", background: "rgba(78,205,196,0.05)", borderBottom: "2px dashed var(--border)", borderLeft: "4px solid var(--accent-primary)" }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          {stRange && (
                            <div style={{ fontWeight: 700, marginBottom: "0.75rem", color: "var(--accent-primary)", fontSize: "1.1rem" }}>
                              {stRange}
                            </div>
                          )}
                          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                            <span style={{ fontSize: "0.75rem", fontWeight: 600, padding: "0.2rem 0.5rem", borderRadius: 99, background: `${TYPE_COLORS[qtype] || "#ccc"}20`, color: TYPE_COLORS[qtype] || "var(--accent-primary)", border: `1px solid ${TYPE_COLORS[qtype] || "#ccc"}40` }}>
                              {TYPE_LABELS[qtype] || qtype}
                            </span>
                            <div style={{ position: "relative", display: "inline-block" }}>
                              <span className={`badge complexity-${q.complexity}`} style={{ paddingRight: "1.5rem" }}>{COMPLEXITY_LABELS[q.complexity as number]}</span>
                              <select style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", opacity: 0, cursor: "pointer" }} value={Number(q.complexity) || 1} onChange={(e) => updateItem(originalIdx, "complexity", +e.target.value)}>
                                {Object.entries(COMPLEXITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                              </select>
                              <span style={{ position: "absolute", right: "0.4rem", top: "50%", transform: "translateY(-50%)", fontSize: "0.6rem", pointerEvents: "none", color: "inherit" }}>▼</span>
                            </div>
                            <Combobox className="select" style={{ width: "100px" }} value={q.grade || grade} onChange={(val) => updateItem(originalIdx, "grade", +val)} options={gradeList.map(g => ({ value: g, label: `Lớp ${g}` }))} placeholder="Lớp" />
                            <Combobox className="select" style={{ flex: 1, minWidth: "150px" }} value={q.chapter || ""} onChange={(val) => updateItem(originalIdx, "chapter", val)} options={Object.keys(((subjects as any)?.[subject]?.[q.grade || grade] || {}))} placeholder="Chương" />
                            <Combobox className="select" style={{ flex: 1, minWidth: "150px" }} value={q.lesson || ""} onChange={(val) => updateItem(originalIdx, "lesson", val)} options={(((subjects as any)?.[subject]?.[q.grade || grade]?.[q.chapter || ""] || []))} placeholder="Bài" />
                          </div>
                          <LatexRenderer content={String(q.content || "")} layoutType={String(q.layout_type || "normal")} images={q.image || q.images} className="question-content" />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", flexShrink: 0 }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => openEdit(originalIdx, false)}>Chi tiết</button>
                          <button className="btn btn-danger btn-sm" onClick={() => removeItem(originalIdx)}>Xóa</button>
                        </div>
                      </div>
                      {/* ST children */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
                        {children.map((child: any, cIdx: number) => (
                          <div key={cIdx} style={{ borderTop: cIdx > 0 ? "1px solid var(--border)" : "none" }}>
                            {renderItem(child, Number(displayNum) + cIdx, true)}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={originalIdx}
                    style={
                      isChild
                        ? { padding: "1.5rem", background: "var(--bg-surface)" }
                        : {
                            padding: "1.25rem",
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius-lg)",
                            boxShadow: "var(--shadow-sm)",
                            marginBottom: "1.5rem",
                          }
                    }
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        gap: "0.75rem",
                        alignItems: "center",
                        marginBottom: "0.5rem",
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 700,
                          color: "var(--accent-primary)",
                          fontSize: "1.1rem",
                        }}
                      >
                        Câu {displayNum}
                      </span>
                      {!isChild && (
                        <div
                          style={{
                            display: "flex",
                            gap: "0.5rem",
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <span
                            style={{
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              padding: "0.2rem 0.6rem",
                              borderRadius: 99,
                              background: `${TYPE_COLORS[qtype] || "#ccc"}20`,
                              color:
                                TYPE_COLORS[qtype] || "var(--accent-primary)",
                              border: `1px solid ${TYPE_COLORS[qtype] || "#ccc"}40`,
                            }}
                          >
                            {TYPE_LABELS[qtype] || qtype}
                          </span>
                          <div style={{ position: "relative", display: "inline-block" }}>
                            <span className={`badge complexity-${q.complexity}`} style={{ paddingRight: "1.5rem" }}>
                              {COMPLEXITY_LABELS[q.complexity as number]}
                            </span>
                            <select
                              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", opacity: 0, cursor: "pointer" }}
                              value={Number(q.complexity) || 1}
                              onChange={(e) => updateItem(originalIdx, "complexity", +e.target.value)}
                            >
                              {Object.entries(COMPLEXITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                            </select>
                            <span style={{ position: "absolute", right: "0.4rem", top: "50%", transform: "translateY(-50%)", fontSize: "0.6rem", pointerEvents: "none", color: "inherit" }}>▼</span>
                          </div>
                          <Combobox className="select" style={{ width: "100px" }} value={q.grade || grade} onChange={(val) => updateItem(originalIdx, "grade", +val)} options={gradeList.map(g => ({ value: g, label: `Lớp ${g}` }))} placeholder="Lớp" />
                          <Combobox className="select" style={{ flex: 1, minWidth: "150px" }} value={q.chapter || ""} onChange={(val) => updateItem(originalIdx, "chapter", val)} options={Object.keys(((subjects as any)?.[subject]?.[q.grade || grade] || {}))} placeholder="Chương" />
                          <Combobox className="select" style={{ flex: 1, minWidth: "150px" }} value={q.lesson || ""} onChange={(val) => updateItem(originalIdx, "lesson", val)} options={(((subjects as any)?.[subject]?.[q.grade || grade]?.[q.chapter || ""] || []))} placeholder="Bài" />
                        </div>
                      )}
                    </div>

                    <LatexRenderer
                      content={String(q.content || "")}
                      layoutType={String(q.layout_type || "normal")}
                      images={q.image || q.images}
                      className="question-content"
                    />

                    {qtype === "mc" &&
                      options.length > 0 &&
                      (() => {
                        const maxLen = Math.max(
                          0,
                          ...options.map(
                            (o: any) => String(o.content || "").length,
                          ),
                        );
                        const nOpts = options.length;
                        let optColsClass = "";
                        if (nOpts >= 4 && maxLen < 20) optColsClass = "mc-options-4";
                        else if (nOpts >= 2 && maxLen < 40) optColsClass = "mc-options-2";

                        return (
                          <div
                            className={`mc-options-grid ${optColsClass}`}
                            style={{ marginLeft: "1rem", marginTop: "1rem" }}
                          >
                            {options.map((opt: any, oi: number) => {
                              let bg = "var(--bg-elevated)";
                              let border = "transparent";
                              let textColor = "var(--text-secondary)";
                              if (opt.is_correct) {
                                bg = "rgba(107,203,119,0.1)";
                                border = "var(--accent-success)";
                                textColor = "var(--accent-success)";
                              }
                              return (
                                <div
                                  key={oi}
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.5rem",
                                    padding: "0.4rem 0.75rem",
                                    borderRadius: "var(--radius-md)",
                                    background: bg,
                                    border: `1px solid ${border}`,
                                  }}
                                >
                                  <div
                                    style={{
                                      fontWeight: 700,
                                      color: textColor,
                                    }}
                                  >
                                    {String.fromCharCode(65 + oi)}.
                                  </div>
                                  <div style={{ flex: 1, minWidth: 0 }}>
                                      <LatexRenderer
                                        content={String(opt.content || "")}
                                        images={q.image || q.images}
                                      />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()}

                    {qtype === "tf" && options.length > 0 && (
                      <div
                        style={{
                          marginLeft: "1rem",
                          marginTop: "1rem",
                          display: "flex",
                          flexDirection: "column",
                          gap: "0.5rem",
                        }}
                      >
                        {options.map((opt: any, oi: number) => (
                          <div
                            key={oi}
                            style={{
                              display: "flex",
                              gap: "0.75rem",
                              alignItems: "center",
                              padding: "0.5rem 0.75rem",
                              borderRadius: "var(--radius-md)",
                              background: opt.is_correct
                                ? "rgba(107,203,119,0.1)"
                                : "rgba(255,107,107,0.1)",
                              border: `1px solid ${opt.is_correct ? "var(--accent-success)" : "var(--accent-danger)"}`,
                            }}
                          >
                            <div
                              style={{
                                fontWeight: 700,
                                color: "var(--text-secondary)",
                              }}
                            >
                              {String.fromCharCode(97 + oi)})
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <LatexRenderer
                                content={String(opt.content || "")}
                                images={q.image || q.images}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {qtype === "sa" &&
                      options.length > 0 &&
                      (() => {
                        const rawAns = String(options[0].content || "")
                          .replace(/\$/g, "")
                          .replace(/[{}]/g, "")
                          .trim();
                        const chars = rawAns.split("");
                        const boxes = Array.from({
                          length: Math.max(4, chars.length),
                        }).map((_, i) => chars[i] || "");

                        return (
                          <div
                            style={{
                              marginTop: "0.75rem",
                              padding: "0.5rem 0.75rem",
                              background: "rgba(255,217,61,0.1)",
                              border: "1px solid var(--accent-warning)",
                              borderRadius: "var(--radius-md)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.75rem",
                            }}
                          >
                            <span
                              style={{
                                fontWeight: 600,
                                color: "var(--accent-warning)",
                              }}
                            >
                              Trả lời ngắn:
                            </span>
                            <div style={{ display: "flex", gap: "0.25rem" }}>
                              {boxes.map((c, i) => (
                                <div
                                  key={i}
                                  style={{
                                    width: "25px",
                                    height: "27px",
                                    border: "2px solid var(--accent-warning)",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontWeight: 700,
                                    borderRadius: "4px",
                                    background: "#fff",
                                    color: "var(--text-primary)",
                                  }}
                                >
                                  {c}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })()}

                    {/* Solution */}
                    {((q.solution && qtype !== "tf") ||
                      (qtype === "tf" && options.length > 0)) && (
                      <div
                        style={{
                          marginTop: "1.5rem",
                          marginLeft: "1rem",
                          padding: "1rem",
                          background: "var(--bg-surface)",
                          borderLeft: "4px solid var(--accent-secondary)",
                          borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
                        }}
                      >
                        <div
                          style={{
                            fontWeight: 700,
                            marginBottom: "0.5rem",
                            color: "var(--accent-secondary)",
                          }}
                        >
                          Lời giải:
                        </div>
                        {qtype === "tf" && options.length > 0 && (
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: "0.5rem",
                              marginBottom: q.solution ? "1rem" : "0",
                            }}
                          >
                            {options.map((opt: any, oi: number) => (
                              <div
                                key={oi}
                                style={{ display: "flex", gap: "0.5rem" }}
                              >
                                <strong>
                                  {String.fromCharCode(97 + oi)}){" "}
                                  {opt.is_correct ? "Đúng." : "Sai."}
                                </strong>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  {opt.explaination && (
                                    <LatexRenderer
                                      content={String(opt.explaination)}
                                      images={q.image || q.images}
                                    />
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                          {q.solution && (
                            <LatexRenderer content={String(q.solution)} images={q.image || q.images} />
                          )}
                      </div>
                    )}
                      </div>{/* end flex-1 content */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", flexShrink: 0 }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => openEdit(originalIdx, isChild, isChild ? Number(displayNum) : undefined)}
                        >
                          Chi tiết
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => removeItem(originalIdx)}
                        >
                          Xóa
                        </button>
                      </div>
                    </div>{/* end flex row */}
                  </div>
                );
              };

              return groupedPreview.map((item) => {
                let currentDisplayCounter = displayCounter;
                const el = renderItem(item, currentDisplayCounter);

                if (item.table_question.question_type === "st") {
                  displayCounter += item.children ? item.children.length : 0;
                } else {
                  displayCounter++;
                }
                return el;
              });
            })()}

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "0.75rem",
                marginTop: "1.5rem",
              }}
            >
              <button
                className="btn btn-secondary"
                onClick={() => setPreview([])}
              >
                ← Hủy
              </button>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleConfirm}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" /> Đang lưu...
                  </>
                ) : (
                  ` Lưu ${countText} vào database`
                )}
              </button>
            </div>
          </div>
        )}
        {/* Edit modal — fixed overlay so page scroll is never affected */}
        {editModal && (
          <div
            style={{
              position: "fixed", inset: 0, zIndex: 1000,
              background: "rgba(0,0,0,0.5)",
              display: "flex", alignItems: "flex-start", justifyContent: "center",
              padding: "2rem",
              overflowY: "auto",
            }}
            onMouseDown={(e) => { if (e.target === e.currentTarget) setEditModal(null); }}
          >
            <div
              style={{
                width: "100%", maxWidth: 900,
                background: "var(--bg-surface)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-lg)",
                marginBottom: "2rem",
              }}
            >
              <div
                style={{
                  padding: "1rem 1.5rem",
                  borderBottom: "1px solid var(--border)",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}
              >
                <h3 style={{ margin: 0 }}>Chi tiết câu hỏi</h3>
                <button
                  onClick={() => setEditModal(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "var(--text-secondary)", lineHeight: 1, padding: 4 }}
                >
                  ✕
                </button>
              </div>

              <div style={{ padding: "1.5rem" }}>
                <QuestionEditor
                  qData={editModal.draft}
                  onChange={(newDraft) => setEditModal((m) => m ? { ...m, draft: newDraft } : m)}
                  isChild={editModal.isChild}
                  childIndex={editModal.childIndex}
                  imageEditable={true}
                />
              </div>

              <div
                style={{
                  padding: "1rem 1.5rem",
                  borderTop: "1px solid var(--border)",
                  display: "flex", justifyContent: "flex-end", gap: "0.75rem",
                }}
              >
                <button className="btn btn-secondary" onClick={() => setEditModal(null)}>
                  Hủy bỏ
                </button>
                <button className="btn btn-primary" onClick={saveEdit}>
                  Lưu
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
