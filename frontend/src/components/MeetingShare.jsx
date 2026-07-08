import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Header from './Header';
import { API_URL, api, getToken } from '../lib/api';

const params = new URLSearchParams(window.location.search);
const PAGE_API_URL = (params.get('api') || API_URL).replace(/\/$/, '');
const SHARE_TOKEN = params.get('share') || '';
const UPLOAD_MODE = params.get('upload_mode') || '';
const UPLOAD_SERIES = params.get('series_id') || '';
const UPLOAD_TITLE = params.get('title') || '';

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

function slugifySeriesId(name) {
  return name
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-_]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function MeetingShare({ meetingId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('standalone');
  const [standaloneName, setStandaloneName] = useState('');
  const [seriesChoice, setSeriesChoice] = useState('new'); // 'new' | 'existing'
  const [newProjectName, setNewProjectName] = useState('');
  const [seriesId, setSeriesId] = useState('');
  const [seriesSearch, setSeriesSearch] = useState('');
  const [seriesOptions, setSeriesOptions] = useState([]);
  const [seriesLoading, setSeriesLoading] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const timer = useRef(null);
  const searchTimer = useRef(null);

  const fetchMeeting = async (cancelledRef) => {
    try {
      const q = SHARE_TOKEN ? `?share=${encodeURIComponent(SHARE_TOKEN)}` : '';
      const url = `${PAGE_API_URL}/api/v1/meeting/${meetingId}${q}`;
      const token = getToken();
      const res = token
        ? await api.get(`/api/v1/meeting/${meetingId}${q}`)
        : await axios.get(url);
      if (cancelledRef?.current) return;
      setData(res.data);
      setError('');
      if (!DONE.has(res.data.status)) {
        timer.current = setTimeout(() => fetchMeeting(cancelledRef), 3000);
      }
    } catch (err) {
      if (cancelledRef?.current) return;
      const status = err?.response?.status;
      if (!err?.response) {
        setError(`Cannot reach API at ${PAGE_API_URL}. Start it: cd apps/api && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`);
      } else if (status === 403) {
        setError('Invalid share link. Open from My Meetings while logged in, or use the full link with share token.');
      } else if (status === 401) {
        setError('This meeting requires a valid share link or login.');
      } else {
        setError('Meeting not found or link expired.');
      }
    } finally {
      if (!cancelledRef?.current) setLoading(false);
    }
  };

  useEffect(() => {
    const cancelled = { current: false };
    fetchMeeting(cancelled);
    return () => {
      cancelled.current = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [meetingId]);

  useEffect(() => {
    if (UPLOAD_MODE === 'standalone' || UPLOAD_MODE === 'connected') {
      setMode(UPLOAD_MODE);
    }
    if (UPLOAD_SERIES) {
      setSeriesChoice('existing');
      setSeriesId(UPLOAD_SERIES);
    }
    if (UPLOAD_TITLE) {
      setStandaloneName(UPLOAD_TITLE);
    }
  }, []);

  const fetchSeriesOptions = async (search = '') => {
    setSeriesLoading(true);
    try {
      const params = new URLSearchParams();
      if (SHARE_TOKEN) params.set('share', SHARE_TOKEN);
      if (search.trim()) params.set('q', search.trim());
      const url = `${PAGE_API_URL}/api/v1/meeting/${meetingId}/series?${params.toString()}`;
      const token = getToken();
      const res = token
        ? await api.get(`/api/v1/meeting/${meetingId}/series?${params.toString()}`)
        : await axios.get(url);
      setSeriesOptions(res.data.items || []);
    } catch {
      setSeriesOptions([]);
    } finally {
      setSeriesLoading(false);
    }
  };

  useEffect(() => {
    if (mode !== 'connected' || data?.status !== 'awaiting_config') return;
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      fetchSeriesOptions(seriesSearch);
    }, 300);
    return () => {
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, [mode, seriesSearch, data?.status, meetingId]);

  const resolvedSeriesId = () => {
    if (mode !== 'connected') return null;
    if (seriesChoice === 'new') return slugifySeriesId(newProjectName);
    return seriesId.trim();
  };

  const handleConfigure = async () => {
    if (mode === 'connected') {
      const sid = resolvedSeriesId();
      if (!sid) {
        alert(
          seriesChoice === 'new'
            ? 'Please enter a project name for the new series.'
            : 'Please search and select an existing project series.'
        );
        return;
      }
    }
    if (mode === 'standalone' && !standaloneName.trim()) {
      alert('Please give this meeting a name so you can find it later on My Meetings.');
      return;
    }
    setConfiguring(true);
    try {
      const q = SHARE_TOKEN ? `?share=${encodeURIComponent(SHARE_TOKEN)}` : '';
      const body = {
        mode,
        series_id: mode === 'connected' ? resolvedSeriesId() : null,
        title: mode === 'standalone' ? standaloneName.trim() : null,
      };
      const token = getToken();
      const res = token
        ? await api.post(`/api/v1/meeting/${meetingId}/configure${q}`, body)
        : await axios.post(`${PAGE_API_URL}/api/v1/meeting/${meetingId}/configure${q}`, body);
      setData(res.data);
      if (timer.current) clearTimeout(timer.current);
      const cancelled = { current: false };
      fetchMeeting(cancelled);
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not configure meeting.');
    } finally {
      setConfiguring(false);
    }
  };

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

  const processing = !DONE.has(data.status) && data.status !== 'awaiting_config';
  const needsConfig = data.status === 'awaiting_config';
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

        {needsConfig && (
          <div className="mb-6 p-5 rounded-lg border border-purple-500/40 bg-purple-950/20">
            <h2 className="text-lg font-bold text-purple-300 mb-1">Meeting Type</h2>
            <p className="text-sm text-gray-400 mb-4">
              Transcription is ready. Choose how this meeting should be summarized.
            </p>

            <div className="flex flex-wrap gap-4 mb-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="meeting-mode"
                  value="standalone"
                  checked={mode === 'standalone'}
                  onChange={() => setMode('standalone')}
                />
                Standalone (single unrelated meeting)
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="meeting-mode"
                  value="connected"
                  checked={mode === 'connected'}
                  onChange={() => setMode('connected')}
                />
                Connected (uses past meetings in same series)
              </label>
            </div>

            {mode === 'standalone' && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Meeting name</label>
                <input
                  type="text"
                  value={standaloneName}
                  onChange={(e) => setStandaloneName(e.target.value)}
                  placeholder="e.g. Client intro call, Team sync March 7"
                  className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-600 text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">
                  This name appears on My Meetings so you can find and share this recording later.
                </p>
              </div>
            )}

            {mode === 'connected' && (
              <div className="mb-4 space-y-4">
                <div className="flex flex-wrap gap-4">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name="series-choice"
                      checked={seriesChoice === 'new'}
                      onChange={() => setSeriesChoice('new')}
                    />
                    Create new project series
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name="series-choice"
                      checked={seriesChoice === 'existing'}
                      onChange={() => {
                        setSeriesChoice('existing');
                        fetchSeriesOptions(seriesSearch);
                      }}
                    />
                    Use existing project series
                  </label>
                </div>

                {seriesChoice === 'new' ? (
                  <div>
                    <label className="block text-sm font-medium mb-1">Project name</label>
                    <input
                      type="text"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      placeholder="e.g. Product Launch Standups"
                      className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-600 text-sm"
                    />
                    {newProjectName.trim() && (
                      <p className="text-xs text-gray-500 mt-1">
                        Series ID: <span className="text-purple-300">{slugifySeriesId(newProjectName) || '—'}</span>
                      </p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      First meeting of this project — later meetings can search and select this series.
                    </p>
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium mb-1">Search project series</label>
                    <input
                      type="text"
                      value={seriesSearch}
                      onChange={(e) => setSeriesSearch(e.target.value)}
                      placeholder="Type project name to search…"
                      className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-600 text-sm mb-2"
                    />
                    {seriesLoading && <p className="text-xs text-gray-500 mb-2">Searching…</p>}
                    {!seriesLoading && seriesOptions.length === 0 && (
                      <p className="text-xs text-gray-500 mb-2">No matching series found. Create a new one instead.</p>
                    )}
                    <div className="max-h-40 overflow-y-auto rounded border border-gray-700 divide-y divide-gray-800">
                      {seriesOptions.map((item) => (
                        <button
                          key={item.series_id}
                          type="button"
                          onClick={() => setSeriesId(item.series_id)}
                          className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-800 ${
                            seriesId === item.series_id ? 'bg-purple-900/40 text-purple-200' : 'text-gray-300'
                          }`}
                        >
                          <span className="font-medium">{item.series_id}</span>
                          <span className="text-gray-500 ml-2">({item.meeting_count} meeting{item.meeting_count !== 1 ? 's' : ''})</span>
                        </button>
                      ))}
                    </div>
                    {seriesId && (
                      <p className="text-xs text-green-400 mt-2">Selected: {seriesId}</p>
                    )}
                  </div>
                )}
              </div>
            )}

            <button
              onClick={handleConfigure}
              disabled={configuring}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 px-4 py-2 rounded font-medium"
            >
              {configuring ? 'Starting…' : mode === 'connected' ? 'Generate Connected Summary' : 'Generate Summary'}
            </button>
          </div>
        )}

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

        {!processing && !failed && !needsConfig && (
          <>
            <div className="mb-4 text-center">
              <a href="/meetings" className="text-sm text-purple-300 hover:text-purple-200 no-underline">
                &larr; Back to My Meetings
              </a>
            </div>
            {(data.use_rag || data.meeting_mode) && (
              <div className="mb-4 p-3 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-400">
                <strong className="text-gray-300">Type:</strong> {data.meeting_mode || 'standalone'}
                {data.meeting_mode === 'connected' && data.series_id && (
                  <> · <strong className="text-gray-300">Series:</strong> {data.series_id}</>
                )}
                {data.use_rag && (
                  <> · <strong className="text-gray-300">RAG:</strong> {data.rag_context_used ? 'past context used' : 'no past context yet'}</>
                )}
              </div>
            )}

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
