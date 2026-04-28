import React from "react";
import Combobox from "@/components/Combobox";
import RichLatexEditor from "@/components/RichLatexEditor";

export type QuestionDetail = {
  id?: number;
  subject?: string;
  grade?: number;
  chapter?: string;
  lesson?: string;
  question_type: string;
  complexity?: number;
  content: string;
  solution?: string;
  teacher_name?: string;
  images?: { storage_path: string; img_scale?: number; img_type?: string }[];
  details?: { id?: number; content: string; is_correct?: boolean }[];
  children?: QuestionDetail[];
};

const TYPE_LABELS: Record<string, string> = {
  mc: "Trắc nghiệm",
  tf: "Đúng/Sai",
  sa: "Trả lời ngắn",
  oe: "Tự luận",
  st: "Câu chung giả thiết",
};
const COMPLEXITY_LABELS: Record<number, string> = {
  1: "Nhận biết",
  2: "Thông hiểu",
  3: "Vận dụng",
  4: "Vận dụng cao",
};

export const QuestionEditor = ({
  qData,
  onChange,
  onDelete,
  isChild = false,
  childIndex = 0,
  curriculum = {},
  metadata = { chapters: [], lessons: [] },
  imageEditable = false,
}: {
  qData: QuestionDetail;
  onChange: (q: QuestionDetail) => void;
  onDelete?: () => void;
  isChild?: boolean;
  childIndex?: number;
  curriculum?: any;
  metadata?: { chapters: string[]; lessons: string[] };
  imageEditable?: boolean;
}) => {
  const handleChange = (field: keyof QuestionDetail, value: any) => {
    onChange({ ...qData, [field]: value });
  };

  const handleDetailChange = (idx: number, field: string, value: any) => {
    const newDetails = [...(qData.details || [])];
    newDetails[idx] = { ...newDetails[idx], [field]: value };
    onChange({ ...qData, details: newDetails });
  };

  const subjOptions = Array.from(new Set(Object.keys(curriculum || {})));

  const gradeOptions = Array.from(
    new Set(
      qData.subject && curriculum[qData.subject]
        ? Object.keys(curriculum[qData.subject])
        : ["10", "11", "12"],
    ),
  );

  const currChapters =
    qData.subject && qData.grade && curriculum[qData.subject]?.[qData.grade]
      ? Object.keys(curriculum[qData.subject][qData.grade])
      : [];
  const chapterOptions = Array.from(
    new Set([...currChapters, ...metadata.chapters]),
  );

  const currLessons =
    qData.subject &&
    qData.grade &&
    qData.chapter &&
    curriculum[qData.subject]?.[qData.grade]?.[qData.chapter]
      ? curriculum[qData.subject][qData.grade][qData.chapter]
      : [];
  const lessonOptions = Array.from(
    new Set([...currLessons, ...metadata.lessons]),
  );

  return (
    <div
      className="card"
      style={{
        marginBottom: "1.5rem",
        border: isChild ? "1px solid var(--border)" : "none",
        background: isChild ? "var(--bg-card)" : "var(--bg-surface)",
      }}
    >
      <div
        className="card-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h3 style={isChild ? { color: "var(--accent-primary)" } : {}}>
          {isChild
            ? `Câu ${childIndex}${qData.id ? ` #${qData.id}` : ""}`
            : `Nội dung câu hỏi ${qData.id ? `#${qData.id}` : ""}`}
        </h3>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <span className={`badge badge-${qData.question_type}`}>
            {TYPE_LABELS[qData.question_type] || qData.question_type}
          </span>
          {!isChild && qData.question_type === "st" && qData.children && (
            Array.from(new Set(qData.children.map(c => c.question_type))).map(t => (
              <span key={t} className={`badge badge-${t}`}>
                {TYPE_LABELS[t] || t}
              </span>
            ))
          )}
          {onDelete && (
            <button
              className="btn btn-danger btn-sm"
              onClick={onDelete}
              title="Xóa câu hỏi này"
              style={{ padding: "0.25rem 0.75rem", fontSize: "0.85rem" }}
            >
              Xóa
            </button>
          )}
        </div>
      </div>

      <div
        style={{
          padding: "1.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.5rem",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "1rem",
          }}
        >
          {!isChild && (
            <>
              <div className="form-group">
                <label className="form-label">Môn học</label>
                <Combobox className="select" value={qData.subject || ""} onChange={(val) => handleChange("subject", val)} options={subjOptions} placeholder="Môn học" />
              </div>
              <div className="form-group">
                <label className="form-label">Khối lớp</label>
                <Combobox className="select" value={qData.grade || ""} onChange={(val) => handleChange("grade", parseInt(val) || 0)} options={gradeOptions} placeholder="Khối lớp" />
              </div>
            </>
          )}
          <div className="form-group">
            <label className="form-label">Chương</label>
            <Combobox className="select" value={qData.chapter || ""} onChange={(val) => handleChange("chapter", val)} options={chapterOptions} placeholder="Chương" />
          </div>
          <div className="form-group">
            <label className="form-label">Bài học</label>
            <Combobox className="select" value={qData.lesson || ""} onChange={(val) => handleChange("lesson", val)} options={lessonOptions} placeholder="Bài học" />
          </div>
          <div className="form-group">
            <label className="form-label">Mức độ</label>
            <Combobox className="select" value={qData.complexity || 1} onChange={(val) => handleChange("complexity", parseInt(val))} options={Object.entries(COMPLEXITY_LABELS).map(([k, v]) => ({ value: +k, label: v }))} placeholder="Mức độ" />
          </div>
        </div>

        <div>
          <label className="form-label">Nội dung đề bài</label>
          <RichLatexEditor
            content={qData.content || ""}
            onChange={(val) => handleChange("content", val)}
            imageEditable={imageEditable}
            images={qData.images}
          />
        </div>



        {qData.details && qData.details.length > 0 && qData.question_type === "sa" && (
          <div>
            <label className="form-label">Đáp án</label>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {qData.details.map((det, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
                  <span style={{ fontWeight: 600, whiteSpace: "nowrap", color: "var(--text-secondary)", paddingTop: "0.75rem" }}>
                    Trả lời ngắn:
                  </span>
                  <div style={{ flex: 1 }}>
                    <RichLatexEditor
                      content={det.content || ""}
                      onChange={(val) => handleDetailChange(idx, "content", val)}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {qData.details && qData.details.length > 0 && qData.question_type !== "sa" && (
          <div>
            <label className="form-label">Các lựa chọn / Chi tiết đáp án</label>
            <div
              style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
            >
              {qData.details.map((det, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "1rem",
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "0.5rem",
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>Lựa chọn {idx + 1}</span>
                    {qData.question_type === "mc" && (
                      <label
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          cursor: "pointer",
                        }}
                      >
                        <input
                          type="radio"
                          name={`correct_${qData.id}_${isChild ? childIndex : "parent"}`}
                          checked={det.is_correct}
                          onChange={() => {
                            const newDetails = qData.details!.map((d, i) => ({
                              ...d,
                              is_correct: i === idx,
                            }));
                            onChange({ ...qData, details: newDetails });
                          }}
                        />
                        <span
                          style={{
                            color: det.is_correct
                              ? "var(--accent-success)"
                              : "inherit",
                            fontWeight: det.is_correct ? 700 : 400,
                          }}
                        >
                          Đáp án đúng
                        </span>
                      </label>
                    )}
                    {qData.question_type === "tf" && (
                      <label
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          cursor: "pointer",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={det.is_correct}
                          onChange={(e) =>
                            handleDetailChange(
                              idx,
                              "is_correct",
                              e.target.checked,
                            )
                          }
                        />
                        <span
                          style={{
                            color: det.is_correct
                              ? "var(--accent-success)"
                              : "inherit",
                            fontWeight: det.is_correct ? 700 : 400,
                          }}
                        >
                          ĐÚNG
                        </span>
                      </label>
                    )}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "1rem",
                      alignItems: "flex-start",
                    }}
                  >
                    <div style={{ fontWeight: 700, marginTop: "0.5rem" }}>
                      {String.fromCharCode(65 + idx)}.
                    </div>
                    <div
                      style={{
                        flex: 1,
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.5rem",
                      }}
                    >
                      <RichLatexEditor
                        content={det.content || ""}
                        onChange={(val) =>
                          handleDetailChange(idx, "content", val)
                        }
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(qData.solution !== undefined || qData.question_type !== "st") && (
          <div>
            <label className="form-label">Lời giải chi tiết</label>
            <RichLatexEditor
              content={qData.solution || ""}
              onChange={(val) => handleChange("solution", val)}
            />
          </div>
        )}

        {!isChild && qData.question_type === "st" && (
          <div style={{ marginTop: "1rem", borderTop: "2px dashed var(--border)", paddingTop: "1.5rem" }}>
            <div style={{ marginBottom: "1.5rem" }}>
              <h3 style={{ margin: 0, paddingLeft: "0.5rem", borderLeft: "4px solid var(--accent-primary)" }}>
                Các câu hỏi con
              </h3>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              {(qData.children || []).map((child, idx) => (
                <QuestionEditor
                  key={idx}
                  qData={child}
                  onChange={(newChild) => {
                    const newChildren = [...(qData.children || [])];
                    newChildren[idx] = newChild;
                    onChange({ ...qData, children: newChildren });
                  }}
                  onDelete={() => {
                    if (!confirm("Xóa câu hỏi con này?")) return;
                    const newChildren = [...(qData.children || [])];
                    newChildren.splice(idx, 1);
                    onChange({ ...qData, children: newChildren });
                  }}
                  isChild={true}
                  childIndex={idx + 1}
                  curriculum={curriculum}
                  metadata={metadata}
                  imageEditable={imageEditable}
                />
              ))}
              {(!qData.children || qData.children.length === 0) && (
                <div style={{ textAlign: "center", padding: "2rem", background: "var(--bg-elevated)", color: "var(--text-muted)", borderRadius: "var(--radius-md)" }}>
                  Chưa có câu hỏi con.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
