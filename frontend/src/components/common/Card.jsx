import React from 'react';

export default function Card({
  title,
  subtitle,
  icon: Icon,
  badge,
  actions,
  children,
  footer,
  className = '',
  bodyClassName = '',
}) {
  return (
    <div
      className={`bg-white border border-[#e6e5e2] rounded-lg shadow-xs overflow-hidden ${className}`}
    >
      {(title || subtitle || actions || badge) && (
        <div className="px-5 py-3.5 border-b border-[#e6e5e2] bg-[#fafaf8] flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 min-w-0">
            {Icon && <Icon className="w-4 h-4 text-[#b15f2c] shrink-0" />}
            <div className="min-w-0">
              {title && (
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-semibold tracking-wider text-[#0a0a0a] uppercase truncate font-mono">
                    {title}
                  </h3>
                  {badge && <div>{badge}</div>}
                </div>
              )}
              {subtitle && (
                <p className="text-xs text-[#8d8d8d] truncate mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
      <div className={`p-5 text-[#111111] ${bodyClassName}`}>{children}</div>
      {footer && (
        <div className="px-5 py-3 border-t border-[#e6e5e2] bg-[#fafaf8] text-xs text-[#8d8d8d] flex items-center justify-between">
          {footer}
        </div>
      )}
    </div>
  );
}
