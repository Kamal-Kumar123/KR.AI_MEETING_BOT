import React, { useEffect, useMemo, useState } from 'react';
import Header from './Header';
import { useAuth } from '../context/AuthContext';
import { fetchMeetings, meetingUrl } from '../lib/api';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusBadge(status) {
  const colors = {
    ready: 'bg-green-500/20 text-green-300',
    processing: 'bg-yellow-500/20 text-yellow-300',
    transcribing: 'bg-yellow-500/20 text-yellow-300',
    awaiting_config: 'bg-purple-500/20 text-purple-300',
    failed: 'bg-red-500/20 text-red-300',
  };
  return colors[status] || 'bg-gray-500/20 text-gray-300';
}

function MeetingRow({ meeting }) {
  const href = meetingUrl(meeting.id, meeting.share_token);
  const duration = meeting.duration_seconds
    ? `${Math.max(1, Math.round(meeting.duration_seconds / 60))} min`
    : '';

  return (
    <a
      href={href}
      className="block p-4 rounded-lg border border-gray-700 bg-gray-900/40 hover:bg-gray-800/60 transition"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-white">{meeting.title || 'Untitled Meeting'}</h3>
          <p className="text-xs text-gray-400 mt-1">
            {meeting.platform}
            {duration ? ` · ${duration}` : ''}
            {' · '}
            {formatDate(meeting.recording_date || meeting.started_at)}
          </p>
        </div>
        <span className={`text-xs px-2 py-1 rounded ${statusBadge(meeting.status)}`}>
          {meeting.status}
        </span>
      </div>
      {meeting.summary?.executive_summary && (
        <p className="text-sm text-gray-400 mt-2 line-clamp-2">
          {meeting.summary.executive_summary}
        </p>
      )}
    </a>
  );
}

function MyMeetings() {
  const { user, loading: authLoading } = useAuth();
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      window.location.href = '/login';
      return;
    }
    fetchMeetings()
      .then(setMeetings)
      .catch(() => setError('Could not load meetings.'))
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return meetings;
    return meetings.filter(
      (m) =>
        (m.title || '').toLowerCase().includes(q) ||
        (m.series_id || '').toLowerCase().includes(q) ||
        (m.platform || '').toLowerCase().includes(q)
    );
  }, [meetings, search]);

  const { standalone, projects } = useMemo(() => {
    const stand = [];
    const projMap = {};

    for (const m of filtered) {
      if (m.meeting_mode === 'connected' && m.series_id) {
        if (!projMap[m.series_id]) projMap[m.series_id] = [];
        projMap[m.series_id].push(m);
      } else {
        stand.push(m);
      }
    }

    const projectList = Object.entries(projMap)
      .map(([seriesId, items]) => ({
        seriesId,
        meetings: items.sort(
          (a, b) => new Date(b.recording_date || 0) - new Date(a.recording_date || 0)
        ),
      }))
      .sort((a, b) => b.meetings.length - a.meetings.length);

    stand.sort((a, b) => new Date(b.recording_date || 0) - new Date(a.recording_date || 0));

    return { standalone: stand, projects: projectList };
  }, [filtered]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-gray-200 flex items-center justify-center">
        Loading your meetings…
      </div>
    );
  }

  return (
    <div className="bg-[#0f172a] text-gray-200 min-h-screen flex flex-col">
      <Header />
      <main className="max-w-5xl mx-auto px-6 py-8 w-full">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">My Meetings</h1>
            <p className="text-sm text-gray-400 mt-1">
              Extension recordings and manual uploads — standalone and project-wise
            </p>
          </div>
          <a
            href="/upload"
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg no-underline"
          >
            + Upload Meeting
          </a>
        </div>

        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, project, or platform…"
          className="w-full mb-8 px-4 py-2 rounded-lg bg-gray-900 border border-gray-600 text-sm"
        />

        {error && <p className="text-red-400 mb-4">{error}</p>}

        {filtered.length === 0 && !error && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-lg mb-2">No meetings yet</p>
            <p className="text-sm">Record with the extension or upload a file from the Upload page.</p>
            <a href="/upload" className="inline-block mt-4 text-blue-400 hover:text-blue-300">
              Upload a meeting →
            </a>
          </div>
        )}

        {standalone.length > 0 && (
          <section className="mb-10">
            <h2 className="text-lg font-bold text-purple-300 mb-1">Standalone Meetings</h2>
            <p className="text-xs text-gray-500 mb-4">Individual meetings with custom names</p>
            <div className="space-y-3">
              {standalone.map((m) => (
                <MeetingRow key={m.id} meeting={m} />
              ))}
            </div>
          </section>
        )}

        {projects.length > 0 && (
          <section>
            <h2 className="text-lg font-bold text-emerald-300 mb-1">Connected Projects</h2>
            <p className="text-xs text-gray-500 mb-4">
              Project meetings — RAG vector database updates with each new meeting
            </p>
            <div className="space-y-8">
              {projects.map(({ seriesId, meetings: projectMeetings }) => (
                <div key={seriesId}>
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="font-semibold text-white">{seriesId}</h3>
                    <span className="text-xs text-gray-500">
                      {projectMeetings.length} meeting{projectMeetings.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="space-y-3 pl-3 border-l-2 border-emerald-500/30">
                    {projectMeetings.map((m) => (
                      <MeetingRow key={m.id} meeting={m} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default MyMeetings;
