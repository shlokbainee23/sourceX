import React from 'react';
import { ArrowDown, Eye } from 'lucide-react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage01Opening({ onBegin }) {
  return (
    <section
      id="stage-origin"
      className="min-h-screen pt-28 pb-16 px-4 md:px-8 flex flex-col justify-between relative overflow-hidden"
    >
      {/* Background architectural grid */}
      <div className="absolute inset-0 sx-grid-pattern opacity-40 pointer-events-none" />

      {/* Top Editorial Identity */}
      <div className="max-w-5xl mx-auto w-full text-center space-y-4 pt-8 md:pt-14 relative z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#f1f0ee] border border-[#e6e5e2] text-[11px] font-mono text-[#b15f2c] tracking-wider uppercase mb-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#b15f2c] animate-ping" />
          <span>FORENSIC DOCUMENT ATTRIBUTION SYSTEM</span>
        </div>

        <h1 className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-black tracking-tight text-[#0a0a0a] uppercase sx-display select-none">
          {'SOURCE—X'.split('').map((char, index) => (
            <span
              key={index}
              className={`sx-flow-letter ${char === '—' ? 'text-[#b15f2c]' : ''}`}
              style={{ transitionDelay: `${index * 35}ms` }}
            >
              {char}
            </span>
          ))}
        </h1>

        <p className="text-xl sm:text-2xl md:text-3xl font-semibold tracking-wide text-[#111111] uppercase font-mono">
          TRACE THE ORIGIN.
        </p>

        <p className="max-w-2xl mx-auto text-sm md:text-base text-[#3a3a3a] font-sans leading-relaxed">
          A forensic attribution system for broadcast-encrypted documents. When classified materials leak, mathematical evidence establishes the origin.
        </p>

        {/* Primary Interactive Trigger */}
        <div className="pt-4 flex flex-wrap items-center justify-center gap-4">
          <button
            type="button"
            onClick={onBegin}
            className="sx-btn-primary cursor-pointer text-xs md:text-sm py-3 px-6 group"
          >
            <Eye className="w-4 h-4 text-[#cf8047] transition-transform duration-300 group-hover:scale-110" />
            <span>BEGIN INVESTIGATION</span>
            <ArrowDown className="w-4 h-4 text-[#cf8047] transition-transform duration-300 group-hover:translate-y-1 animate-bounce" />
          </button>
        </div>
      </div>

      {/* Persistent Story Object Entrance with 3D perspective staging */}
      <div className="max-w-lg mx-auto w-full my-12 relative z-10 perspective-1000">
        <div className="text-center mb-3 text-[10px] font-mono uppercase tracking-widest text-[#8d8d8d]">
          STAGE 01 // CANONICAL SENDER DIRECTIVE
        </div>
        <div className="transform-3d transition-transform duration-500 hover:rotate-x-1 hover:rotate-y-1">
          <DocumentStoryObject
            state="DOCUMENT"
            docId="DOC-2026-FLEET-08"
            docHash="64e94e7e0434c78dd1281ce5d90cd58253d1ede02600eacedd70c9fa077557c5"
          />
        </div>
      </div>

      {/* Editorial Pause Question */}
      <div className="max-w-3xl mx-auto w-full text-center space-y-3 pb-8 relative z-10 border-t border-[#e6e5e2] pt-8">
        <p className="text-base sm:text-lg text-[#3a3a3a] font-medium">
          Every document has a source.
        </p>
        <p className="text-lg sm:text-2xl font-bold font-mono text-[#b15f2c] tracking-wide">
          BUT CAN YOU PROVE IT?
        </p>
      </div>
    </section>
  );
}
