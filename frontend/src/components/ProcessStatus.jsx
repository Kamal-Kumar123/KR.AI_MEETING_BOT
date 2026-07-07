import React from 'react';

function ProcessStatus() {
  return (
    <div className="relative overflow-hidden bg-gray-900 border border-purple-500 rounded-xl p-6 shadow-lg">
      <div
        className="absolute top-[-50%] left-[-75%] w-1/2 h-[200%] bg-gradient-to-r from-transparent via-white/30 to-transparent
        animate-shineMove pointer-events-none z-10"
        style={{ transform: 'skewX(-40deg)' }}
      />

      <h3 className="text-xl font-semibold text-purple-400 mb-4 relative z-20">Extension Flow (Zoom Host)</h3>
      <ol className="space-y-2 text-gray-300 list-decimal list-inside relative z-20 text-sm">
        <li>Install extension → see <code className="text-purple-300">meet_extensiion/INSTALL.md</code></li>
        <li>Open Zoom in Chrome → <strong>Start Meeting Capture</strong></li>
        <li>After meeting → <strong>End Meeting & Open Share Page</strong></li>
        <li>Share link via Email / WhatsApp / Copy</li>
        <li className="text-purple-400">Or upload Zoom .mp4 recording here for all voices</li>
      </ol>
    </div>
  );
}

export default ProcessStatus;
