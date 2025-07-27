import React from 'react';

function FeatureCards() {
  const features = [
    { emoji: '🎧', title: 'Supports Audio & Text', desc: 'Upload MP3 or TXT files for processing' },
    { emoji: '⚡', title: 'Action Item Generation', desc: 'Get action item content in seconds using AI' },
    { emoji: '📚', title: 'Summary Generation', desc: 'Automatically generates key takeaways from the transcript' },
    {
      emoji: '📝',
      title: (
        <>
          Export to Notion{' '}
          <span className="text-xs text-gray-500">(In next version)</span>
        </>
      ),
      desc: 'Save notes directly to your Notion workspace (coming soon)',
    },
    { emoji: '📧', title: 'Share via Email', desc: 'Email summary and action items' },
    { emoji: '📋', title: 'Copy Summary', desc: 'Quickly copy the generated summary to clipboard' },
  ];

  return (
    <section className="w-full max-w-7xl mx-auto px-4 py-8">
      
      <div className="relative inline-block mb-6 overflow-hidden">
        <h2
          className="
            text-4xl 
            font-extrabold 
            bg-gradient-to-r 
            from-purple-400 
            via-blue-500 
            to-yellow-400 
            bg-clip-text 
            text-transparent 
            relative 
            z-10
          "
        >
          Features -
        </h2>
        
        <span
          className="
            pointer-events-none 
            absolute 
            top-0 
            left-[-75%] 
            w-[150%] 
            h-full 
            bg-gradient-to-r 
            from-transparent 
            via-white/40 
            to-transparent 
            animate-shineMove
          "
        ></span>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((item, idx) => (
          <div
            key={idx}
            className="
              relative
              rounded-xl
              border-[0.5px]
              p-6
              shadow-md
              hover:shadow-lg
              transition
              bg-gray-800
              border-4
              border-transparent
              before:absolute
              before:inset-0
              before:rounded-xl
              before:border-[2px]
              before:border-gradient
              before:border-t-pink-500
              before:border-r-yellow-500
              before:border-b-green-500
              before:border-l-blue-500
              before:animate-borderMove
              before:pointer-events-none
            "
          >
            <h3 className="text-lg font-semibold text-teal-400 mb-2">
              {item.emoji} {item.title}
            </h3>
            <p className="text-gray-400">{item.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default FeatureCards;

