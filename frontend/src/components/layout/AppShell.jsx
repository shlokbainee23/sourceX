import React, { useState } from 'react';
import DefenseHeader from './DefenseHeader';
import RoleNav from './RoleNav';
import SystemFooter from './SystemFooter';
import { Menu } from 'lucide-react';

export default function AppShell({ children }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-[#fafaf8] text-[#111111] overflow-x-hidden font-sans">
      <DefenseHeader />

      {/* Mobile Nav Bar Toggle */}
      <div className="lg:hidden bg-[#fafaf8] border-b border-[#e6e5e2] px-4 py-2 flex items-center justify-between text-xs font-mono text-[#0a0a0a]">
        <button
          type="button"
          onClick={() => setMobileNavOpen(true)}
          className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#ffffff] border border-[#d8d6d2] text-[#0a0a0a] shadow-xs hover:border-[#b15f2c] transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="w-4 h-4 text-[#b15f2c]" />
          <span className="font-semibold text-[11px] tracking-wider">WORKSPACE MENU</span>
        </button>
        <span className="text-[#8d8d8d] uppercase text-[11px] tracking-wider">SOURCE-X TERMINAL</span>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <RoleNav isOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 space-y-6">
          {children}
        </main>
      </div>

      <SystemFooter />
    </div>
  );
}
