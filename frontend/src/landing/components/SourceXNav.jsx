import React from 'react';
import { useRouter } from '../../app/RouterContext';
import { useAuth } from '../../app/AuthContext';
import { ArrowUpRight, Shield } from 'lucide-react';

export default function SourceXNav() {
  const { navigate } = useRouter();
  const { isAuthenticated, user, getDefaultRouteForRole } = useAuth();

  const handleEnterWorkstation = () => {
    if (isAuthenticated && user?.role) {
      navigate(getDefaultRouteForRole(user.role));
    } else {
      navigate('/login');
    }
  };

  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#ffffff]/92 backdrop-blur-md border-b border-[#e6e5e2] px-4 md:px-8 py-3 transition-all shadow-[0_1px_3px_rgba(10,10,10,0.03)]">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <a
            href="#/"
            className="flex items-center gap-2.5 group text-decoration-none"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          >
            <div className="w-7 h-7 rounded-[8px] bg-[#0a0a0a] border border-[#0a0a0a] flex items-center justify-center text-[#f1f0ee] relative group-hover:bg-[#b15f2c] group-hover:border-[#b15f2c] transition-colors">
              <span className="font-mono text-xs font-semibold">X</span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#b15f2c] group-hover:bg-white absolute -top-0.5 -right-0.5 transition-colors" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-xs md:text-sm tracking-[0.2em] text-[#0a0a0a] uppercase font-mono">
                SOURCE-X
              </span>
              <span className="text-[9px] font-mono tracking-[0.16em] text-[#b15f2c] uppercase font-semibold">
                TRACE THE ORIGIN
              </span>
            </div>
          </a>
        </div>

        {/* Minimal Orientation Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-7 text-xs font-mono tracking-wider text-[#8d8d8d]">
          <button
            type="button"
            onClick={() => scrollTo('stage-origin')}
            className="hover:text-[#0a0a0a] transition-colors cursor-pointer"
          >
            <span className="text-[#b6b6b6] mr-1">01</span>ORIGIN
          </button>
          <button
            type="button"
            onClick={() => scrollTo('stage-provenance')}
            className="hover:text-[#0a0a0a] transition-colors cursor-pointer"
          >
            <span className="text-[#b6b6b6] mr-1">02</span>PROVENANCE
          </button>
          <button
            type="button"
            onClick={() => scrollTo('stage-investigation')}
            className="hover:text-[#0a0a0a] transition-colors cursor-pointer"
          >
            <span className="text-[#b6b6b6] mr-1">03</span>INVESTIGATION
          </button>
          <button
            type="button"
            onClick={() => scrollTo('stage-verification')}
            className="hover:text-[#0a0a0a] transition-colors cursor-pointer"
          >
            <span className="text-[#b6b6b6] mr-1">04</span>VERIFICATION
          </button>
        </nav>

        {/* Primary Operational Action */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleEnterWorkstation}
            className="sx-btn-primary cursor-pointer text-xs"
            aria-label="Enter SOURCE-X Operational Workstation"
          >
            <Shield className="w-3.5 h-3.5 text-[#cf8047]" />
            <span>ENTER SOURCE-X</span>
            <ArrowUpRight className="w-3 h-3 text-[#f1f0ee]" />
          </button>
        </div>
      </div>
    </header>
  );
}
