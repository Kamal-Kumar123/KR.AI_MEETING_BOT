import React, { useEffect, useState } from 'react';
import Header from './Header';
import { useAuth } from '../context/AuthContext';
import { api, meetingUrl } from '../lib/api';

function isAudioFile(f) {
  if (!f) return false;
  return /\.(mp3|wav|m4a|mp4|webm|ogg|aac|flac)$/i.test(f.name);
}

function isTextFile(f) {
  return f && /\.txt$/i.test(f.name);
}

function ManualUpload() {
  const { user, loading: authLoading } = useAuth();
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('standalone');
  const [seriesId, setSeriesId] = useState('');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && !user) {
      window.location.href = '/';
    }
  }, [user, authLoading]);

  const handleFileChange = (e) => {
    const picked = e.target.files[0];
    setFile(picked || null);
    setError('');
    if (picked && !title.trim()) {
      setTitle(picked.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' '));
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select an audio/video file or a .txt transcript.');
      return;
    }
    if (mode === 'connected' && !seriesId.trim()) {
      setError('Enter a Series ID for connected meetings.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('platform', 'manual_upload');
      const res = await api.post('/api/v1/recordings/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const url = new URL(meetingUrl(res.data.meeting_id, res.data.share_token));
      url.searchParams.set('upload_mode', mode);
      if (mode === 'connected' && seriesId.trim()) {
        url.searchParams.set('series_id', seriesId.trim());
      }
      if (title.trim()) {
        url.searchParams.set('title', title.trim());
      }
      window.location.href = url.toString();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Is the API running on port 8000?');
    } finally {
      setBusy(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-gray-200 flex items-center justify-center">
        Loading…
      </div>
    );
  }

  return (
    <div className="bg-[#0f172a] text-gray-200 min-h-screen flex flex-col">
      <Header />
      <main className="max-w-6xl mx-auto px-6 py-8 w-full grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 p-6 rounded-xl border border-gray-700 bg-gray-900/50">
          <h1 className="text-xl font-bold mb-1">Upload Meeting</h1>
          <p className="text-sm text-gray-400 mb-6">
            Upload a Zoom recording or transcript file — same pipeline as the extension.
          </p>

          <div className="mb-5 p-4 rounded-lg border border-blue-500/40 bg-blue-950/20">
            <h2 className="text-sm font-semibold text-blue-300 mb-2">Zoom local recording (all voices)</h2>
            <ol className="text-xs text-gray-400 list-decimal list-inside space-y-1 mb-3">
              <li>In Zoom: Record → Record on this Computer</li>
              <li>After meeting, find file in Documents/Zoom (.mp4 or .m4a)</li>
              <li>Upload here → Whisper transcribes for free</li>
            </ol>
            <label className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer text-sm">
              {file ? file.name : 'Select recording (.mp4, .m4a, .mp3, .wav, .webm)'}
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.mp4,.webm,.ogg,.aac,.flac,.txt"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>

          <div className="mb-4">
            <label className="block text-sm mb-1">Meeting name (optional)</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Sprint planning call"
              className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
            />
          </div>

          <div className="mb-4 space-y-3">
            <p className="text-sm font-medium">Meeting type</p>
            <div className="flex flex-wrap gap-4 text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="upload-mode"
                  checked={mode === 'standalone'}
                  onChange={() => setMode('standalone')}
                />
                Standalone
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="upload-mode"
                  checked={mode === 'connected'}
                  onChange={() => setMode('connected')}
                />
                Connected (RAG project series)
              </label>
            </div>
          </div>

          {mode === 'connected' && (
            <div className="mb-4">
              <label className="block text-sm mb-1">Series ID</label>
              <input
                type="text"
                value={seriesId}
                onChange={(e) => setSeriesId(e.target.value)}
                placeholder="e.g. product-launch-standups"
                className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
              />
            </div>
          )}

          {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleUpload}
              disabled={busy || !file}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded font-medium"
            >
              {busy
                ? isTextFile(file)
                  ? 'Uploading transcript…'
                  : 'Uploading & transcribing…'
                : isAudioFile(file)
                  ? 'Upload & Transcribe'
                  : isTextFile(file)
                    ? 'Upload Transcript'
                    : 'Upload & Process'}
            </button>
            <button
              type="button"
              onClick={() => {
                setFile(null);
                setError('');
              }}
              className="border border-gray-600 px-4 py-2 rounded hover:bg-gray-800"
            >
              Clear
            </button>
            <a
              href="/meetings"
              className="inline-flex items-center gap-1 border border-gray-500 px-4 py-2 rounded-lg hover:bg-gray-800 no-underline text-gray-200 text-sm"
            >
              <span aria-hidden="true">&larr;</span> Back to My Meetings
            </a>
          </div>
        </div>

        <aside className="p-6 rounded-xl border border-gray-700 bg-gray-900/40 h-fit">
          <h2 className="font-bold text-purple-300 mb-3">Extension Flow</h2>
          <ol className="text-sm text-gray-400 space-y-2 list-decimal list-inside">
            <li>Install KRAI Chrome extension</li>
            <li>Open Google Meet / Teams / Zoom</li>
            <li>Click extension → Start recording</li>
            <li>Stop → auto upload to this dashboard</li>
            <li>Or upload a Zoom .mp4 here for all voices</li>
          </ol>
        </aside>
      </main>
    </div>
  );
}

export default ManualUpload;
