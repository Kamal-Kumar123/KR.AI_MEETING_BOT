import React, { useEffect, useState } from 'react';

function Header() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [showColon, setShowColon] = useState(true);

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
    <header className="relative flex items-center justify-between px-6 py-4 bg-gradient-to-r from-purple-700 via-indigo-700 to-purple-900 shadow-lg">
      <div
        className="tracking-wide px-4 py-2"
        style={{
          fontFamily: "'Montserrat', sans-serif",
          fontSize: '36px',
          fontWeight: 800,
          color: '#000',
          letterSpacing: '0.1em',
        }}
      >
        KRAI
      </div>

      <div className="text-center flex-1">
        <h1 className="text-3xl font-bold text-white">KR.AI BOT</h1>
        <br />
        <p className="text-gray-300 text-sm">
          AI-Powered Audio & Text File Transcription with Summarization
        </p>
      </div>

      <div className="w-10"></div>

      <div className="absolute bottom-2 right-6 text-right text-white">
        <p className="text-lg font-bold">
          {hours}
          <span className={`${showColon ? 'opacity-100' : 'opacity-0'} transition-opacity duration-300`}>
            :
          </span>
          {minutes}
        </p>
        <p className="text-sm font-bold">{weekday}</p>
        <p className="text-sm">{`${day} ${month} ${year}`}</p>
      </div>
    </header>
  );
}

export default Header;
