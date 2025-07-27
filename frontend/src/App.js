import React, { useState } from 'react';
import Header from './components/Header';
import TranscriptInput from './components/TranscriptInput';
import ProcessStatus from './components/ProcessStatus';
import FeatureCards from './components/FeatureCards';
import SplashScreen from './components/SplashScreen';

function App() {
  const [showSplash, setShowSplash] = useState(true);

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
            {/* <br></br> */}
            <FeatureCards />
          </main>
        </div>
      )}
    </>
  );
}
export default App;

// import React, { useEffect } from 'react';
// import Header from './components/Header';
// import TranscriptInput from './components/TranscriptInput';
// import ProcessStatus from './components/ProcessStatus';
// import FeatureCards from './components/FeatureCards';
// import SplashScreen from './components/SplashScreen';
// import './App.css';

// function App() {
//   useEffect(() => {
//     document.title = "Meeting Summarizer Agent";
//   }, []);

//   return (
//     <div className="app-container" style={{ backgroundColor: '#f4f6fb', minHeight: '100vh' }}>
//       <Header />
//       <main className="main-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '20px' }}>
//         <div className="top-section" style={{ display: 'flex', justifyContent: 'space-between', width: '90%', maxWidth: '1200px', marginBottom: '30px' }}>
//           <TranscriptInput />
//           <ProcessStatus />
//         </div>
//         <FeatureCards />
//       </main>
//     </div>
//   );
// }

// export default App;