'use client';
import { useEffect, useState } from 'react';

interface Props {
 totalSeconds: number;
 onExpire?: () => void;
}

export default function ExamTimer({ totalSeconds, onExpire }: Props) {
 const [remaining, setRemaining] = useState(totalSeconds);

 useEffect(() => {
 if (remaining <= 0) {
  onExpire?.();
  return;
 }
 const interval = setInterval(() => {
  setRemaining((prev) => {
  if (prev <= 1) { onExpire?.(); return 0; }
  return prev - 1;
  });
 }, 1000);
 return () => clearInterval(interval);
 }, [remaining, onExpire]);

 const mins = Math.floor(remaining / 60).toString().padStart(2, '0');
 const secs = (remaining % 60).toString().padStart(2, '0');
 const pct = ((totalSeconds - remaining) / totalSeconds) * 100;

 const timerClass = remaining < 60 ? 'danger' : remaining < 300 ? 'warning' : '';

 return (
 <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'center' }}>
  <div className={`exam-timer ${timerClass}`}>
  <span></span>
  <span>{mins}:{secs}</span>
  </div>
  <div className="progress-bar" style={{ width: '140px' }}>
  <div className="progress-fill" style={{ width: `${pct}%` }} />
  </div>
 </div>
 );
}
