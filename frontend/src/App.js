import React, { useState } from 'react';
import Header from './components/Header';
import TranscriptInput from './components/TranscriptInput';
import ProcessStatus from './components/ProcessStatus';
import FeatureCards from './components/FeatureCards';
import SplashScreen from './components/SplashScreen';
import MeetingShare from './components/MeetingShare';

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const params = new URLSearchParams(window.location.search);
  const meetingId = params.get('meeting_id');

  if (meetingId) {
    return <MeetingShare meetingId={meetingId} />;
  }

  return (
    <>
      {showSplash ? (
        <SplashScreen onComplete={() => setShowSplash(false)} />
      ) : (
        <div className="bg-[#0f172a] text-gray-200 min-h-screen flex flex-col animate-smoothScaleFadeIn" style={{ backgroundColor: '#0f172a' }}>
          <Header />
          <main className="flex flex-col items-center px-6 py-8 space-y-8">
            <div className="w-full max-w-7xl flex flex-col md:flex-row md:space-x-6 space-y-6 md:space-y-0">
              <div className="flex-1">
                <TranscriptInput />
              </div>
              <div className="w-full md:w-1/3">
                <ProcessStatus />
              </div>
            </div>
            <FeatureCards />
          </main>
        </div>
      )}
    </>
  );
}

export default App;
