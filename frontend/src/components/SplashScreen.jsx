import React, { useEffect } from "react";

const SplashScreen = ({ onComplete }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete();
    }, 2000); // match animation duration

    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="fixed inset-0 bg-[#0f172a] flex flex-col justify-center items-center z-50">
      <div className="text-center animate-riseFadeOut">
        <h1 className="text-4xl md:text-6xl font-extrabold tracking-widest leading-tight text-cyan-300">
          KRAI'S
          <br />
          <span className="block mt-2" style={{ color: '#ff1a1a' }}>
            BOT
          </span>
        </h1>
      </div>
    </div>
  );
};

export default SplashScreen;
