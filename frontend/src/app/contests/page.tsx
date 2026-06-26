'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';
import Link from 'next/link';
import ExportContestModal from '@/components/ExportContestModal';

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

  useEffect(() => { if (!isLoading && !user) router.replace('/'); }, [user, isLoading, router]);

  useEffect(() => {
    if (!user) return;
    api.getContests().then(res => setContests(res as Contest[])).catch(() => { }).finally(() => setLoading(false));
  }, [user]);

  const toggleStatus = async (c: Contest) => {
    const newStatus = c.status === 'active' ? 'inactive' : 'active';
    await api.updateContestStatus(c.id, newStatus);
    setContests(prev => prev.map(x => x.id === c.id ? { ...x, status: newStatus } : x));
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
                  {user?.role !== 'teacher' && (
                    <span className={`badge badge-${c.status}`}>{c.status === 'active' ? 'Đang mở' : 'Đóng'}</span>
                  )}
                  {user?.role === 'teacher' ? (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn btn-sm"
                        onClick={() => toggleStatus(c)}
                        title={c.status === 'active' ? 'Bấm để đóng đề thi' : 'Bấm để mở đề thi'}
                        style={c.status === 'active'
                          ? { background: 'rgba(107,203,119,0.15)', color: 'var(--accent-success)', border: '1px solid rgba(107,203,119,0.35)' }
                          : { background: 'rgba(136,144,176,0.15)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                      >
                        {c.status === 'active' ? 'Đang mở' : 'Đóng'}
                      </button>
                      <button className="btn btn-primary btn-sm" onClick={() => {
                        setSelectedContest(c);
                        setShowExportModal(true);
                      }}>Xuất đề</button>
                      <Link href={`/contests/${c.id}`} className="btn btn-secondary btn-sm">Chi tiết</Link>
                      <button className="btn btn-danger btn-sm" onClick={async () => {
                        if (!confirm('Bạn có chắc muốn xóa đề thi này không?')) return;
                        await api.updateContestStatus(c.id, 'deleted');
                        setContests(prev => prev.filter(x => x.id !== c.id));
                      }}>Xóa</button>
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
        <ExportContestModal contest={selectedContest} onClose={() => setShowExportModal(false)} />
      )}
    </div>
  );
}
