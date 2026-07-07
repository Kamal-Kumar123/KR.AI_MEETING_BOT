import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Header from './Header';

const params = new URLSearchParams(window.location.search);
// The extension appends ?api=<backend> so the report reads from the same
// backend that stored the recording (apps/api on :8000 by default).
const API_URL = (params.get('api') || process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const SHARE_TOKEN = params.get('share') || '';

const SPEAKER_COLORS = [
  { bg: 'bg-indigo-500/20', text: 'text-indigo-300', border: 'border-indigo-500/40' },
  { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/40' },
  { bg: 'bg-amber-500/20', text: 'text-amber-300', border: 'border-amber-500/40' },
  { bg: 'bg-pink-500/20', text: 'text-pink-300', border: 'border-pink-500/40' },
  { bg: 'bg-sky-500/20', text: 'text-sky-300', border: 'border-sky-500/40' },
  { bg: 'bg-purple-500/20', text: 'text-purple-300', border: 'border-purple-500/40' },
];

function speakerStyle(speaker) {
  const match = /(\d+)/.exec(speaker || '');
  const idx = match ? (parseInt(match[1], 10) - 1) % SPEAKER_COLORS.length : 0;
  return SPEAKER_COLORS[(idx + SPEAKER_COLORS.length) % SPEAKER_COLORS.length];
}

function buildShareText(data) {
  let text = '📋 KRAI Meeting Report\n\n';
  text += `📝 Summary:\n${data.summary?.executive_summary || 'N/A'}\n\n`;
  if (data.action_items?.length) {
    text += '✅ Action Items:\n';
    text += data.action_items
      .map((item) => `- ${item.task} [Owner: ${item.owner}] [Deadline: ${item.deadline}]`)
      .join('\n');
    text += '\n\n';
  }
  const segments = data.transcript_segments || [];
  if (segments.length) {
    text += '🎙️ Transcript:\n';
    text += segments.map((s) => `${s.speaker || 'Speaker'}: ${s.text}`).join('\n');
  } else if (data.transcript) {
    text += `🎙️ Transcript:\n${data.transcript}`;
  }
  return text;
}

const DONE = new Set(['ready', 'failed']);

function MeetingShare({ meetingId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const timer = useRef(null);

  useEffect(() => {
    let cancelled = false;

    const fetchOnce = async () => {
      try {
        const url = `${API_URL}/api/v1/meeting/${meetingId}${SHARE_TOKEN ? `?share=${encodeURIComponent(SHARE_TOKEN)}` : ''}`;
        const res = await axios.get(url);
        if (cancelled) return;
        setData(res.data);
        setError('');
        if (!DONE.has(res.data.status)) {
          timer.current = setTimeout(fetchOnce, 3000);
        }
      } catch (err) {
        if (cancelled) return;
        setError('Meeting not found or link expired.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchOnce();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [meetingId]);

  const shareUrl = window.location.href;
  const copyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    alert('Share link copied!');
  };
  const copyReport = () => {
    navigator.clipboard.writeText(buildShareText(data));
    alert('Full report copied!');
  };
  const emailShare = () => {
    const body = encodeURIComponent(buildShareText(data) + `\n\nLink: ${shareUrl}`);
    window.location.href = `mailto:?subject=Meeting Summary&body=${body}`;
  };
  const whatsappShare = () => {
    const text = encodeURIComponent(buildShareText(data) + `\n\n${shareUrl}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-gray-200 flex items-center justify-center">
        <p>Loading meeting results...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-gray-200 flex items-center justify-center">
        <p>{error || 'Meeting not found.'}</p>
      </div>
    );
  }

  const processing = !DONE.has(data.status);
  const failed = data.status === 'failed';
  const segments = data.transcript_segments || [];
  const speakerCount = new Set(segments.map((s) => s.speaker).filter(Boolean)).size;

  return (
    <div className="bg-[#0f172a] text-gray-200 min-h-screen flex flex-col">
      <Header />
      <main className="max-w-4xl mx-auto px-6 py-8 w-full">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">{data.title || 'Meeting Report'}</h1>
          <p className="text-sm text-gray-400">
            {data.platform} · {data.status}
            {data.duration_seconds ? ` · ${Math.round(data.duration_seconds / 60)} min` : ''}
          </p>
        </div>

        {processing && (
          <div className="mb-6 p-4 rounded-lg border border-yellow-500/40 bg-yellow-950/20">
            <p className="font-medium text-yellow-300">Processing…</p>
            <p className="text-sm text-gray-400">
              {data.progress_message || 'Transcribing and generating your summary.'} This page updates automatically.
            </p>
          </div>
        )}

        {failed && (
          <div className="mb-6 p-4 rounded-lg border border-red-500/40 bg-red-950/20">
            <p className="font-medium text-red-300">Processing failed</p>
            <p className="text-sm text-gray-400">{data.error_message || 'The recording could not be processed.'}</p>
          </div>
        )}

        {!processing && !failed && (
          <>
            <div className="mb-6 p-4 rounded-lg border border-green-500/40 bg-green-950/20">
              <h2 className="text-lg font-bold text-green-300 mb-2">Meeting Ready to Share</h2>
              <input
                readOnly
                value={shareUrl}
                className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-600 text-sm mb-3"
              />
              <div className="flex flex-wrap gap-2">
                <button onClick={copyLink} className="bg-blue-600 px-4 py-2 rounded text-sm hover:bg-blue-700">Copy Link</button>
                <button onClick={copyReport} className="bg-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-600">Copy Full Report</button>
                <button onClick={emailShare} className="bg-purple-600 px-4 py-2 rounded text-sm hover:bg-purple-700">Email</button>
                <button onClick={whatsappShare} className="bg-green-600 px-4 py-2 rounded text-sm hover:bg-green-700">WhatsApp</button>
              </div>
            </div>

            {data.summary?.executive_summary && (
              <div className="mb-6 p-4 rounded-lg bg-gray-900 border border-gray-700">
                <h3 className="font-bold text-lg mb-2">📝 Summary</h3>
                <p className="whitespace-pre-wrap text-gray-300">{data.summary.executive_summary}</p>
              </div>
            )}

            {data.action_items?.length > 0 && (
              <div className="mb-6 p-4 rounded-lg bg-gray-900 border border-gray-700">
                <h3 className="font-bold text-lg mb-2">✅ Action Items</h3>
                <ul className="space-y-3">
                  {data.action_items.map((item, i) => (
                    <li key={i} className="text-sm text-gray-300 border-l-2 border-teal-500 pl-3">
                      <strong>{item.task}</strong>
                      <br />
                      Owner: {item.owner} · Deadline: {item.deadline}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {(segments.length > 0 || data.transcript) && (
          <div className="p-4 rounded-lg bg-gray-900 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-lg">🎙️ Transcript</h3>
              {speakerCount > 0 && (
                <span className="text-xs text-gray-400">{speakerCount} speaker{speakerCount > 1 ? 's' : ''} detected</span>
              )}
            </div>
            <div className="max-h-96 overflow-y-auto text-sm space-y-2">
              {segments.length > 0 ? (
                segments.map((s, i) => {
                  const st = speakerStyle(s.speaker);
                  return (
                    <div key={i} className="flex gap-2">
                      <span className={`shrink-0 h-fit rounded px-2 py-0.5 text-xs font-medium border ${st.bg} ${st.text} ${st.border}`}>
                        {s.speaker || 'Speaker'}
                      </span>
                      <span className="text-gray-300">{s.text}</span>
                    </div>
                  );
                })
              ) : (
                <p className="text-gray-400 whitespace-pre-wrap">{data.transcript}</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default MeetingShare;
