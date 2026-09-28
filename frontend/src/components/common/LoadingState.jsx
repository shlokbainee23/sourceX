import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingState({
  message = 'Loading cryptographic state...',
  subtext = 'Querying local verified data store',
  className = '',
}) {
  return (
    <div className={`p-12 text-center flex flex-col items-center justify-center space-y-3 ${className}`}>
      <div className="w-9 h-9 rounded-full bg-[#f1f0ee] border border-[#e6e5e2] flex items-center justify-center text-[#b15f2c]">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-[#0a0a0a] font-mono">
          {message}
        </h4>
        {subtext && (
          <p className="text-[11px] text-[#8d8d8d] font-mono">{subtext}</p>
        )}
      </div>
    </div>
  );
}
