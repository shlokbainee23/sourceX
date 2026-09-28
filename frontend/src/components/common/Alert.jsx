import React from 'react';
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

const ALERT_CONFIG = {
  info: {
    bg: 'bg-[#cf8047]/10 border-[#cf8047]/30 text-[#4a2e18]',
    icon: Info,
    iconColor: 'text-[#b15f2c]',
  },
  success: {
    bg: 'bg-[#2d6a4f]/10 border-[#2d6a4f]/30 text-[#1b4332]',
    icon: CheckCircle2,
    iconColor: 'text-[#2d6a4f]',
  },
  warning: {
    bg: 'bg-[#b15f2c]/10 border-[#b15f2c]/30 text-[#5a2e12]',
    icon: AlertTriangle,
    iconColor: 'text-[#b15f2c]',
  },
  error: {
    bg: 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#541a10]',
    icon: AlertCircle,
    iconColor: 'text-[#8b3a2a]',
  },
};

export default function Alert({
  type = 'info',
  title,
  message,
  children,
  onDismiss,
  className = '',
}) {
  const config = ALERT_CONFIG[type] || ALERT_CONFIG.info;
  const Icon = config.icon;

  return (
    <div
      role="alert"
      className={`p-3.5 rounded-md border flex items-start gap-3 text-xs ${config.bg} ${className}`}
    >
      <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${config.iconColor}`} />
      <div className="flex-1 space-y-0.5 min-w-0">
        {title && <h4 className="font-semibold text-[#0a0a0a] uppercase tracking-wide font-mono text-[11px]">{title}</h4>}
        {message && <p className="text-[#3a3a3a] leading-relaxed">{message}</p>}
        {children}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-[#8d8d8d] hover:text-[#0a0a0a] p-0.5 rounded shrink-0 transition-colors"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
