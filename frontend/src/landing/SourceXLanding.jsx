import React from 'react';
import { useLenis } from './hooks/useLenis';
import { useScrollStory } from './hooks/useScrollStory';
import SourceXNav from './components/SourceXNav';
import InvestigationTimeline from './components/InvestigationTimeline';
import SourceXHUD from './components/SourceXHUD';

// 18 Narrative Stages
import Stage01Opening from './components/Stage01Opening';
import Stage02ImpossibleQuestion from './components/Stage02ImpossibleQuestion';
import Stage03TheProblem from './components/Stage03TheProblem';
import Stage04RewindDecryption from './components/Stage04RewindDecryption';
import Stage05ProvenanceEvent from './components/Stage05ProvenanceEvent';
import Stage06TimePasses from './components/Stage06TimePasses';
import Stage07EvidenceRoom from './components/Stage07EvidenceRoom';
import Stage08ForensicLens from './components/Stage08ForensicLens';
import Stage09TenQuestions from './components/Stage09TenQuestions';
import Stage10ChainTension from './components/Stage10ChainTension';
import Stage11Verified from './components/Stage11Verified';
import Stage12Unverified from './components/Stage12Unverified';
import Stage13FollowTheChain from './components/Stage13FollowTheChain';
import Stage14FourPerspectives from './components/Stage14FourPerspectives';
import Stage15CryptoFoundation from './components/Stage15CryptoFoundation';
import Stage16SystemQuestioned from './components/Stage16SystemQuestioned';
import Stage17FinalReveal from './components/Stage17FinalReveal';
import Stage18EntryCTA from './components/Stage18EntryCTA';

import './styles/sourcex.css';

export default function SourceXLanding() {
  // Initialize Lenis smooth scroll
  useLenis(true);

  // Initialize timeline and scroll story tracking
  const { activeStage, scrollProgress, scrollToStage } = useScrollStory();

  const handleBeginInvestigation = () => {
    scrollToStage('distribution');
  };

  const handleWitnessRewind = () => {
    scrollToStage('provenance');
  };

  const handleStartInvestigation = () => {
    scrollToStage('investigation');
  };

  const handleResolveAttribution = () => {
    scrollToStage('verification');
  };

  return (
    <div className="sourcex-root min-h-screen bg-[#fafaf8] text-[#111111] flex flex-col relative selection:bg-[#b15f2c] selection:text-white">
      {/* Minimal Orientation Bar */}
      <SourceXNav />

      {/* Persistent Floating Timeline Tracker */}
      <InvestigationTimeline
        activeStage={activeStage}
        scrollToStage={scrollToStage}
      />

      {/* Fixed Telemetry HUD (inspired by advaithdabilipuram-com) */}
      <SourceXHUD
        activeStage={activeStage}
        scrollProgress={scrollProgress}
        onScrollToTop={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      />

      {/* Main Narrative Investigation Stream */}
      <main className="flex-1 flex flex-col">
        {/* Stage 01: Opening */}
        <Stage01Opening onBegin={handleBeginInvestigation} />

        {/* Stage 02: The Impossible Question */}
        <Stage02ImpossibleQuestion />

        {/* Stage 03: The Problem */}
        <Stage03TheProblem onProceed={handleWitnessRewind} />

        {/* Stage 04: Rewind / Decryption */}
        <Stage04RewindDecryption />

        {/* Stage 05: Provenance Event */}
        <Stage05ProvenanceEvent />

        {/* Stage 06: Time Passes */}
        <Stage06TimePasses onProceed={handleStartInvestigation} />

        {/* Editorial Chapter Bridge (Advaith .about-type-bridge style) */}
        <div className="py-14 px-4 md:px-8 border-y border-[#e6e5e2] bg-[#f1f0ee]/40 text-center select-none overflow-hidden">
          <div className="max-w-4xl mx-auto space-y-2">
            <div className="text-[10px] font-mono text-[#b15f2c] uppercase tracking-widest font-bold">
              FORENSIC TRANSITION // AIR-GAP EXTRACTION
            </div>
            <div className="text-2xl sm:text-4xl md:text-5xl sx-type-bridge">
              ZERO RUNTIME SOCKETS <em>→</em> 100% MATHEMATICAL TRUTH
            </div>
          </div>
        </div>

        {/* Stage 07: Evidence Room */}
        <Stage07EvidenceRoom />

        {/* Stage 08: Forensic Lens */}
        <Stage08ForensicLens />

        {/* Stage 09: Ten Questions */}
        <Stage09TenQuestions onComplete={handleResolveAttribution} />

        {/* Stage 10: Chain Tension */}
        <Stage10ChainTension onResolve={handleResolveAttribution} />

        {/* Stage 11: Verified Attribution */}
        <Stage11Verified />

        {/* Stage 12: Unverified Fail-Closed Standard */}
        <Stage12Unverified />

        {/* Editorial Chapter Bridge (Advaith .services-proof-bridge style) */}
        <div className="py-14 px-4 md:px-8 border-y border-[#e6e5e2] bg-[#f1f0ee]/40 text-center select-none overflow-hidden">
          <div className="max-w-4xl mx-auto space-y-2">
            <div className="text-[10px] font-mono text-[#b15f2c] uppercase tracking-widest font-bold">
              FORENSIC COVENANT // THE COMPLETE STANDARD
            </div>
            <div className="text-2xl sm:text-4xl md:text-5xl sx-type-bridge">
              FAIL-CLOSED INTEGRITY <em>→</em> UNBROKEN PROVENANCE CHAIN
            </div>
          </div>
        </div>

        {/* Stage 13: Follow The Chain */}
        <Stage13FollowTheChain />

        {/* Stage 14: Four Perspectives */}
        <Stage14FourPerspectives />

        {/* Stage 15: Cryptographic Foundation */}
        <Stage15CryptoFoundation />

        {/* Stage 16: Built To Be Questioned */}
        <Stage16SystemQuestioned />

        {/* Stage 17: Final Reveal */}
        <Stage17FinalReveal />

        {/* Stage 18: Entry CTA */}
        <Stage18EntryCTA />
      </main>

      {/* Minimalist Editorial Colophon */}
      <footer className="py-8 px-4 md:px-8 border-t border-[#e6e5e2] bg-[#f1f0ee] text-center font-mono text-[11px] text-[#8d8d8d]">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-[#3a3a3a] font-medium">SOURCE-X // FORENSIC DOCUMENT ATTRIBUTION SYSTEM</span>
          <span>WESEE · MINISTRY OF DEFENCE · RESTRICTED ASSET</span>
        </div>
      </footer>
    </div>
  );
}
