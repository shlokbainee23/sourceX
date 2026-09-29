import React, { useState, useRef, useEffect } from 'react';
import { Anchor, Cpu, LogOut, UserCheck, ArrowLeftRight, ChevronDown } from 'lucide-react';
import { useAuth } from '../../app/AuthContext';
import { DEFAULT_STATIONS } from '../../app/config';
import ConfirmModal from '../common/ConfirmModal';
import Badge from '../common/Badge';

export default function DefenseHeader() {
  const { user, logout, switchStation } = useAuth();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showStationMenu, setShowStationMenu] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowStationMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <>
      <header className="h-14 bg-white border-b border-[#e6e5e2] px-4 md:px-6 flex items-center justify-between z-30 select-none shadow-xs">
        {/* Left: Organization & Identity */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[#fafaf8] border border-[#d8d6d2] flex items-center justify-center shrink-0 text-[#b15f2c]">
            <Anchor className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-xs md:text-sm tracking-wider text-[#0a0a0a] uppercase font-mono">
                WESEE · MoD
              </span>
              <span className="hidden sm:inline-block text-[10px] text-[#d8d6d2] font-mono">
                |
              </span>
              <span className="hidden sm:inline-block text-xs font-semibold text-[#b15f2c] tracking-wide font-mono">
                SOURCE-X WORKSTATION
              </span>
            </div>
            <div className="text-[10px] text-[#8d8d8d] font-mono tracking-tight hidden md:block">
              POST-QUANTUM AIR-GAPPED FORENSIC ATTRIBUTION SYSTEM
            </div>
          </div>
        </div>

        {/* Center: System Posture Telemetry */}
        <div className="hidden lg:flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#2d6a4f]/08 border border-[#2d6a4f]/25 text-[#1b4332]">
            <span className="w-2 h-2 rounded-full bg-[#2d6a4f] animate-pulse" />
            <span className="text-[11px] font-semibold">LOCAL ENGINE WORKSTATION</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#fafaf8] border border-[#e6e5e2] text-[#3a3a3a]">
            <Cpu className="w-3.5 h-3.5 text-[#b15f2c]" />
            <span className="text-[11px]">ML-KEM-768 · ML-DSA-44</span>
          </div>
        </div>

        {/* Right: Active Principal & Session Control */}
        <div className="flex items-center gap-3">
          {user && (
            <div className="flex items-center gap-2.5">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-[#0a0a0a] tracking-wide flex items-center justify-end gap-1.5 font-mono">
                  <UserCheck className="w-3.5 h-3.5 text-[#b15f2c]" />
                  <span>{user.principal_id}</span>
                </div>
                <div className="text-[10px] text-[#8d8d8d] truncate max-w-[140px]">
                  {user.name || user.role}
                </div>
              </div>

              <Badge status={user.role} size="xs" />

              {/* Station Switcher Dropdown */}
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setShowStationMenu(!showStationMenu)}
                  title="Switch Operational Station"
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-white hover:bg-[#fafaf8] border border-[#d8d6d2] hover:border-[#b15f2c] text-xs font-mono text-[#0a0a0a] transition-all shadow-xs"
                >
                  <ArrowLeftRight className="w-3.5 h-3.5 text-[#b15f2c]" />
                  <span className="hidden md:inline font-semibold">Switch Station</span>
                  <ChevronDown className={`w-3.5 h-3.5 text-[#8d8d8d] transition-transform ${showStationMenu ? 'rotate-180' : ''}`} />
                </button>

                {showStationMenu && (
                  <div className="absolute right-0 mt-2 w-72 bg-white border border-[#d8d6d2] rounded-lg shadow-xl py-2 z-50 text-left font-sans">
                    <div className="px-3 py-1.5 border-b border-[#e6e5e2] text-[11px] font-mono text-[#8d8d8d] uppercase tracking-wider">
                      Switch Role & Station
                    </div>
                    <div className="max-h-80 overflow-y-auto py-1 space-y-0.5">
                      {DEFAULT_STATIONS.map((st) => {
                        const isCurrent = st.principal_id === user.principal_id;
                        return (
                          <button
                            key={st.principal_id}
                            type="button"
                            onClick={async () => {
                              setShowStationMenu(false);
                              if (!isCurrent) {
                                await switchStation(st.principal_id);
                              }
                            }}
                            className={`w-full px-3 py-2 text-left flex items-start gap-2.5 transition-colors ${
                              isCurrent
                                ? 'bg-[#b15f2c]/08 border-l-2 border-[#b15f2c] text-[#0a0a0a]'
                                : 'hover:bg-[#fafaf8] text-[#3a3a3a]'
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-1">
                                <span className="font-mono text-xs font-bold text-[#b15f2c]">
                                  {st.principal_id}
                                </span>
                                <Badge status={st.role} size="xs" />
                              </div>
                              <div className="text-xs text-[#0a0a0a] font-medium truncate mt-0.5">
                                {st.name}
                              </div>
                              <div className="text-[10px] text-[#8d8d8d] truncate">
                                {st.rank}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => setShowLogoutConfirm(true)}
                title="End secure station session"
                className="p-1.5 rounded bg-white hover:bg-[#8b3a2a]/10 border border-[#d8d6d2] hover:border-[#8b3a2a]/30 text-[#8d8d8d] hover:text-[#8b3a2a] transition-colors"
                aria-label="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </header>

      <ConfirmModal
        isOpen={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        onConfirm={() => {
          setShowLogoutConfirm(false);
          logout();
        }}
        title="Lock & Terminate Session"
        message="Are you sure you want to end your secure terminal session?"
        consequences="Your server-side bearer session will be invalidated. Any keys unlocked in memory will be scrubbed immediately."
        reversible={true}
        confirmText="Lock Station & Logout"
        variant="danger"
      />
    </>
  );
}
