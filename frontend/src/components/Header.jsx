import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

const navBtn =
  'inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-full border border-white/30 bg-white/10 hover:bg-white/20 text-white no-underline transition whitespace-nowrap';

function Header({ showAuth = true }) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [showColon, setShowColon] = useState(true);
  const { user, signOut } = useAuth();
  const path = window.location.pathname;
  const onUploadPage = path === '/upload';
  const onMeetingsPage = path === '/meetings';

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
      setShowColon((prev) => !prev);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const weekday = currentTime.toLocaleDateString('en-GB', { weekday: 'long' });
  const day = currentTime.getDate();
  const month = currentTime.toLocaleDateString('en-GB', { month: 'long' });
  const year = currentTime.getFullYear();
  const hours = String(currentTime.getHours()).padStart(2, '0');
  const minutes = String(currentTime.getMinutes()).padStart(2, '0');

  return (
    <header className="flex items-start justify-between gap-4 px-6 py-4 bg-gradient-to-r from-purple-700 via-indigo-700 to-purple-900 shadow-lg">
      <a
        href={user ? '/meetings' : '/'}
        className="tracking-wide shrink-0 no-underline pt-1"
        style={{
          fontFamily: "'Montserrat', sans-serif",
          fontSize: '36px',
          fontWeight: 800,
          color: '#000',
          letterSpacing: '0.1em',
        }}
      >
        KRAI
      </a>

      <div className="text-center flex-1 min-w-0 pt-1 px-2">
        <h1 className="text-2xl md:text-3xl font-bold text-white leading-tight">KR.AI BOT</h1>
        <p className="text-gray-300 text-xs md:text-sm mt-1">
          AI-Powered Audio & Text File Transcription with Summarization
        </p>
      </div>

      <div className="shrink-0 flex flex-col items-end gap-3 min-w-[200px]">
        {showAuth && user && (
          <div className="flex flex-col items-end gap-2 w-full">
            <div className="flex flex-wrap items-center justify-end gap-2">
              {!onUploadPage && (
                <a href="/upload" className={navBtn}>
                  Upload Meeting
                </a>
              )}
              {!onMeetingsPage && (
                <a href="/meetings" className={navBtn}>
                  <span aria-hidden="true">&larr;</span> Back to My Meetings
                </a>
              )}
              <button
                type="button"
                onClick={signOut}
                className="text-xs font-medium px-3 py-1.5 rounded-full border border-red-300/40 bg-red-500/20 hover:bg-red-500/35 text-white transition"
              >
                Logout
              </button>
            </div>
            <span className="text-[11px] text-gray-300/90 max-w-[200px] truncate text-right">
              {user.email}
            </span>
          </div>
        )}

        <div className="text-right text-white leading-tight">
          <p className="text-lg font-bold">
            {hours}
            <span className={`${showColon ? 'opacity-100' : 'opacity-0'} transition-opacity duration-300`}>:</span>
            {minutes}
          </p>
          <p className="text-xs font-semibold text-gray-200">{weekday}</p>
          <p className="text-[11px] text-gray-300">{`${day} ${month} ${year}`}</p>
        </div>
      </div>
    </header>
  );
}

export default Header;
