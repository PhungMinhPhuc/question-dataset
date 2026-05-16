'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import LatexRenderer from '@/components/LatexRenderer';
import api from '@/lib/api';

type Question = { id: number; content: string; question_type: string; chapter?: string; subject?: string; children?: any[]; parent_id?: number | null; };

export default function NewContestPage() {
 const { user, isLoading } = useAuth();
 const router = useRouter();

 const [title, setTitle] = useState('');
 const [timeLimit, setTimeLimit] = useState(45);
 const [classId, setClassId] = useState<number | ''>('');
 const [status, setStatus] = useState('inactive');
 const [scores, setScores] = useState({ mc: 0.25, tf: 1.0, sa: 0.25, oe: 2.0 });
 const [classes, setClasses] = useState<{id:number; class_name:string}[]>([]);

 // Question bank picking
 const [bankQuestions, setBankQuestions] = useState<Question[]>([]);
 const [selectedQuestions, setSelectedQuestions] = useState<Question[]>([]);
 const [search, setSearch] = useState('');
 const [qType, setQType] = useState('');
 const [bankLoading, setBankLoading] = useState(false);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState('');
 const [success, setSuccess] = useState('');

 useEffect(() => {
 if (!isLoading && (!user || user.role !== 'teacher')) router.replace('/dashboard');
 }, [user, isLoading, router]);

 useEffect(() => {
 api.getClasses().then(r => setClasses(r as {id:number; class_name:string}[])).catch(() => {});
 }, []);

 const fetchBank = useCallback(() => {
 setBankLoading(true);
 api.getQuestions({ search, question_type: qType, page_size: 50 })
  .then(r => setBankQuestions(r.data as Question[]))
  .catch(() => {})
  .finally(() => setBankLoading(false));
 }, [search, qType]);

 useEffect(() => { if (user) fetchBank(); }, [user, fetchBank]);

 const toggle = async (q: Question) => {
  const isSelected = selectedQuestions.some(x => x.id === q.id);
  if (isSelected) {
   setSelectedQuestions(prev => {
    let newSelected = prev.filter(x => x.id !== q.id);
    if (q.question_type === 'st' && q.children) {
     const childIds = q.children.map(c => c.id);
     newSelected = newSelected.filter(x => !childIds.includes(x.id));
    } else if (q.parent_id) {
     newSelected = newSelected.filter(x => x.id !== q.parent_id && x.parent_id !== q.parent_id);
    }
    return newSelected;
   });
  } else {
   if (q.question_type === 'st') {
    setSelectedQuestions(prev => {
     let newSelected = [...prev, q];
     if (q.children) {
      q.children.forEach(c => {
       if (!newSelected.some(x => x.id === c.id)) newSelected.push(c);
      });
     }
     return newSelected;
    });
   } else if (q.parent_id) {
    try {
     const parentQ = await api.getQuestion(q.parent_id) as Question;
     setSelectedQuestions(prev => {
      let newSelected = [...prev];
      if (!newSelected.some(x => x.id === parentQ.id)) newSelected.push(parentQ);
      if (parentQ.children) {
       parentQ.children.forEach((c: any) => {
        if (!newSelected.some(x => x.id === c.id)) newSelected.push(c);
       });
      }
      return newSelected;
     });
    } catch (err) {
     console.error(err);
    }
   } else {
    setSelectedQuestions(prev => [...prev, q]);
   }
  }
 };

 useEffect(() => {
  if (selectedQuestions.length > 0 && scores.sa === 0.25) {
   const hasMath = selectedQuestions.some(q => q.subject && q.subject.toLowerCase().includes('toán'));
   if (hasMath) {
    setScores(prev => ({ ...prev, sa: 0.5 }));
   }
  }
 }, [selectedQuestions]);

 const handleSubmit = async (e: React.FormEvent) => {
 e.preventDefault();
 if (selectedQuestions.length === 0) { setError('Vui lòng chọn ít nhất 1 câu hỏi'); return; }
 setLoading(true); setError('');
 let parsed: Record<string, unknown> = { ...scores };
 try {
  // Sort selected questions: mc -> tf -> sa -> oe -> st
  const order = { mc: 1, tf: 2, sa: 3, oe: 4, st: 5 };
  
  const getSortType = (q: Question) => {
   if (q.question_type === 'st' && q.children && q.children.length > 0) {
    return q.children[0].question_type;
   }
   return q.question_type;
  };

  const flattenedIds: number[] = [];
  const sortedSelected = [...selectedQuestions]
    .sort((a, b) => (order[getSortType(a) as keyof typeof order] || 99) - (order[getSortType(b) as keyof typeof order] || 99));

  sortedSelected.forEach(q => {
    flattenedIds.push(q.id);
    if (q.question_type === 'st' && q.children) {
      q.children.forEach(c => flattenedIds.push(c.id));
    }
  });
  
  const sortedIds = Array.from(new Set(flattenedIds));

  const res = await api.createContest({
  class_id: classId || null, title, time_limit: timeLimit,
  scoring_config: parsed, question_ids: sortedIds, status
  });
  setSuccess(` Tạo đề thi thành công! ID: ${res.id}`);
  setTimeout(() => router.push('/contests'), 1500);
 } catch (err: unknown) {
  setError(err instanceof Error ? err.message : 'Lỗi tạo đề thi');
 } finally { setLoading(false); }
 };

 const TYPE_LABELS: Record<string, string> = { mc: 'TN', tf: 'ĐS', sa: 'TLN', oe: 'TL', st: 'Chung giả thiết' };
 
 const typeCounts: Record<string, number> = { mc: 0, tf: 0, sa: 0, oe: 0 };
 let totalQs = 0;
 selectedQuestions.forEach(q => {
  if (q.question_type !== 'st') {
   totalQs++;
   if (typeCounts[q.question_type] !== undefined) {
    typeCounts[q.question_type]++;
   }
  }
 });
 const summaryParts = [];
 if (typeCounts.mc > 0) summaryParts.push(`${typeCounts.mc} TN`);
 if (typeCounts.tf > 0) summaryParts.push(`${typeCounts.tf} ĐS`);
 if (typeCounts.sa > 0) summaryParts.push(`${typeCounts.sa} TLN`);
 if (typeCounts.oe > 0) summaryParts.push(`${typeCounts.oe} TL`);
 const summaryText = totalQs > 0 ? `${totalQs} câu` + (summaryParts.length > 0 ? ` (${summaryParts.join(', ')})` : '') : '0 câu';
 
 const topLevelCount = selectedQuestions.filter(q => q.question_type === 'st' || !q.parent_id).length;

 return (
 <div className="page-wrapper">
  <Sidebar />
  <main className="main-content">
  <div className="page-header">
   <div>
   <h1 className="page-title">Tạo đề thi mới</h1>
   <p className="page-sub">Chọn câu hỏi từ ngân hàng và cấu hình đề thi</p>
   </div>
  </div>

  {error && <div className="alert alert-error"> {error}</div>}
  {success && <div className="alert alert-success">{success}</div>}

  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
   {/* Left: Info */}
   <div className="card">
   <h3 style={{ marginBottom: '1.25rem' }}>Thông tin đề thi</h3>
   <form onSubmit={handleSubmit}>
    <div className="form-group">
    <label className="form-label">Tên đề thi</label>
    <input className="input" placeholder="VD: Kiểm tra 15 phút - Chương I" value={title} onChange={e => setTitle(e.target.value)} required />
    </div>
    <div className="form-group">
    <label className="form-label">Thời gian (phút)</label>
    <input className="input" type="number" min={1} max={300} value={timeLimit} onChange={e => setTimeLimit(+e.target.value)} required />
    </div>
    <div className="form-group">
    <label className="form-label">Giao cho lớp (tùy chọn)</label>
    <select className="select" value={classId} onChange={e => setClassId(e.target.value ? +e.target.value : '')}>
     <option value="">— Tất cả / Không giới hạn —</option>
     {classes.map(c => <option key={c.id} value={c.id}>{c.class_name}</option>)}
    </select>
    </div>
    <div className="form-group">
    <label className="form-label" style={{ marginBottom: '0.75rem' }}>Thang điểm</label>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.85rem', width: '50px' }}>TN:</span>
        <input type="number" step="0.01" className="input" value={scores.mc} onChange={e => setScores({ ...scores, mc: +e.target.value })} style={{ padding: '0.4rem', fontSize: '0.9rem' }} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.85rem', width: '50px' }}>ĐS:</span>
        <input type="number" step="0.01" className="input" value={scores.tf} onChange={e => setScores({ ...scores, tf: +e.target.value })} style={{ padding: '0.4rem', fontSize: '0.9rem' }} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.85rem', width: '50px' }}>TLN:</span>
        <input type="number" step="0.01" className="input" value={scores.sa} onChange={e => setScores({ ...scores, sa: +e.target.value })} style={{ padding: '0.4rem', fontSize: '0.9rem' }} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.85rem', width: '50px' }}>TL:</span>
        <input type="number" step="0.01" className="input" value={scores.oe} onChange={e => setScores({ ...scores, oe: +e.target.value })} style={{ padding: '0.4rem', fontSize: '0.9rem' }} />
      </div>
    </div>
    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>TN=Trắc nghiệm, ĐS=Đúng/Sai, TLN=Trả lời ngắn, TL=Tự luận</div>
    </div>
    <div className="form-group">
    <label className="form-label">Trạng thái</label>
    <select className="select" value={status} onChange={e => setStatus(e.target.value)}>
     <option value="inactive">Chưa mở</option>
     <option value="active">Mở ngay</option>
    </select>
    </div>

    <div style={{ padding: '0.875rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem' }}>
    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Đã chọn: {topLevelCount} mục ({summaryText})</div>
    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Thời gian dự kiến: {timeLimit} phút</div>
    </div>

    <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading || selectedQuestions.length === 0}>
    {loading ? <><span className="spinner" /> Đang tạo...</> : ' Tạo đề thi'}
    </button>
   </form>
   </div>

   {/* Right: Question bank */}
   <div className="card">
    <h3 style={{ marginBottom: '1rem' }}>Chọn câu hỏi ({topLevelCount} mục - {summaryText})</h3>
   <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
    <input className="input" placeholder=" Tìm câu hỏi hoặc ID..." value={search} onChange={e => setSearch(e.target.value)} />
    <select className="select" style={{ width: 'auto' }} value={qType} onChange={e => setQType(e.target.value)}>
    <option value="">Tất cả loại</option>
    <option value="mc">Trắc nghiệm</option>
    <option value="tf">Đúng/Sai</option>
    <option value="sa">Trả lời ngắn</option>
    <option value="oe">Tự luận</option>
    <option value="st">Chung giả thiết</option>
    </select>
   </div>

   <div style={{ maxHeight: '500px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
    {bankLoading ? (
    Array(5).fill(0).map((_, i) => <div key={i} className="skeleton" style={{ height: '60px' }} />)
    ) : bankQuestions.length === 0 ? (
    <div className="empty-state" style={{ padding: '2rem' }}><p>Không có câu hỏi nào</p></div>
    ) : bankQuestions.map(q => {
    const selected = selectedQuestions.some(sq => sq.id === q.id);
    return (
     <div
     key={q.id}
     onClick={() => toggle(q)}
     style={{
      display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
      padding: '0.75rem', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
      background: selected ? 'rgba(108,99,255,0.08)' : 'var(--bg-elevated)',
      border: `1px solid ${selected ? 'var(--accent-primary)' : 'var(--border)'}`,
      transition: 'all 0.2s',
     }}
     >
     <div style={{
      width: 20, height: 20, borderRadius: 4, flexShrink: 0, marginTop: 2,
      background: selected ? 'var(--accent-primary)' : 'transparent',
      border: `2px solid ${selected ? 'var(--accent-primary)' : 'var(--border)'}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'white', fontSize: '0.75rem', fontWeight: 700
     }}>
      {selected ? '✓' : ''}
     </div>
     <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.3rem', flexWrap: 'wrap' }}>
       {q.question_type === 'st' ? (
           <>
               <span className="badge badge-st" style={{ fontSize: '0.7rem' }}>Chung giả thiết</span>
               {q.children && q.children.length > 0 && Array.from(new Set(q.children.map((c: any) => c.question_type))).map((type: any) => (
                   <span key={type} className={`badge badge-${type}`} style={{ fontSize: '0.7rem' }}>
                       {TYPE_LABELS[type] || type}
                   </span>
               ))}
           </>
       ) : (
           <span className={`badge badge-${q.question_type}`} style={{ fontSize: '0.7rem' }}>
               {TYPE_LABELS[q.question_type]}
           </span>
       )}
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>ID: {q.id}</span>
      {q.subject && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>{q.subject}</span>}
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, maxHeight: '80px', overflowY: 'auto', overflowX: 'hidden' }}>
      <div style={{ pointerEvents: 'none' }}>
       <LatexRenderer content={q.content || ''} />
      </div>
      </div>
     </div>
     </div>
    );
    })}
   </div>
   </div>
  </div>
  </main>
 </div>
 );
}
