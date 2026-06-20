'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';
import Link from 'next/link';
import RichLatexEditor from '@/components/RichLatexEditor';
import LatexRenderer from '@/components/LatexRenderer';

type Contest = {
  id: number; title: string; status: string; time_limit: number;
  class_name?: string; question_count: number; public_id: string;
  result_id?: number;
  attempts?: any[];
};

export default function ContestsPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [contests, setContests] = useState<Contest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedHistory, setExpandedHistory] = useState<number | null>(null);

  // Export Modal states
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedContest, setSelectedContest] = useState<Contest | null>(null);

  const [examTitle, setExamTitle] = useState('');
  const [department, setDepartment] = useState('BỘ GIÁO DỤC VÀ ĐÀO TẠO');
  const [examType, setExamType] = useState('ĐỀ THI CHÍNH THỨC');
  const [subject, setSubject] = useState('TOÁN');
  const [duration, setDuration] = useState(50);
  const [enableGeneralInfo, setEnableGeneralInfo] = useState(false);
  const [generalInfo, setGeneralInfo] = useState('+ Cho biết: $\\pi = 3,14$; ...\n+ Không làm tròn kết quả các phép tính trung gian.');
  const [exportFormats, setExportFormats] = useState({ word: true, pdf: false, latex: false });
  const [numShuffles, setNumShuffles] = useState(0);
  const [codeType, setCodeType] = useState('incremental'); // 'incremental' | 'random'
  const [startingCode, setStartingCode] = useState('0101');
  const [codeStep, setCodeStep] = useState(1);
  const [randomLength, setRandomLength] = useState(3);

  const [exporting, setExporting] = useState(false);

  useEffect(() => { if (!isLoading && !user) router.replace('/'); }, [user, isLoading, router]);

  useEffect(() => {
    // Load saved settings
    const saved = localStorage.getItem('export_modal_defaults');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.examTitle) setExamTitle(parsed.examTitle);
        if (parsed.department) setDepartment(parsed.department);
        if (parsed.examType) setExamType(parsed.examType);
        if (parsed.subject) setSubject(parsed.subject);
        if (typeof parsed.duration === 'number') setDuration(parsed.duration);
        if (typeof parsed.enableGeneralInfo === 'boolean') setEnableGeneralInfo(parsed.enableGeneralInfo);
        if (parsed.generalInfo) setGeneralInfo(parsed.generalInfo);
        if (parsed.exportFormats) setExportFormats(parsed.exportFormats);
        if (typeof parsed.numShuffles === 'number') setNumShuffles(parsed.numShuffles);
        if (parsed.codeType) setCodeType(parsed.codeType);
        if (parsed.startingCode) setStartingCode(parsed.startingCode);
        if (typeof parsed.codeStep === 'number') setCodeStep(parsed.codeStep);
        if (typeof parsed.randomLength === 'number') setRandomLength(parsed.randomLength);
      } catch (e) { }
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    api.getContests().then(res => setContests(res as Contest[])).catch(() => { }).finally(() => setLoading(false));
  }, [user]);

  const toggleStatus = async (c: Contest) => {
    const newStatus = c.status === 'active' ? 'inactive' : 'active';
    await api.updateContestStatus(c.id, newStatus);
    setContests(prev => prev.map(x => x.id === c.id ? { ...x, status: newStatus } : x));
  };

  const handleExport = async () => {
    if (!selectedContest) return;
    setExporting(true);

    // Save to localStorage
    const toSave = {
      examTitle: examTitle.trim() ? examTitle : selectedContest.title,
      department,
      examType,
      subject,
      duration,
      enableGeneralInfo,
      generalInfo,
      exportFormats,
      numShuffles,
      codeType,
      startingCode,
      codeStep,
      randomLength
    };
    localStorage.setItem('export_modal_defaults', JSON.stringify(toSave));

    try {
      const formats = Object.keys(exportFormats).filter(k => (exportFormats as any)[k]);
      await api.exportContest(selectedContest.id, {
        formats,
        num_shuffles: numShuffles,
        exam_title: toSave.examTitle,
        department: toSave.department,
        exam_type: toSave.examType,
        subject: toSave.subject,
        duration: toSave.duration,
        general_info: enableGeneralInfo ? generalInfo : '',
        code_type: codeType,
        starting_code: startingCode,
        code_step: codeStep,
        random_length: randomLength
      });
      setShowExportModal(false);
    } catch (err: any) {
      alert(err.message || 'Lỗi khi xuất đề');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page-wrapper">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">{user?.role === 'teacher' ? 'Quản lý đề thi' : 'Đề thi của tôi'}</h1>
            <p className="page-sub">{contests.length} đề thi</p>
          </div>
          {user?.role === 'teacher' && (
            <Link href="/contests/new" className="btn btn-primary"> Tạo đề thi</Link>
          )}
        </div>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: '80px', borderRadius: 'var(--radius-lg)' }} />)}
          </div>
        ) : contests.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"></div>
            <h3>Chưa có đề thi nào</h3>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {contests.map(c => (
              <div key={c.id} className="card" style={{ display: 'flex', flexDirection: 'column', padding: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', padding: '1.25rem' }}>
                  <div style={{ width: 44, height: 44, background: c.status === 'active' ? 'rgba(107,203,119,0.15)' : 'var(--bg-elevated)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.3rem', flexShrink: 0 }}>
                    {c.status === 'active' ? '' : ''}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.25rem' }}>{c.title}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                      <span> {c.time_limit} phút</span>
                      <span> {c.question_count} câu</span>
                      {c.class_name && <span> {c.class_name}</span>}
                    </div>
                  </div>
                  <span className={`badge badge-${c.status}`}>{c.status === 'active' ? 'Đang mở' : 'Đóng'}</span>
                  {user?.role === 'teacher' ? (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button className="btn btn-primary btn-sm" onClick={() => {
                        setSelectedContest(c);
                        if (!examTitle) setExamTitle(c.title);
                        setShowExportModal(true);
                      }}>Xuất đề</button>
                      <button className={`btn btn-sm ${c.status === 'active' ? 'btn-danger' : 'btn-secondary'}`} onClick={() => toggleStatus(c)}>
                        {c.status === 'active' ? 'Đóng' : 'Mở'}
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={async () => {
                        if (!confirm('Bạn có chắc muốn xóa đề thi này không?')) return;
                        await api.updateContestStatus(c.id, 'deleted');
                        setContests(prev => prev.filter(x => x.id !== c.id));
                      }}>Xóa</button>
                      <Link href={`/contests/${c.id}`} className="btn btn-ghost btn-sm">Chi tiết</Link>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {c.attempts && c.attempts.length === 1 && (
                        <Link href={`/results/${c.attempts[0].id}`} className="btn btn-secondary btn-sm" style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}>Xem kết quả</Link>
                      )}
                      {c.attempts && c.attempts.length > 1 && (
                        <button onClick={() => setExpandedHistory(expandedHistory === c.id ? null : c.id)} className="btn btn-secondary btn-sm" style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}>
                          Lịch sử ({c.attempts.length}) {expandedHistory === c.id ? '▲' : '▼'}
                        </button>
                      )}
                      <Link href={`/exam/${c.id}`} className="btn btn-primary btn-sm">{c.attempts && c.attempts.length > 0 ? 'Làm lại' : 'Làm bài →'}</Link>
                    </div>
                  )}
                </div>

                {expandedHistory === c.id && c.attempts && c.attempts.length > 1 && (
                  <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--border)', background: 'rgba(0,0,0,0.02)' }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>Lịch sử các lần làm bài:</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {c.attempts.map((att, i) => (
                        <div key={att.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                          <div>
                            <span style={{ fontWeight: 600, marginRight: '1rem', color: 'var(--text-primary)' }}>Lần {i + 1}</span>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                              {new Date(att.start_time).toLocaleString('vi-VN')}
                            </span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                            <span style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>{Number(att.total_score).toFixed(2)} điểm</span>
                            <Link href={`/results/${att.id}`} className="btn btn-ghost btn-sm">Xem kết quả</Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {showExportModal && selectedContest && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '1400px', width: '95vw', maxHeight: '95vh', padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className="modal-header" style={{ borderBottom: '1px solid var(--border)', padding: '1rem 1.5rem', background: '#fff' }}>
              <h3 className="modal-title" style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Xuất đề thi: {selectedContest.title}</h3>
            </div>

            <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
              {/* CỘT TRÁI: ĐIỀU CHỈNH THÔNG TIN */}
              <div style={{ flex: '1 1 55%', padding: '1rem 1.5rem', overflowY: 'auto', borderRight: '1px solid var(--border)', background: '#fcfcfc' }}>

                {/* Phần 1: Các trường thông tin cơ bản (2 cột) */}
                <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1.25rem' }}>
                  {/* Cột 1 */}
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Đơn vị (VD: BỘ GIÁO DỤC VÀ ĐÀO TẠO)</label>
                      <input type="text" className="form-control" value={department} onChange={e => setDepartment(e.target.value)} style={{ width: '100%', padding: '0.6rem' }} />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Loại đề (VD: ĐỀ THI CHÍNH THỨC)</label>
                      <input type="text" className="form-control" value={examType} onChange={e => setExamType(e.target.value)} style={{ width: '100%', padding: '0.6rem' }} />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Thời gian làm bài (phút): (VD: 50)</label>
                      <input type="number" className="form-control" value={duration} onChange={e => setDuration(Number(e.target.value))} style={{ width: '100%', padding: '0.6rem' }} />
                    </div>
                  </div>

                  {/* Cột 2 */}
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Tên kỳ thi (VD: KỲ THI TỐT NGHIỆP...)</label>
                      <input type="text" className="form-control" placeholder={selectedContest.title} value={examTitle} onChange={e => setExamTitle(e.target.value)} style={{ width: '100%', padding: '0.6rem' }} />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Môn thi: (VD: TOÁN)</label>
                      <input type="text" className="form-control" value={subject} onChange={e => setSubject(e.target.value)} style={{ width: '100%', padding: '0.6rem' }} />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Định dạng xuất</label>
                      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.3rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}><input type="checkbox" checked={exportFormats.word} onChange={e => setExportFormats({ ...exportFormats, word: e.target.checked })} /> Word</label>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}><input type="checkbox" checked={exportFormats.pdf} onChange={e => setExportFormats({ ...exportFormats, pdf: e.target.checked })} /> PDF</label>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}><input type="checkbox" checked={exportFormats.latex} onChange={e => setExportFormats({ ...exportFormats, latex: e.target.checked })} /> LaTeX</label>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Phần 2: Các trường cấu hình phức tạp (1 cột full width) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

                  {/* Mã đề */}
                  <div style={{ display: 'flex', flexDirection: 'column', border: '1px solid var(--border)', borderRadius: '4px', padding: '1rem', background: '#fff' }}>
                    <label style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>Mã đề:</label>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.95rem' }}>
                        <input type="radio" checked={codeType === 'random'} onChange={() => setCodeType('random')} />
                        Ngẫu nhiên (số chữ số)
                      </label>
                      <input type="number" className="form-control" value={randomLength} min={1} max={6} onChange={e => setRandomLength(Number(e.target.value))} style={{ width: '80px', padding: '0.4rem', fontSize: '0.9rem' }} disabled={codeType !== 'random'} />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.95rem' }}>
                        <input type="radio" checked={codeType === 'incremental'} onChange={() => setCodeType('incremental')} />
                        Tăng dần:
                      </label>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        Từ: <input type="text" className="form-control" value={startingCode} onChange={e => setStartingCode(e.target.value)} style={{ width: '70px', padding: '0.4rem' }} disabled={codeType !== 'incremental'} />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        Bước nhảy <input type="number" className="form-control" value={codeStep} min={1} onChange={e => setCodeStep(Number(e.target.value))} style={{ width: '60px', padding: '0.4rem' }} disabled={codeType !== 'incremental'} />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        Số đề: <input type="number" className="form-control" value={numShuffles} min={0} onChange={e => setNumShuffles(Number(e.target.value))} style={{ width: '70px', padding: '0.4rem' }} />
                      </div>
                    </div>
                  </div>

                  {/* Thông tin chung */}
                  <div style={{ display: 'flex', flexDirection: 'column', border: '1px solid var(--border)', borderRadius: '4px', padding: '1rem', background: '#fff' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.75rem' }}>
                      <input type="checkbox" checked={enableGeneralInfo} onChange={e => setEnableGeneralInfo(e.target.checked)} />
                      Thông tin chung (Ghi chú):
                    </label>
                    {enableGeneralInfo && (
                      <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                        <RichLatexEditor content={generalInfo} onChange={setGeneralInfo} minHeight="60px" maxHeight="120px" />
                      </div>
                    )}
                  </div>

                </div>
              </div>

              {/* CỘT PHẢI: PREVIEW SỬ DỤNG CONTAINER QUERIES */}
              <div style={{ flex: '1 1 45%', padding: '1rem 1.5rem', background: '#e5e7eb', overflowY: 'auto' }}>
                <h4 style={{ fontSize: '1rem', marginBottom: '1.25rem', color: 'var(--text-secondary)' }}>Xem trước Giao diện Đề thi</h4>

                <div style={{ width: '100%', containerType: 'inline-size' }}>
                  <div style={{
                    width: '100%',
                    background: '#fff',
                    padding: '5.95cqw 5.95cqw 5.95cqw 7.14cqw',
                    boxSizing: 'border-box',
                    borderRadius: '4px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                    fontFamily: '"Times New Roman", Times, serif',
                    color: '#000',
                    lineHeight: 1.25
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2.5cqw', alignItems: 'flex-start' }}>
                      <div style={{ width: '30cqw', textAlign: 'center' }}>
                        <div style={{ fontWeight: 'bold', fontSize: '1.9cqw' }}>{department || 'BỘ GIÁO DỤC VÀ ĐÀO TẠO'}</div>
                        <div style={{ borderBottom: 'max(1px, 0.15cqw) solid #000', margin: '0.4cqw auto 0.6cqw', width: '60%' }}></div>
                        <div style={{ fontSize: '1.9cqw' }}>{examType || 'ĐỀ THI CHÍNH THỨC'}</div>
                        <div style={{ fontStyle: 'italic', marginTop: '0.4cqw', fontSize: '1.9cqw' }}>(Đề thi có ... trang)</div>
                      </div>

                      <div style={{ width: '60cqw', textAlign: 'center' }}>
                        <div style={{ fontWeight: 'bold', fontSize: '1.9cqw' }}>{examTitle || selectedContest.title}</div>
                        <div style={{ fontWeight: 'bold', marginTop: '0.6cqw', fontSize: '1.9cqw' }}>Môn thi: {subject || 'TOÁN'}</div>
                        <div style={{ fontStyle: 'italic', marginTop: '0.6cqw', fontSize: '1.9cqw' }}>
                          Thời gian <span style={{ borderBottom: 'max(1px, 0.15cqw) solid #000' }}>làm bài: {duration || 50} phút, không kể thời gian</span> phát đề
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '3cqw', marginBottom: '2cqw' }}>
                      <div style={{ width: '52.38cqw', display: 'flex', flexDirection: 'column', gap: '1cqw' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5cqw' }}>
                          <strong style={{ fontSize: '1.9cqw' }}>Họ, tên thí sinh: </strong>
                          <div style={{ flex: 1, borderBottom: 'max(1px, 0.2cqw) dotted #000' }}></div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5cqw' }}>
                          <strong style={{ fontSize: '1.9cqw' }}>Số báo danh: </strong>
                          <div style={{ flex: 1, borderBottom: 'max(1px, 0.2cqw) dotted #000' }}></div>
                        </div>
                      </div>

                      <div style={{ width: '30.95cqw', display: 'flex', justifyContent: 'flex-end' }}>
                        <div style={{
                          border: 'max(1px, 0.15cqw) solid #000',
                          padding: '0.5cqw 6.5cqw',
                          fontWeight: 'bold',
                          textAlign: 'center',
                          fontSize: '1.9cqw'
                        }}>
                          Mã đề: {codeType === 'incremental' ? startingCode || '000' : '000'}
                        </div>
                      </div>
                    </div>

                    {enableGeneralInfo && generalInfo && (
                      <div style={{ fontSize: '1.9cqw', marginTop: '2cqw', whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>
                        <LatexRenderer content={generalInfo.replace(/\n/g, '\\\\')} />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.5rem', background: '#fff', borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic', maxWidth: '60%' }}>
                <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>Mẹo:</span> Đối với file Word, do đặc thù tự động dàn trang, vui lòng nhấn tổ hợp <kbd>Ctrl</kbd> + <kbd>P</kbd> rồi nhấn <kbd>ESC</kbd> khi mở file để hệ thống tự động tính và cập nhật đúng tổng số trang vào phần "Đề thi có ... trang".
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button className="btn btn-secondary" onClick={() => setShowExportModal(false)} disabled={exporting}>Hủy thao tác</button>
                <button className="btn btn-primary" onClick={handleExport} disabled={exporting} style={{ paddingLeft: '1.5rem', paddingRight: '1.5rem' }}>
                  {exporting ? 'Đang xử lý...' : 'Xuất đề thi'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
