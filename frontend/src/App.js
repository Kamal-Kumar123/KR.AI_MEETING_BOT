import React from 'react';
import MeetingShare from './components/MeetingShare';
import LoginPage from './components/LoginPage';
import MyMeetings from './components/MyMeetings';
import ManualUpload from './components/ManualUpload';
import { useAuth } from './context/AuthContext';

function App() {
  const { user, loading } = useAuth();
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const meetingId = params.get('meeting_id');

  // Share links work without login
  if (meetingId) {
    return <MeetingShare meetingId={meetingId} />;
  }

  if (path === '/upload') {
    return <ManualUpload />;
  }

  if (path === '/meetings') {
    return <MyMeetings />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-gray-200 flex items-center justify-center">
        Loading…
      </div>
    );
  }

  // Default start page: login (also handles /login)
  if (user) {
    window.location.replace('/meetings');
    return null;
  }

  return <LoginPage />;
}

export default App;
