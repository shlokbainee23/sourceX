import React from 'react';
import {
  FileText,
  Users,
  KeyRound,
  Inbox,
  Lock,
  Search,
  Eye,
  Archive,
  Layers,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { useAuth } from '../../app/AuthContext';
import { useRouter } from '../../app/RouterContext';

const NAV_CONFIG = {
  AUTHORITY: [
    {
      path: '/authority/directives',
      label: 'Directives',
      icon: FileText,
      description: 'Document registration & broadcast encryption',
    },
    {
      path: '/authority/personnel',
      label: 'Personnel Registry',
      icon: Users,
      description: 'Officer directory & enrolment codes',
    },
    {
      path: '/authority/trust',
      label: 'Trust Desk',
      icon: KeyRound,
      description: 'Authority pin, manifest & attestations',
    },
    {
      path: '/authority/audit',
      label: 'System Audit',
      icon: FileSpreadsheet,
      description: 'Authority activity log',
    },
  ],
  RECIPIENT: [
    {
      path: '/recipient/inbox',
      label: 'Directive Inbox',
      icon: Inbox,
      description: 'Assigned encrypted directives',
    },
    {
      path: '/recipient/decrypt',
      label: 'Decryption Terminal',
      icon: Lock,
      description: 'Step-up decrypt & one-time download',
    },
    {
      path: '/recipient/keys',
      label: 'Station Key Status',
      icon: KeyRound,
      description: 'Public key fingerprint & attestation',
    },
  ],
  INVESTIGATOR: [
    {
      path: '/investigator/intake',
      label: 'Forensic Intake',
      icon: Search,
      description: '10-point fail-closed attribution',
    },
    {
      path: '/investigator/invariance',
      label: 'Visual Invariance',
      icon: Eye,
      description: '150-DPI raster forensic comparison',
    },
    {
      path: '/investigator/dossiers',
      label: 'Dossier Archive',
      icon: Archive,
      description: 'Verified signed investigation reports',
    },
  ],
  AUDITOR: [
    {
      path: '/auditor/ledger',
      label: 'Ledger Explorer',
      icon: Layers,
      description: 'Tamper-evident hash chain inspection',
    },
    {
      path: '/auditor/integrity',
      label: 'Chain Verification',
      icon: CheckCircle,
      description: 'Merkle & signature cryptographic verification',
    },
    {
      path: '/auditor/audit',
      label: 'Audit Trail',
      icon: FileSpreadsheet,
      description: 'Immutable system audit records',
    },
    {
      path: '/auditor/tamper',
      label: 'Tamper Sandbox',
      icon: AlertTriangle,
      description: 'Adversarial simulation & fail test',
    },
  ],
};

export default function RoleNav({ isOpen, onClose }) {
  const { user } = useAuth();
  const { currentPath, navigate } = useRouter();

  if (!user) return null;

  const items = NAV_CONFIG[user.role] || [];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-[#0a0a0a]/40 backdrop-blur-xs z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Navigation Sidebar */}
      <aside
        className={`fixed lg:static top-14 bottom-10 left-0 w-64 bg-white border-r border-[#e6e5e2] flex flex-col z-40 transition-transform duration-200 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4 border-b border-[#e6e5e2] bg-[#fafaf8]">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[#8d8d8d]">
            Operational Workspace
          </div>
          <div className="text-xs font-bold text-[#0a0a0a] tracking-wider mt-0.5 uppercase font-mono">
            {user.role} TERMINAL
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {items.map((item) => {
            const Icon = item.icon;
            const isActive = currentPath === item.path || currentPath.startsWith(item.path + '/');

            return (
              <button
                key={item.path}
                type="button"
                onClick={() => {
                  navigate(item.path);
                  if (onClose) onClose();
                }}
                className={`w-full flex items-start gap-3 px-3 py-2.5 rounded text-left transition-all group ${
                  isActive
                    ? 'bg-[#b15f2c]/08 text-[#0a0a0a] border border-[#b15f2c]/20 shadow-xs'
                    : 'text-[#3a3a3a] hover:text-[#0a0a0a] hover:bg-[#fafaf8] border border-transparent'
                }`}
              >
                <Icon
                  className={`w-4 h-4 mt-0.5 shrink-0 transition-colors ${
                    isActive ? 'text-[#b15f2c]' : 'text-[#8d8d8d] group-hover:text-[#0a0a0a]'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold tracking-wide uppercase font-mono">
                    {item.label}
                  </div>
                  <div className="text-[11px] text-[#8d8d8d] leading-tight mt-0.5 truncate font-sans">
                    {item.description}
                  </div>
                </div>
              </button>
            );
          })}
        </nav>

        {/* Workspace Quick Details */}
        <div className="p-3.5 border-t border-[#e6e5e2] bg-[#fafaf8] text-[11px] font-mono text-[#8d8d8d] space-y-1">
          <div className="flex justify-between">
            <span>STATION:</span>
            <span className="text-[#0a0a0a] font-bold">{user.principal_id}</span>
          </div>
          <div className="flex justify-between">
            <span>ROLE:</span>
            <span className="text-[#b15f2c] font-semibold">{user.role}</span>
          </div>
        </div>
      </aside>
    </>
  );
}
