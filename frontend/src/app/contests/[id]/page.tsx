'use client';

import { useEffect, useState, use } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import LatexRenderer from '@/components/LatexRenderer';
import api from '@/lib/api';
import Link from 'next/link';
import { QuestionEditor, QuestionDetail } from '@/components/QuestionEditor';
import ExportContestModal from '@/components/ExportContestModal';

type QuestionInContest = {
  id: number;
  question_type: string;
  content: string;
  layout_type: string;
  original_order: number;
  point_weight: number;
  chapter?: string;
  lesson?: string;
  complexity?: number;
  parent_id?: number | null;
  children?: QuestionInContest[];
  images?: { storage_path: string; img_scale?: number; img_type?: string }[];
};

type Contest = {
  id: number;
  title: string;
  time_limit: number;
  status: string;
  public_id: string;
  class_id?: number;
  scoring_config?: Record<string, number>;
};

const TYPE_LABELS: Record<string, string> = {
  mc: 'Trắc nghiệm',
  tf: 'Đúng/Sai',
  sa: 'Trả lời ngắn',
  oe: 'Tự luận',
  st: 'Chung giả thiết',
};

const TYPE_COLORS: Record<string, string> = {
  mc: '#6c63ff',
  tf: '#f59e0b',
  sa: '#10b981',
  oe: '#3b82f6',
  st: '#ec4899',
};

const COMPLEXITY_LABELS: Record<number, string> = {
  1: 'Nhận biết',
  2: 'Thông hiểu',
  3: 'Vận dụng',
  4: 'Vận dụng cao',
};

