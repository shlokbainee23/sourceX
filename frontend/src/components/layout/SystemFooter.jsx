import React, { useEffect, useState } from 'react';
import { systemApi } from '../../services/api';

export default function SystemFooter() {
  const [healthy, setHealthy] = useState(true);

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await systemApi.getHealth();
        if (active) setHealthy(res.status === 'HEALTHY');
      } catch {
        if (active) setHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <footer className="h-9 bg-[#fafaf8] border-t border-[#e6e5e2] px-4 flex items-center justify-between text-[11px] font-mono text-[#8d8d8d] select-none z-30">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              healthy ? 'bg-[#2d6a4f]' : 'bg-[#8b3a2a]'
            }`}
          />
          <span className={healthy ? 'text-[#3a3a3a] font-medium' : 'text-[#8b3a2a] font-bold'}>
            {healthy ? 'ENGINE ONLINE (AIR-GAPPED)' : 'BACKEND DISCONNECTED'}
          </span>
        </div>
        <span className="text-[#d8d6d2] hidden sm:inline">|</span>
        <span className="hidden md:inline text-[#8d8d8d]">
          WESEE / MoD FORENSIC SYSTEM
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden lg:inline text-[#8d8d8d]">
          ALGORITHMS: FIPS 203 / FIPS 204
        </span>
        <span className="text-[#d8d6d2] hidden sm:inline">|</span>
        <span className="text-[#0a0a0a] font-semibold">
          STRICT FAIL-CLOSED ASSURANCE
        </span>
      </div>
    </footer>
  );
}
