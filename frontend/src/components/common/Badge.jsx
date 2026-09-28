import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, XCircle, Info, Lock } from 'lucide-react';

const BADGE_STYLES = {
  VERIFIED: {
    bg: 'bg-[#2d6a4f]/10 border-[#2d6a4f]/30 text-[#1b4332]',
    icon: ShieldCheck,
  },
  SUCCESS: {
    bg: 'bg-[#2d6a4f]/10 border-[#2d6a4f]/30 text-[#1b4332]',
    icon: CheckCircle2,
  },
  ACTIVE: {
    bg: 'bg-[#2d6a4f]/10 border-[#2d6a4f]/30 text-[#1b4332]',
    icon: CheckCircle2,
  },
  CORRELATED: {
    bg: 'bg-[#b15f2c]/10 border-[#b15f2c]/30 text-[#97501f]',
    icon: AlertTriangle,
  },
  WARNING: {
    bg: 'bg-[#b15f2c]/10 border-[#b15f2c]/30 text-[#97501f]',
    icon: AlertTriangle,
  },
  UNVERIFIED: {
    bg: 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#8b3a2a]',
    icon: ShieldAlert,
  },
  NOT_ATTRIBUTABLE: {
    bg: 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#8b3a2a]',
    icon: ShieldAlert,
  },
  FAILED: {
    bg: 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#8b3a2a]',
    icon: XCircle,
  },
  DENIED: {
    bg: 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#8b3a2a]',
    icon: XCircle,
  },
  REVOKED: {
    bg: 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#8b3a2a]',
    icon: XCircle,
  },
  ENCRYPTED: {
    bg: 'bg-[#cf8047]/10 border-[#cf8047]/30 text-[#97501f]',
    icon: Lock,
  },
  REGISTERED: {
    bg: 'bg-[#b15f2c]/10 border-[#b15f2c]/25 text-[#97501f]',
    icon: Info,
  },
  DEMO: {
    bg: 'bg-[#7a5c88]/10 border-[#7a5c88]/30 text-[#543b60]',
    icon: Info,
  },
  PENDING: {
    bg: 'bg-[#b15f2c]/10 border-[#b15f2c]/30 text-[#97501f]',
    icon: AlertTriangle,
  },
  AUTHORITY: {
    bg: 'bg-[#b15f2c]/10 border-[#b15f2c]/30 text-[#97501f]',
    icon: Lock,
  },
  RECIPIENT: {
    bg: 'bg-[#cf8047]/10 border-[#cf8047]/30 text-[#97501f]',
    icon: Lock,
  },
  INVESTIGATOR: {
    bg: 'bg-[#0a0a0a]/08 border-[#0a0a0a]/20 text-[#0a0a0a]',
    icon: ShieldCheck,
  },
  AUDITOR: {
    bg: 'bg-[#2d6a4f]/10 border-[#2d6a4f]/30 text-[#1b4332]',
    icon: CheckCircle2,
  },
  DEFAULT: {
    bg: 'bg-[#f1f0ee] border-[#d8d6d2] text-[#3a3a3a]',
    icon: Info,
  },
};

export default function Badge({ status = 'DEFAULT', label, size = 'sm', className = '' }) {
  const normStatus = (status || 'DEFAULT').toUpperCase();
  const config = BADGE_STYLES[normStatus] || BADGE_STYLES.DEFAULT;
  const Icon = config.icon;
  const displayLabel = label || normStatus.replace(/_/g, ' ');

  const sizeClasses = size === 'xs'
    ? 'text-[10px] px-1.5 py-0.5 gap-1'
    : size === 'lg'
    ? 'text-sm px-3 py-1.5 gap-2'
    : 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span
      className={`inline-flex items-center font-medium font-mono uppercase tracking-wider border rounded ${config.bg} ${sizeClasses} ${className}`}
    >
      <Icon className={size === 'xs' ? 'w-3 h-3' : size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
      <span>{displayLabel}</span>
    </span>
  );
}
