import React from 'react';
import { Inbox, FileSearch } from 'lucide-react';
import Button from './Button';

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No Records Found',
  description = 'No active entries are registered under this operational parameter.',
  actionLabel,
  onAction,
  className = '',
}) {
  return (
    <div className={`p-10 border border-dashed border-[#d8d6d2] rounded-lg bg-[#fafaf8] text-center max-w-lg mx-auto ${className}`}>
      <div className="w-10 h-10 rounded-full bg-[#f1f0ee] border border-[#e6e5e2] text-[#8d8d8d] flex items-center justify-center mx-auto mb-3">
        <Icon className="w-5 h-5 text-[#b15f2c]" />
      </div>
      <h3 className="text-xs font-bold uppercase tracking-wider text-[#0a0a0a] font-mono">
        {title}
      </h3>
      <p className="text-xs text-[#8d8d8d] mt-1.5 max-w-sm mx-auto leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