export default function ContestDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  // Safe unwrap for params in Next.js 14 vs 15
  const { id } = params instanceof Promise ? use(params) : (params as any);
  const contestId = parseInt(id);

  const [contest, setContest] = useState<Contest | null>(null);
  const [questions, setQuestions] = useState<QuestionInContest[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toggling, setToggling] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showSubmissions, setShowSubmissions] = useState(false);
  const [showEditContestModal, setShowEditContestModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [editContestData, setEditContestData] = useState({ title: '', time_limit: 0 });
  const [detailModal, setDetailModal] = useState<{ question: QuestionDetail; saving: boolean; error: string; displayNumStr: string } | null>(null);
  const [subjects, setSubjects] = useState<Record<string, unknown>>({});

  useEffect(() => {
    api.getSubjects().then(setSubjects).catch(() => { });
  }, []);

  useEffect(() => {
    if (!isLoading && !user) router.replace('/');
    if (!isLoading && user?.role !== 'teacher') router.replace('/contests');
  }, [user, isLoading, router]);

  useEffect(() => {
    Promise.all([
      api.getContest(contestId),
      api.getContestSubmissions(contestId).catch(() => ({ submissions: [] }))
    ]).then(([res, subRes]) => {
      setContest(res.contest as Contest);
      setQuestions((res.questions || []) as QuestionInContest[]);
      setSubmissions(subRes.submissions || []);
    })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [contestId]);

  const toggleStatus = async () => {
    if (!contest) return;
    setToggling(true);
    const newStatus = contest.status === 'active' ? 'inactive' : 'active';
    try {
      await api.updateContestStatus(contest.id, newStatus);
      setContest(prev => prev ? { ...prev, status: newStatus } : prev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Lỗi cập nhật trạng thái');
    } finally {
      setToggling(false);
    }
  };

  const handleOpenEditContest = () => {
    if (!contest) return;
    setEditContestData({ title: contest.title, time_limit: contest.time_limit });
    setShowEditContestModal(true);
  };

  const handleSaveContest = async () => {
    if (!contest) return;
    try {
      await api.updateContest(contest.id, editContestData);
      setContest({ ...contest, title: editContestData.title, time_limit: editContestData.time_limit });
      setShowEditContestModal(false);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Lỗi cập nhật đề thi');
    }
  };

  const examUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/exam/${contestId}`
    : '';

  const copyLink = () => {
    navigator.clipboard.writeText(examUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const openDetail = async (questionId: number, displayNumStr: string) => {
    if (user?.role !== 'teacher') return;
    try {
      const q = await api.getQuestion(questionId);
      setDetailModal({ question: q, saving: false, error: '', displayNumStr });
    } catch { /* ignore */ }
  };

  const saveDetail = async () => {
    if (!detailModal) return;
    if (!confirm('Bạn có chắc chắn muốn lưu?\n\nLưu ý: Việc thay đổi sẽ ảnh hưởng đến TOÀN BỘ các đề thi khác đang chứa câu hỏi này!')) return;

    setDetailModal(d => d ? { ...d, saving: true, error: '' } : d);
    try {
      const q = detailModal.question;
      await api.updateQuestion(q.id!, {
        subject: q.subject, grade: q.grade, chapter: q.chapter,
        lesson: q.lesson, complexity: q.complexity,
        content: q.content, solution: q.solution,
        details: q.details?.map((d: any) => ({ id: d.id, content: d.content, is_correct: d.is_correct })),
      });

      if (q.question_type === 'st' && q.children && q.children.length > 0) {
        for (const child of q.children) {
          if (child.id) {
            await api.updateQuestion(child.id, {
              subject: child.subject, grade: child.grade, chapter: child.chapter,
              lesson: child.lesson, complexity: child.complexity,
              content: child.content, solution: child.solution,
              details: child.details?.map((d: any) => ({ id: d.id, content: d.content, is_correct: d.is_correct })),
            });
          }
        }
      }

      setDetailModal(null);
      const res = await api.getContest(contestId);
      setQuestions(res.questions as QuestionInContest[]);
    } catch (e: any) {
      setDetailModal(d => d ? { ...d, saving: false, error: e.message || 'Lỗi lưu câu hỏi' } : d);
    }
  };

  const questionCounts = questions.reduce((acc, q) => {
    acc[q.question_type] = (acc[q.question_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const actualQuestions = questions.filter(q => q.question_type !== 'st');
  const summaryParts = [];
  if (questionCounts.mc > 0) summaryParts.push(`${questionCounts.mc} TN`);
  if (questionCounts.tf > 0) summaryParts.push(`${questionCounts.tf} ĐS`);
  if (questionCounts.sa > 0) summaryParts.push(`${questionCounts.sa} TLN`);
  if (questionCounts.oe > 0) summaryParts.push(`${questionCounts.oe} TL`);
  const summaryText = actualQuestions.length > 0 ? `${actualQuestions.length} câu` + (summaryParts.length > 0 ? ` (${summaryParts.join(', ')})` : '') : '0 câu';

  const topLevelQs = questions.filter(q => q.question_type === 'st' || !q.parent_id);
  topLevelQs.forEach(q => {
    if (q.question_type === 'st') {
      q.children = questions.filter(c => c.parent_id === q.id);
    }
  });

  const sortOrder = { mc: 1, tf: 2, sa: 3, oe: 4, st: 5 };
  const getSortType = (q: any) => {
    if (q.question_type === 'st' && q.children && q.children.length > 0) {
      return q.children[0].question_type;
    }
    return q.question_type;
  };
  const sortedTopLevelQs = [...topLevelQs].sort((a, b) => (sortOrder[getSortType(a) as keyof typeof sortOrder] || 99) - (sortOrder[getSortType(b) as keyof typeof sortOrder] || 99));

  let currentQuestionIndex = 1;
  const renderedQuestions = sortedTopLevelQs.map(q => {
    const isSt = q.question_type === 'st';
    const childCount = q.children ? q.children.length : 0;
    const startIdx = currentQuestionIndex;
    const endIdx = isSt ? currentQuestionIndex + childCount - 1 : currentQuestionIndex;

    if (isSt) {
      currentQuestionIndex += childCount;
    } else {
      currentQuestionIndex += 1;
    }

    return { ...q, startIdx, endIdx };
  });

  if (loading) return (
    <div className="page-wrapper">
      <Sidebar />
      <main className="main-content">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingTop: '2rem' }}>
          {[1, 2, 3, 4].map(i => <div key={i} className="skeleton" style={{ height: '80px', borderRadius: 'var(--radius-lg)' }} />)}
        </div>
      </main>
    </div>
  );

  if (error || !contest) return (
    <div className="page-wrapper">
      <Sidebar />
      <main className="main-content">
        <div className="alert alert-error">{error || 'Không tìm thấy đề thi'}</div>
        <Link href="/contests" className="btn btn-ghost" style={{ marginTop: '1rem' }}>← Quay lại</Link>
      </main>
    </div>
  );

  return (
    <div className="page-wrapper">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
              <Link href="/contests" style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textDecoration: 'none' }}>
                ← Đề thi
              </Link>
              <span style={{ color: 'var(--border)' }}>/</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Chi tiết</span>
            </div>
            <h1 className="page-title">{contest.title}</h1>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <Link href={`/exam/${contestId}`} className="btn btn-ghost btn-sm" target="_blank">
              Xem trước
            </Link>
            <button className="btn btn-secondary btn-sm" onClick={handleOpenEditContest}>
              Chỉnh sửa
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowExportModal(true)}>
              Xuất đề
            </button>
            <button
              className={`btn btn-sm ${contest.status === 'active' ? 'btn-danger' : 'btn-primary'}`}
              onClick={toggleStatus}
              disabled={toggling}
            >
              {toggling ? <span className="spinner" /> : contest.status === 'active' ? ' Đóng đề' : ' Mở đề'}
            </button>
          </div>
        </div>



        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '1.5rem', alignItems: 'start' }}>
          {/* Question list */}
          <div className="card">
            <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>
              Danh sách câu hỏi ({topLevelQs.length} mục - {actualQuestions.length} câu)
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {renderedQuestions.map((q) => (
                <div key={q.id}>
                  <div
                    onClick={() => {
                      if (q.question_type === 'st') openDetail(q.id, `${q.startIdx} - ${q.endIdx}`);
                      else openDetail(q.id, `${q.startIdx}`);
                    }}
                    style={{
                      cursor: user?.role === 'teacher' ? 'pointer' : 'default',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.875rem',
                      padding: '0.875rem',
                      background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)',
                      marginBottom: q.question_type === 'st' && q.children && q.children.length > 0 ? '0.5rem' : '0'
                    }}
                  >
                    {/* Order number */}
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                      background: q.question_type === 'st' ? 'rgba(236,72,153,0.15)' : 'rgba(108,99,255,0.12)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.75rem', fontWeight: 700,
                      color: TYPE_COLORS[q.question_type] || 'var(--accent-primary)',
                    }}>
                      {q.question_type === 'st' ? '' : q.startIdx}
                    </div>

                    {/* Content */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
                        <span style={{
                          fontSize: '0.7rem', fontWeight: 600, padding: '0.15rem 0.45rem',
                          borderRadius: 99, background: `${TYPE_COLORS[q.question_type] || '#ccc'}20`,
                          color: TYPE_COLORS[q.question_type] || 'var(--accent-primary)',
                          border: `1px solid ${TYPE_COLORS[q.question_type] || '#ccc'}40`,
                        }}>
                          {TYPE_LABELS[q.question_type] || q.question_type}
                        </span>
                        {q.question_type === 'st' && q.children && q.children.length > 0 && Array.from(new Set(q.children.map(c => c.question_type))).map((type: any) => (
                          <span key={type} style={{
                            fontSize: '0.7rem', fontWeight: 600, padding: '0.15rem 0.45rem',
                            borderRadius: 99, background: `${TYPE_COLORS[type] || '#ccc'}20`,
                            color: TYPE_COLORS[type] || 'var(--accent-primary)',
                            border: `1px solid ${TYPE_COLORS[type] || '#ccc'}40`,
                          }}>
                            {TYPE_LABELS[type] || type}
                          </span>
                        ))}
                        {q.chapter && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{q.chapter}</span>
                        )}
                        {q.complexity && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            • {COMPLEXITY_LABELS[q.complexity] || q.complexity}
                          </span>
                        )}
                      </div>
                      {q.question_type === 'st' && q.children && q.children.length > 0 && (
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                          Dựa vào thông tin sau để trả lời từ câu {q.startIdx} đến câu {q.endIdx}:
                        </div>
                      )}
                      <div style={{
                        fontSize: '0.825rem', color: 'var(--text-secondary)',
                        lineHeight: 1.5, maxHeight: '6em', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical'
                      }}>
                        <LatexRenderer content={q.content || ''} layoutType={q.layout_type} images={q.images} />
                      </div>
                    </div>

                    {/* Weight */}
                    <div style={{
                      fontSize: '0.75rem', color: 'var(--text-muted)',
                      flexShrink: 0, textAlign: 'right',
                    }}>
                      {q.point_weight > 0 ? `×${q.point_weight}` : ''}
                    </div>
                  </div>

                  {/* Children of ST */}
                  {q.question_type === 'st' && q.children && q.children.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                      {q.children.map((child, cIdx) => (
                        <div key={child.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            openDetail(q.id, `${q.startIdx} - ${q.endIdx}`);
                          }}
                          style={{ cursor: user?.role === 'teacher' ? 'pointer' : 'default', display: 'flex', alignItems: 'flex-start', gap: '0.75rem', padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                          <div style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0, background: 'rgba(108,99,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                            {q.startIdx + cIdx}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.5, maxHeight: '6em', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>
                              <LatexRenderer content={child.content || ''} layoutType={child.layout_type} images={child.images} />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {questions.length === 0 && (
                <div className="empty-state" style={{ padding: '2rem' }}>
                  <div className="empty-state-icon"></div>
                  <p>Chưa có câu hỏi nào trong đề thi</p>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar info */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* General info */}
            <div className="card" style={{ padding: '1.25rem' }}>
              <h4 style={{ marginBottom: '0.875rem', fontSize: '0.9rem' }}> Thông tin chung</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Thời gian</span>
                  <span style={{ fontWeight: 600 }}>{contest.time_limit} phút</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Trạng thái</span>
                  <span style={{ fontWeight: 600, color: contest.status === 'active' ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                    {contest.status === 'active' ? 'Đang mở' : 'Đóng'}
                  </span>
                </div>
              </div>
            </div>

            {/* Share link */}
            <div className="card" style={{ padding: '1.25rem' }}>
              <h4 style={{ marginBottom: '0.875rem', fontSize: '0.9rem' }}> Chia sẻ đề thi</h4>
              <div style={{
                background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
                padding: '0.625rem 0.75rem', fontSize: '0.75rem',
                color: 'var(--text-secondary)', wordBreak: 'break-all',
                border: '1px solid var(--border)', marginBottom: '0.75rem',
              }}>
                {examUrl || `…/exam/${contestId}`}
              </div>
              <button
                className={`btn btn-sm ${copied ? 'btn-secondary' : 'btn-primary'}`}
                style={{ width: '100%' }}
                onClick={copyLink}
              >
                {copied ? ' Đã sao chép!' : ' Sao chép đường dẫn'}
              </button>
            </div>

            {/* Question type breakdown */}
            <div className="card" style={{ padding: '1.25rem' }}>
              <h4 style={{ marginBottom: '0.875rem', fontSize: '0.9rem' }}> Phân loại câu hỏi</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {['mc', 'tf', 'sa', 'oe'].filter(type => questionCounts[type] > 0).map(type => (
                  <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: TYPE_COLORS[type] || 'var(--accent-primary)',
                      flexShrink: 0,
                    }} />
                    <span style={{ flex: 1, fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                      {TYPE_LABELS[type] || type}
                    </span>
                    <span style={{ fontSize: '0.825rem', fontWeight: 600 }}>{questionCounts[type]}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Scoring config */}
            {contest.scoring_config && (
              <div className="card" style={{ padding: '1.25rem' }}>
                <h4 style={{ marginBottom: '0.875rem', fontSize: '0.9rem' }}> Thang điểm</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {['mc', 'tf', 'sa', 'oe'].filter(type => contest.scoring_config![type] !== undefined).map(type => (
                    <div key={type} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{TYPE_LABELS[type] || type}</span>
                      <span style={{ fontWeight: 600 }}>{contest.scoring_config![type]} điểm/câu</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="card" style={{ padding: '1.25rem' }}>
              <h4 style={{ marginBottom: '0.875rem', fontSize: '0.9rem' }}> Thao tác</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <button onClick={() => setShowSubmissions(true)} className="btn btn-primary btn-sm" style={{ width: '100%' }}>
                  Xem danh sách đã nộp ({submissions.length})
                </button>
                <Link href={`/exam/${contestId}`} className="btn btn-ghost btn-sm" target="_blank"
                  style={{ textAlign: 'center' }}>
                  Xem trước bài thi
                </Link>
                <Link href={`/exam/${contestId}?guest=true`} className="btn btn-ghost btn-sm"
                  style={{ textAlign: 'center' }}>
                  Link cho học sinh (guest)
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Modal Submissions */}
      {showSubmissions && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000, padding: '1rem'
        }}>
          <div className="card" style={{
            width: '90vw', maxWidth: '1200px', height: '90vh',
            display: 'flex', flexDirection: 'column', padding: 0
          }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>Danh sách bài thi ({submissions.length})</h3>
              <button onClick={() => setShowSubmissions(false)} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0 }}>✕</button>
            </div>
            <div style={{ padding: '1.5rem', overflowY: 'auto' }}>
              {submissions.length === 0 ? (
                <div className="empty-state" style={{ minHeight: 'auto', padding: '2rem 0' }}>
                  <p>Chưa có bài nộp nào</p>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Thí sinh</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Thời gian nộp</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Điểm số</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.map((sub) => {
                        const endTime = sub.end_time ? new Date(sub.end_time).toLocaleString('vi-VN') : 'Đang làm';
                        return (
                          <tr key={sub.result_id} style={{ borderBottom: '1px solid var(--border)' }}>
                            <td style={{ padding: '0.75rem', fontWeight: 500 }}>{sub.student_name}</td>
                            <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>{endTime}</td>
                            <td style={{ padding: '0.75rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
                              {sub.total_score != null ? Number(sub.total_score).toFixed(2) : '-'}
                            </td>
                            <td style={{ padding: '0.75rem' }}>
                              <Link href={`/results/${sub.result_id}`} className="btn btn-secondary btn-sm">
                                Xem chi tiết
                              </Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Question Edit Modal */}
      {detailModal && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
          onMouseDown={(e) => { if (e.target === e.currentTarget) setDetailModal(null); }}
        >
          <div style={{ width: '90vw', maxWidth: '1200px', height: '90vh', background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <h3 style={{ margin: 0 }}>Đang chỉnh sửa: Câu {detailModal.displayNumStr}</h3>
              <button onClick={() => setDetailModal(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--text-secondary)', lineHeight: 1, padding: 4 }}>✕</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '1rem 1.5rem 0 1.5rem' }}>
                <div className="alert alert-error" style={{ margin: 0, display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 600, color: 'var(--accent-danger)' }}>
                  Lưu ý: Bạn đang sửa câu hỏi gốc trong ngân hàng. Việc thay đổi sẽ ảnh hưởng đến TOÀN BỘ các đề thi khác đang chứa câu hỏi này!
                </div>
              </div>

              <div style={{ padding: '1.5rem' }}>
                <QuestionEditor
                  qData={detailModal.question}
                  onChange={(q) => setDetailModal(d => d ? { ...d, question: q } : d)}
                  curriculum={subjects}
                  imageEditable={true}
                />
              </div>
              {detailModal.error && <div style={{ padding: '0 1.5rem 1rem', color: 'var(--accent-danger)', fontSize: '0.875rem' }}>{detailModal.error}</div>}
            </div>

            <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', flexShrink: 0 }}>
              <button className="btn btn-secondary" onClick={() => setDetailModal(null)}>Đóng</button>
              <button className="btn btn-primary" onClick={saveDetail} disabled={detailModal.saving}>
                {detailModal.saving ? 'Đang lưu...' : 'Lưu và Cập nhật toàn bộ'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Contest Modal */}
      {showExportModal && contest && (
        <ExportContestModal contest={{ id: contest.id, title: contest.title }} onClose={() => setShowExportModal(false)} />
      )}

      {showEditContestModal && contest && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div className="card" style={{ width: '90vw', maxWidth: '500px', display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1.5rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem' }}>Chỉnh sửa thông tin đề thi</h3>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem' }}>Tên đề thi</label>
              <input
                type="text"
                className="input"
                style={{ width: '100%' }}
                value={editContestData.title}
                onChange={(e) => setEditContestData({ ...editContestData, title: e.target.value })}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem' }}>Thời gian làm bài (phút)</label>
              <input
                type="number"
                className="input"
                style={{ width: '100%' }}
                value={editContestData.time_limit}
                onChange={(e) => setEditContestData({ ...editContestData, time_limit: parseInt(e.target.value) || 0 })}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => setShowEditContestModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleSaveContest}>Lưu thay đổi</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
