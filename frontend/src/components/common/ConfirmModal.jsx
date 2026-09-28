import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';
import Modal from './Modal';
import Button from './Button';

export default function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Operation',
  message,
  consequences,
  reversible = false,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
  loading = false,
}) {
  const isDanger = variant === 'danger';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      maxWidth="max-w-md"
      closeOnBackdrop={!loading}
    >
      <div className="space-y-4">
        <div
          className={`p-3.5 rounded-md border flex items-start gap-3 ${
            isDanger
              ? 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#541a10]'
              : 'bg-[#b15f2c]/10 border-[#b15f2c]/30 text-[#5a2e12]'
          }`}
        >
          {isDanger ? (
            <AlertTriangle className="w-5 h-5 text-[#8b3a2a] shrink-0 mt-0.5" />
          ) : (
            <Info className="w-5 h-5 text-[#b15f2c] shrink-0 mt-0.5" />
          )}
          <div className="text-xs space-y-1">
            <p className="font-semibold text-[#0a0a0a]">{message}</p>
            {consequences && <p className="text-[#3a3a3a]">{consequences}</p>}
            <p className="font-mono text-[11px] pt-1">
              STATUS:{' '}
              <span className={reversible ? 'text-[#97501f]' : 'text-[#8b3a2a] font-bold'}>
                {reversible ? 'REVERSIBLE OPERATION' : 'IRREVERSIBLE · CANNOT BE UNDONE'}
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#e6e5e2]">
          <Button variant="secondary" onClick={onClose} disabled={loading} size="sm">
            {cancelText}
          </Button>
          <Button
            variant={variant}
            onClick={onConfirm}
            loading={loading}
            size="sm"
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
