import React from 'react';

function ProcessStatus() {
  return (
    <div className="relative overflow-hidden bg-gray-900 border border-purple-500 rounded-xl p-6 shadow-lg">
      <div
        className="absolute top-[-50%] left-[-75%] w-1/2 h-[200%] bg-gradient-to-r from-transparent via-white/30 to-transparent
        animate-shineMove pointer-events-none z-10"
        style={{ transform: 'skewX(-40deg)' }}
      />

      <h3 className="text-xl font-semibold text-purple-400 mb-4 relative z-20">How It Works</h3>
      <ol className="space-y-2 text-gray-300 list-decimal list-inside relative z-20">
        <li>Select an text or audio file</li>
        <li>Click on <strong>"Generate Summary"</strong></li>
        <li>Review AI summary & Action items</li>
        <li>Summary can be copy, download and emailed</li>
        <li className="text-purple-400">When you're redirected to this webpage via zoom extension click on "Generate Zoom Meeting Summary" for summary</li>
      </ol>
    </div>
  );
}

export default ProcessStatus;