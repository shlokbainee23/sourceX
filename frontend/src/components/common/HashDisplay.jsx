import React, { useState } from 'react';
import { Copy, Check, Eye, EyeOff } from 'lucide-react';

export default function HashDisplay({
  hash,
  label,
  truncate = true,
  length = 8,
  mono = true,
  showCopy = true,
  className = '',
}) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(!truncate);

  if (!hash) {
    return <span className="text-[#8d8d8d] italic text-xs font-mono">None</span>;
  }

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const displayHash =
    !expanded && hash.length > length * 2 + 3
      ? `${hash.slice(0, length)}...${hash.slice(-length)}`
      : hash;

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      {label && <span className="text-xs text-[#8d8d8d] select-none font-mono">{label}:</span>}
      <code
        title={hash}
        className={`text-xs px-2 py-0.5 rounded bg-[#f1f0ee] border border-[#e6e5e2] text-[#0a0a0a] ${
          mono ? 'font-mono' : ''
        } select-all break-all`}
      >
        {displayHash}
      </code>

      {truncate && hash.length > length * 2 + 3 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          title={expanded ? 'Collapse hash' : 'Show full hash'}
          className="p-1 text-[#8d8d8d] hover:text-[#0a0a0a] transition-colors rounded hover:bg-[#e6e5e2]"
          aria-label={expanded ? 'Collapse hash' : 'Expand full hash'}
        >
          {expanded ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
        </button>
      )}

      {showCopy && (
        <button
          type="button"
          onClick={handleCopy}
          title="Copy full cryptographic value"
          className="p-1 text-[#8d8d8d] hover:text-[#0a0a0a] transition-colors rounded hover:bg-[#e6e5e2]"
          aria-label="Copy hash"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-[#2d6a4f]" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
      )}
    </div>
  );
}
