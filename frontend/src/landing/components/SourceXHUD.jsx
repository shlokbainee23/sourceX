import React from 'react';
import { ArrowUp, Activity } from 'lucide-react';

export default function SourceXHUD({ activeStage = '01', scrollProgress = 0, onScrollToTop }) {
  const percent = Math.min(100, Math.max(0, Math.round(scrollProgress * 100)));

  return (
    <div className="fixed inset-x-0 bottom-0 pointer-events-none z-40 px-4 md:px-8 pb-5 flex items-end justify-between select-none">
      {/* Bottom Left: Defense Environment Telemetry (Advaith .experience-location style) */}
      <aside aria-label="System status" className="pointer-events-auto inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-white/85 backdrop-blur-md border border-[#e6e5e2] shadow-sm font-mono text-[10px] text-[#3a3a3a] tracking-wider uppercase transition-all duration-300 hover:border-[#b15f2c]">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#2d6a4f] opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2d6a4f]" />
        </span>
        <span className="hidden sm:inline text-[#8d8d8d]">DEFENSE CUSTODY:</span>
        <span className="font-bold text-[#0a0a0a]">AIR-GAP ACTIVE</span>
        <span className="text-[#8d8d8d] hidden md:inline">·</span>
        <span className="hidden md:inline text-[#8d8d8d]">FIPS-204</span>
        <span className="text-[#8d8d8d] hidden md:inline">·</span>
        <span className="hidden lg:inline text-[#b15f2c] font-semibold">BLOCK #004 HEAD</span>
      </aside>

      {/* Bottom Right: Live Scroll Progress Meter (Advaith .experience-menu style) */}
      <nav aria-label="Navigation controls" className="pointer-events-auto flex items-center gap-2 font-mono text-[11px]">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/85 backdrop-blur-md border border-[#e6e5e2] shadow-sm text-[#3a3a3a] tracking-wider">
          <Activity className="w-3 h-3 text-[#b15f2c] animate-pulse" />
          <span className="text-[#8d8d8d]">STREAM</span>
          <span className="font-bold text-[#0a0a0a] min-w-[32px] text-right">
            {String(percent).padStart(2, '0')}%
          </span>
          <span className="text-[#8d8d8d]">STAGE {activeStage}</span>
        </div>

        {percent > 8 && (
          <button
            type="button"
            onClick={onScrollToTop}
            aria-label="Scroll to top of investigation stream"
            className="w-8 h-8 rounded-full bg-white/90 backdrop-blur-md border border-[#e6e5e2] shadow-sm text-[#3a3a3a] hover:text-[#0a0a0a] hover:border-[#b15f2c] hover:bg-[#f1f0ee] transition-all flex items-center justify-center cursor-pointer"
            title="Return to origin"
          >
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
        )}
      </nav>
    </div>
  );
}
