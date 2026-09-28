import React from 'react';
import { TIMELINE_STAGES } from '../hooks/useScrollStory';

export default function InvestigationTimeline({ activeStage, scrollToStage }) {
  return (
    <aside
      aria-label="Investigation timeline"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-[#ffffff]/94 backdrop-blur-md border border-[#e6e5e2] px-3 py-1.5 rounded-full shadow-[0_12px_36px_-16px_rgba(10,10,10,0.18)] flex items-center gap-1.5 sm:gap-2 max-w-[95vw] overflow-x-auto scrollbar-none select-none transition-all"
    >
      <div className="hidden lg:flex items-center text-[10px] font-mono text-[#8d8d8d] uppercase tracking-[0.16em] pl-2 pr-2 border-r border-[#e6e5e2]">
        TIMELINE
      </div>

      <div className="flex items-center gap-1">
        {TIMELINE_STAGES.map((st) => {
          const isActive = st.index === activeStage;
          return (
            <button
              key={st.id}
              type="button"
              onClick={() => scrollToStage(st.id)}
              className={`px-2.5 py-1 rounded-full text-[10px] sm:text-[11px] font-mono tracking-tight transition-all flex items-center gap-1 cursor-pointer whitespace-nowrap ${
                isActive
                  ? 'bg-[#b15f2c]/12 border border-[#b15f2c]/45 text-[#97501f] font-bold shadow-xs'
                  : 'text-[#8d8d8d] hover:text-[#0a0a0a] hover:bg-[#f1f0ee]'
              }`}
              aria-current={isActive ? 'step' : undefined}
            >
              <span className={isActive ? 'text-[#b15f2c]' : 'text-[#b6b6b6]'}>
                {st.index}
              </span>
              <span className="hidden sm:inline">{st.label}</span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
