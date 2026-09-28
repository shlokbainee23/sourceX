import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  type = 'button',
  icon: Icon,
  className = '',
  ...props
}) {
  const baseClasses =
    'inline-flex items-center justify-center font-medium rounded transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#fafaf8] focus:ring-[#b15f2c] disabled:opacity-40 disabled:cursor-not-allowed select-none cursor-pointer';

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5 font-mono tracking-wider uppercase',
    md: 'text-xs md:text-sm px-4 py-2 gap-2 font-mono tracking-wider uppercase',
    lg: 'text-sm md:text-base px-5 py-2.5 gap-2.5 font-mono tracking-wider uppercase',
  }[size] || 'text-xs md:text-sm px-4 py-2 gap-2 font-mono tracking-wider uppercase';

  const variantClasses = {
    primary:
      'bg-[#0a0a0a] hover:bg-[#b15f2c] active:bg-[#97501f] text-white shadow-sm border border-[#0a0a0a] hover:border-[#b15f2c]',
    secondary:
      'bg-white hover:bg-[#f1f0ee] active:bg-[#e3e2df] text-[#111111] border border-[#d8d6d2] shadow-sm hover:border-[#0a0a0a]',
    danger:
      'bg-[#8b3a2a] hover:bg-[#a34433] active:bg-[#6e2b1f] text-white border border-[#8b3a2a] shadow-sm',
    warning:
      'bg-[#8a5a1a] hover:bg-[#a66f24] text-white font-semibold border border-[#8a5a1a]',
    ghost:
      'bg-transparent hover:bg-[#f1f0ee] active:bg-[#e3e2df] text-[#3a3a3a] hover:text-[#0a0a0a]',
    outline:
      'bg-transparent hover:bg-[#b15f2c]/10 text-[#b15f2c] border border-[#b15f2c]',
  }[variant] || 'bg-[#0a0a0a] hover:bg-[#b15f2c] text-white';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-current" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {Icon && <Icon className="w-4 h-4 text-current" />}
          <span>{children}</span>
        </>
      )}
    </button>
  );
}
