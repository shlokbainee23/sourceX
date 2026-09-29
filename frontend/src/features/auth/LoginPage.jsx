import React, { useEffect, useState } from 'react';
import {
  Anchor,
  Eye,
  EyeOff,
  Cpu,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../../app/AuthContext';
import { useRouter } from '../../app/RouterContext';
import { DEFAULT_STATIONS, SYSTEM_INFO } from '../../app/config';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import { systemApi } from '../../services/api';

export default function LoginPage() {
  const { login, isLoading, authError, clearError, requestedStation } = useAuth();
  const { navigate } = useRouter();
  const [selectedStation, setSelectedStation] = useState(requestedStation || DEFAULT_STATIONS[0].principal_id);
  const [passphrase, setPassphrase] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const result = await systemApi.getHealth();
        if (active) setBackendStatus(result?.status === 'HEALTHY' ? 'ready' : 'unavailable');
      } catch {
        if (active) setBackendStatus('unavailable');
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  const currentStation =
    DEFAULT_STATIONS.find((s) => s.principal_id === selectedStation) || DEFAULT_STATIONS[0];

  const handleSelectStation = (station) => {
    setSelectedStation(station.principal_id);
    setPassphrase('');
    if (authError) clearError();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!passphrase.trim() || backendStatus !== 'ready') return;
    await login(selectedStation, passphrase);
  };

  return (
    <div className="min-h-screen bg-[#fafaf8] text-[#111111] flex flex-col justify-between p-4 md:p-8 select-none font-sans">
      {/* Top Banner */}
      <header className="max-w-5xl mx-auto w-full flex items-center justify-between border-b border-[#e6e5e2] pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-white border border-[#d8d6d2] flex items-center justify-center text-[#b15f2c] shadow-xs">
            <Anchor className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm md:text-base font-bold tracking-wider text-[#0a0a0a] uppercase font-mono">
              {SYSTEM_INFO.authority}
            </h1>
            <p className="text-xs text-[#8d8d8d] font-mono tracking-tight">
              {SYSTEM_INFO.organization} · {SYSTEM_INFO.securityLevel}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-xs font-mono text-[#8d8d8d] hover:text-[#b15f2c] flex items-center gap-1.5 transition-colors cursor-pointer font-semibold"
          >
            <span>←</span>
            <span>SOURCE-X OVERVIEW</span>
          </button>

          <div className="hidden sm:flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded bg-[#2d6a4f]/08 border border-[#2d6a4f]/25 text-[#1b4332]">
            <span className="w-2 h-2 rounded-full bg-[#2d6a4f] animate-pulse" />
            <span className="font-semibold text-[11px]">LOCAL WORKSTATION ACCESS</span>
          </div>
        </div>
      </header>

      {/* Center Container */}
      <div className="max-w-4xl mx-auto w-full my-auto py-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
          {/* Station Selection Panel */}
          <div className="md:col-span-5 bg-white border border-[#e6e5e2] rounded-lg p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-[#8d8d8d] mb-1 font-semibold">
                Step 1: Select Operational Station
              </div>
              <h2 className="text-xs font-bold uppercase text-[#0a0a0a] tracking-wider mb-4 font-mono">
                Assigned Terminal Station
              </h2>

              <div className="space-y-2">
                {DEFAULT_STATIONS.map((st) => {
                  const isSelected = st.principal_id === selectedStation;
                  return (
                    <button
                      key={st.principal_id}
                      type="button"
                      onClick={() => handleSelectStation(st)}
                      className={`w-full text-left p-3 rounded border transition-all ${
                        isSelected
                          ? 'bg-[#b15f2c]/08 border-[#b15f2c] text-[#0a0a0a] shadow-xs'
                          : 'bg-white border-[#e6e5e2] text-[#3a3a3a] hover:border-[#d8d6d2] hover:bg-[#fafaf8]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold tracking-wide text-[#b15f2c]">
                          {st.principal_id}
                        </span>
                        <Badge status={st.role} size="xs" />
                      </div>
                      <div className="text-xs text-[#0a0a0a] font-medium mt-1 truncate">
                        {st.name}
                      </div>
                      <div className="text-[11px] text-[#8d8d8d] mt-0.5 truncate">
                        {st.rank}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-[#e6e5e2] text-[11px] font-mono text-[#8d8d8d] space-y-1">
              <div className="flex items-center gap-1.5 text-[#b15f2c] font-semibold">
                <Cpu className="w-3.5 h-3.5" />
                <span>PQC ENCRYPTION & SIGNING</span>
              </div>
              <p className="text-[10px] text-[#8d8d8d] leading-tight">
                ML-KEM-768 key encapsulation · ML-DSA-44 digital signatures · AES-256-GCM.
              </p>
            </div>
          </div>

          {/* Authentication Panel */}
          <div className="md:col-span-7 bg-white border border-[#d8d6d2] rounded-lg p-6 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-[#e6e5e2] pb-3 mb-4">
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-[#8d8d8d] font-semibold">
                    Step 2: Keystore Authentication
                  </div>
                  <h2 className="text-sm font-bold text-[#0a0a0a] uppercase tracking-wider mt-0.5 font-mono">
                    Unlock Station Keystore
                  </h2>
                </div>
                <Badge status={currentStation.role} size="sm" />
              </div>

              {/* Station Context Card */}
              <div className="p-3.5 bg-[#fafaf8] border border-[#e6e5e2] rounded-md text-xs mb-5 space-y-2 font-mono">
                <div className="flex justify-between">
                  <span className="text-[#8d8d8d]">PRINCIPAL ID:</span>
                  <span className="text-[#b15f2c] font-bold">{currentStation.principal_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8d8d8d]">OFFICER / DESK:</span>
                  <span className="text-[#0a0a0a] font-medium">{currentStation.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8d8d8d]">SECURITY ROLE:</span>
                  <span className="text-[#0a0a0a] font-medium">{currentStation.role}</span>
                </div>
                <p className="text-[11px] text-[#8d8d8d] font-sans pt-1 border-t border-[#e6e5e2]">
                  {currentStation.description}
                </p>
              </div>

              {backendStatus !== 'ready' && (
                <div role="status" className="mb-4 p-3 bg-[#b15f2c]/10 border border-[#b15f2c]/25 rounded text-xs text-[#5a2e12]">
                  <p className="font-semibold">{backendStatus === 'checking' ? 'Checking workstation connection…' : 'Workstation backend unavailable'}</p>
                  {backendStatus === 'unavailable' && <p className="mt-1">This page needs the local SourceX engine to sign in. Open your running local workstation to use encryption, investigation and auditing. Connection checks retry automatically.</p>}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label htmlFor="station-passphrase" className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] font-mono">
                      Station Keystore Passphrase
                    </label>
                  </div>
                  <div className="relative">
                    <input
                      id="station-passphrase"
                      autoComplete="current-password"
                      type={showPassword ? 'text' : 'password'}
                      value={passphrase}
                      onChange={(e) => {
                        setPassphrase(e.target.value);
                        if (authError) clearError();
                      }}
                      placeholder="Enter passphrase to unlock keystore..."
                      disabled={isLoading || backendStatus !== 'ready'}
                      required
                      autoFocus
                      className="w-full px-3.5 py-2.5 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-sm focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c] placeholder:text-[#8d8d8d] pr-10 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8d8d8d] hover:text-[#0a0a0a] p-1 transition-colors"
                      aria-label={showPassword ? 'Hide passphrase' : 'Show passphrase'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-[11px] text-[#8d8d8d] mt-1 font-mono">
                    Passphrase unlocks the local AES-256-GCM + scrypt software keystore.
                  </p>
                </div>

                {authError && (
                  <div className="p-3 bg-[#8b3a2a]/10 border border-[#8b3a2a]/30 rounded text-xs text-[#541a10] space-y-2">
                    <div className="flex items-start gap-2.5">
                      <AlertCircle className="w-4 h-4 text-[#8b3a2a] mt-0.5 shrink-0" />
                      <div>
                        <p className="font-semibold text-[#8b3a2a] uppercase tracking-wide font-mono text-[11px]">
                          Authentication Rejected
                        </p>
                        <p className="mt-0.5 text-[#541a10]">
                          {authError}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="pt-2">
                  <Button
                    type="submit"
                    variant="primary"
                    loading={isLoading}
                    disabled={!passphrase.trim() || isLoading || backendStatus !== 'ready'}
                    className="w-full py-2.5"
                    icon={ShieldCheck}
                  >
                    Authenticate & Enter Workspace
                  </Button>
                </div>
              </form>
            </div>

            <div className="mt-6 pt-3 border-t border-[#e6e5e2] text-[11px] text-[#8d8d8d] flex items-center justify-between font-mono">
              <span>LOCAL ENGINE REQUIRED</span>
              <span className="text-[#8d8d8d]">WESEE MoD SECURE ASSET</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Footer */}
      <footer className="max-w-5xl mx-auto w-full text-center text-[11px] font-mono text-[#8d8d8d] border-t border-[#e6e5e2] pt-4">
        {SYSTEM_INFO.name} · {SYSTEM_INFO.pqcStandards} · APPEND-ONLY LEDGER
      </footer>
    </div>
  );
}
