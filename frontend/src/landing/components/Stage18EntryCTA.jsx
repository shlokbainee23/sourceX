import React from 'react';
import { useRouter } from '../../app/RouterContext';
import { useAuth } from '../../app/AuthContext';
import { ShieldCheck, ArrowRight, RotateCcw, Cpu } from 'lucide-react';

export default function Stage18EntryCTA() {
  const { navigate } = useRouter();
  const { isAuthenticated, user, getDefaultRouteForRole } = useAuth();

  const handleEnter = () => {
    if (isAuthenticated && user?.role) {
      navigate(getDefaultRouteForRole(user.role));
    } else {
      navigate('/login');
    }
  };

  const handleRestart = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <section className="py-24 px-4 md:px-8 border-t border-[#e6e5e2] bg-[#f1f0ee] relative">
      <div className="max-w-4xl mx-auto text-center space-y-10">
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-[#e6e5e2] text-xs font-mono text-[#3a3a3a] shadow-sm">
            <Cpu className="w-3.5 h-3.5 text-[#b15f2c]" />
            <span>OPERATIONAL FORENSIC WORKSTATION</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            ENTER THE OPERATIONAL SYSTEM.
          </h2>

          <p className="max-w-xl mx-auto text-[#3a3a3a] text-sm md:text-base font-sans leading-relaxed">
            Secure provenance. Verifiable evidence. Defensible attribution. Enter your station terminal to dispatch, decrypt, investigate, or audit.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4">
          <button
            type="button"
            onClick={handleEnter}
            className="sx-btn-primary cursor-pointer text-sm py-3.5 px-8 shadow-sm"
          >
            <ShieldCheck className="w-4 h-4 text-[#cf8047]" />
            <span>ENTER SOURCE-X</span>
            <ArrowRight className="w-4 h-4 text-[#cf8047]" />
          </button>

          <button
            type="button"
            onClick={handleRestart}
            className="sx-btn-secondary cursor-pointer text-sm py-3.5 px-6"
          >
            <RotateCcw className="w-3.5 h-3.5 text-[#8d8d8d]" />
            <span>EXPLORE THE SYSTEM</span>
          </button>
        </div>

        {/* Operational Telemetry Guarantee Footer */}
        <div className="pt-12 border-t border-[#e6e5e2] grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono text-[#8d8d8d]">
          <div>
            <span className="text-[#0a0a0a] block font-semibold">AIR-GAPPED ENVIRONMENT</span>
            Zero runtime network transmissions
          </div>
          <div>
            <span className="text-[#0a0a0a] block font-semibold">POST-QUANTUM STANDARDS</span>
            FIPS 203 (ML-KEM) · FIPS 204 (ML-DSA)
          </div>
          <div>
            <span className="text-[#0a0a0a] block font-semibold">FAIL-CLOSED PROTOCOL</span>
            Zero attribution without complete proof
          </div>
        </div>
      </div>
    </section>
  );
}
