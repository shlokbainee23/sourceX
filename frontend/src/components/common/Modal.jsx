import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

export default function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'max-w-lg',
  closeOnBackdrop = true,
}) {
  const modalRef = useRef(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0a0a0a]/50 backdrop-blur-xs animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="fixed inset-0"
        onClick={closeOnBackdrop ? onClose : undefined}
      />
      <div
        ref={modalRef}
        className={`relative w-full ${maxWidth} bg-white border border-[#d8d6d2] rounded-lg shadow-2xl overflow-hidden z-10 text-[#111111]`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#e6e5e2] bg-[#fafaf8]">
          <div>
            <h3 id="modal-title" className="text-sm font-bold text-[#0a0a0a] tracking-wider uppercase font-mono">
              {title}
            </h3>
            {subtitle && <p className="text-xs text-[#8d8d8d] mt-0.5">{subtitle}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-[#8d8d8d] hover:text-[#0a0a0a] hover:bg-[#f1f0ee] transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 max-h-[80vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
