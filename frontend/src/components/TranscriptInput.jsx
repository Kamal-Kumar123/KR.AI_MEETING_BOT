import React, { useState } from 'react';
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:10000';

const TranscriptInput = () => {
  const [file, setFile] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [summary, setSummary] = useState('');
  const [actionItems, setActionItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('standalone');
  const [seriesId, setSeriesId] = useState('');
  const [meetingMeta, setMeetingMeta] = useState(null);
  const [transcriptionInfo, setTranscriptionInfo] = useState(null);

  const isAudioFile = (f) => {
    if (!f) return false;
    return /\.(mp3|wav|m4a|mp4|webm|ogg|aac|flac)$/i.test(f.name);
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setTranscriptionInfo(null);
  };

  const handleUpload = async () => {
    if (mode === 'connected' && !seriesId.trim()) {
      alert('Please enter a Series ID for connected meetings (e.g. sprint-12-standups).');
      return;
    }

    setLoading(true);
    try {
      let res;

      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);
        if (mode === 'connected') {
          formData.append('series_id', seriesId.trim());
        }
        res = await axios.post(`${BASE_URL}/transcribe`, formData);
      } else {
        const params = new URLSearchParams({ mode });
        if (mode === 'connected') {
          params.append('series_id', seriesId.trim());
        }
        res = await axios.post(`${BASE_URL}/transcribe/from-file?${params.toString()}`);
      }

      setTranscript(res.data.transcript || '');
      setSummary(res.data.summary?.map((s) => s.summary).join('\n') || 'No summary available');
      setActionItems(res.data.action_items || []);
      setMeetingMeta({
        mode: res.data.mode,
        seriesId: res.data.series_id,
        useRag: res.data.use_rag,
        ragContextUsed: res.data.rag_context_used,
        stack: res.data.stack || 'free-local',
        type: res.data.type,
        meetingId: res.data.meeting_id,
        shareUrl: res.data.share_url,
      });
      setTranscriptionInfo(res.data.transcription || null);
    } catch (err) {
      console.error('Upload failed:', err);
      const message = err.response?.data?.error || 'Upload failed. Check backend connection and inputs.';
      alert(`❌ ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setTranscript('');
    setSummary('');
    setActionItems([]);
    setMeetingMeta(null);
    setTranscriptionInfo(null);
  };

  const handleCopy = () => {
    const text = generateExportText();
    navigator.clipboard.writeText(text);
    alert('📋 Copied to clipboard!');
  };

  const handleDownload = () => {
    const text = generateExportText();
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'meeting-summary.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const generateMailtoLink = () => {
    const text = generateExportText();
    return `mailto:?subject=Meeting Summary&body=${encodeURIComponent(text)}`;
  };

  const generateExportText = () => {
    let text = '';
    if (transcript) {
      text += '🎙️ Transcript:\n' + transcript + '\n\n';
    }
    text += '📝 Meeting Summary:\n';
    text += summary + '\n\n';
    text += '✅ Action Items:\n';
    if (Array.isArray(actionItems)) {
      text += actionItems
        .map((item) => `- ${item.task} [Owner: ${item.owner}] [Deadline: ${item.deadline}]`)
        .join('\n');
    } else {
      text += 'No action items.';
    }
    return text;
  };

  const handleExportToNotion = () => {
    alert('📓 Export to Notion feature coming soon!');
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-white dark:bg-gray-900 p-6 rounded-lg shadow-lg border dark:border-gray-700">
      <br></br>
      <h2 className="text-lg font-semibold mb-1 text-gray-900 dark:text-white">📄 Upload Meeting</h2>

      <div className="mb-4 p-4 rounded-lg border border-blue-500/40 bg-blue-950/20">
        <h3 className="text-sm font-semibold text-blue-300 mb-2">🎧 Zoom local recording (free — all voices)</h3>
        <ol className="text-xs text-gray-400 list-decimal list-inside space-y-1 mb-3">
          <li>In Zoom: Record → Record on this Computer</li>
          <li>After meeting, find file in Documents/Zoom (usually .mp4 or .m4a)</li>
          <li>Upload here → Deepgram transcribes with speaker labels</li>
        </ol>
        <label className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer text-sm">
          {file && isAudioFile(file) ? file.name : 'Select Zoom recording (.mp4, .m4a, .mp3, .wav)'}
          <input
            type="file"
            accept=".mp3,.wav,.m4a,.mp4,.webm,.ogg,.aac,.flac,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>
      </div>

      <div className="mb-4 space-y-3">
        <div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Meeting Type</p>
          <div className="flex flex-wrap gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer">
              <input
                type="radio"
                name="meeting-mode"
                value="standalone"
                checked={mode === 'standalone'}
                onChange={() => setMode('standalone')}
              />
              Standalone (single unrelated meeting)
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer">
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
        </div>

        {mode === 'connected' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Series ID
            </label>
            <input
              type="text"
              value={seriesId}
              onChange={(e) => setSeriesId(e.target.value)}
              placeholder="e.g. product-launch-standups"
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 mt-1">
              Use the same Series ID for all related meetings so RAG can pull past context.
            </p>
          </div>
        )}
      </div>

      <div className="mb-4">
        <label className="inline-block bg-gray-100 dark:bg-gray-800 dark:text-white border border-gray-300 dark:border-gray-600 px-4 py-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 cursor-pointer text-center">
          {file && !isAudioFile(file) ? file.name : 'Or select a .txt transcript file'}
          <input
            type="file"
            accept=".txt"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>
      </div>

      <div className="flex gap-4 mb-4">
        <button
          onClick={handleUpload}
          disabled={loading}
          className="border border-teal-600 text-teal-600 px-4 py-1.5 rounded hover:bg-teal-600 hover:text-white transition disabled:opacity-60" // ✅ yaha style same kiya jaise image me
        >
          {loading
            ? isAudioFile(file)
              ? 'Transcribing audio...'
              : 'Processing...'
            : isAudioFile(file)
              ? 'Transcribe & Summarize'
              : 'Generate Summary'}
        </button>

        <button
          onClick={handleClear}
          className="border border-gray-600 text-gray-600 px-4 py-1.5 rounded hover:bg-gray-600 hover:text-white transition" // ✅ yaha bhi same styling ki
        >
          Clear
        </button>
      </div>
      <br></br>
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={handleUpload}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-60"
        >
          Generate Zoom Meeting Summary
        </button>
      </div>

      <br></br>

      {transcriptionInfo && (
        <div className="mb-4 p-3 rounded border border-green-600/40 bg-green-950/20 text-sm text-gray-300">
          <p><strong>Transcription:</strong> {transcriptionInfo.engine} ({transcriptionInfo.model}) — {transcriptionInfo.cost}</p>
          {transcriptionInfo.diarization?.enabled && (
            <p><strong>Diarization:</strong> ✅ {transcriptionInfo.diarization.speaker_count} speakers detected</p>
          )}
          {transcriptionInfo.diarization && !transcriptionInfo.diarization.enabled && isAudioFile(file) && (
            <p className="text-yellow-400 text-xs">Diarization off — set HF_TOKEN in backend .env for Speaker 1, Speaker 2 labels</p>
          )}
          {transcriptionInfo.duration_seconds && (
            <p><strong>Duration:</strong> {Math.round(transcriptionInfo.duration_seconds / 60)} min</p>
          )}
          <p><strong>Segments:</strong> {transcriptionInfo.segment_count}</p>
        </div>
      )}

      {meetingMeta && (
        <div className="mb-4 p-3 rounded border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300">
          <p><strong>Mode:</strong> {meetingMeta.mode}</p>
          <p><strong>Series:</strong> {meetingMeta.seriesId}</p>
          <p><strong>RAG used:</strong> {meetingMeta.useRag ? (meetingMeta.ragContextUsed ? 'Yes (past context found)' : 'Yes (no past context yet)') : 'No'}</p>
          <p><strong>Stack:</strong> {meetingMeta.stack} (Deepgram + Gemini + ChromaDB)</p>
          {meetingMeta.shareUrl && (
            <div className="mt-2 pt-2 border-t border-gray-600">
              <p className="text-xs mb-1"><strong>Share link:</strong></p>
              <a href={meetingMeta.shareUrl} className="text-blue-400 text-xs break-all" target="_blank" rel="noreferrer">
                {meetingMeta.shareUrl}
              </a>
              <button
                onClick={() => { navigator.clipboard.writeText(meetingMeta.shareUrl); alert('Link copied!'); }}
                className="mt-2 text-xs bg-blue-600 text-white px-2 py-1 rounded"
              >
                Copy Share Link
              </button>
            </div>
          )}
        </div>
      )}

      {transcript && (
        <div className="mb-4">
          <h4 className="font-bold text-gray-900 dark:text-white mb-1">
            🎙️ Full Transcript {transcriptionInfo?.diarization?.enabled ? '(with speakers)' : ''}
          </h4>
          <div className="max-h-64 overflow-y-auto p-3 rounded bg-gray-100 dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-300 whitespace-pre-wrap">
            {transcript}
          </div>
        </div>
      )}

      {summary && (
        <div className="mb-4">
          <h4 className="font-bold text-gray-900 dark:text-white mb-1">📝 Summary</h4>
          <p className="whitespace-pre-wrap text-gray-800 dark:text-gray-300">{summary}</p>
        </div>
      )}

      {Array.isArray(actionItems) && actionItems.length > 0 && (
        <div className="mb-4">
          <h4 className="font-bold text-gray-900 dark:text-white mb-1">✅ Action Items</h4>
          <ul className="list-disc list-inside text-gray-800 dark:text-gray-300">
            {actionItems.map((item, index) => (
              <li key={index}>
                <strong>Task:</strong> {item.task}<br />
                <strong>Owner:</strong> {item.owner}<br />
                <strong>Deadline:</strong> {item.deadline}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(summary || actionItems.length > 0) && (
        <div className="flex flex-col gap-2">
          <button onClick={handleCopy} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900">
            📋 Copy to Clipboard
          </button>
          <button onClick={handleDownload} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
            💾 Download Summary
          </button>
          <a
            href={generateMailtoLink()}
            className="bg-purple-600 text-white px-4 py-2 rounded text-center hover:bg-purple-700"
          >
            📧 Send via Email
          </a>
          <button onClick={handleExportToNotion} className="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600">
            📓 Export to Notion
          </button>
        </div>
      )}
    </div>
  );
};

export default TranscriptInput;

