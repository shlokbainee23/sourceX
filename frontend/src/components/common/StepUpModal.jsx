import React, { useState, useEffect } from 'react';
import { KeyRound, Eye, EyeOff, ShieldCheck, AlertCircle } from 'lucide-react';
import Modal from './Modal';
import Button from './Button';

export default function StepUpModal({
  isOpen,
  onClose,
  onSubmit,
  principalId,
  documentId,
  title = 'Step-Up Cryptographic Authentication',
  loading = false,
}) {
  const [passphrase, setPassphrase] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setPassphrase('');
      setError('');
      setShowPassword(false);
    }
  }, [isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!passphrase.trim()) {
      setError('Passphrase is required to unlock your recipient keystore.');
      return;
    }
    onSubmit(passphrase);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={`Station Identity: ${principalId} · Document: ${documentId}`}
      maxWidth="max-w-md"
      closeOnBackdrop={!loading}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-3 bg-[#b15f2c]/10 border border-[#b15f2c]/25 rounded-md text-xs text-[#5a2e12] flex items-start gap-2.5">
          <KeyRound className="w-4 h-4 text-[#b15f2c] mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold text-[#0a0a0a] uppercase tracking-wide font-mono text-[11px]">Step-Up Key Decryption Required</p>
            <p className="mt-1 text-[#3a3a3a] leading-relaxed">
              Your keystore passphrase is required to unwrap the AES-256-GCM Content Encryption Key (CEK)
              via ML-KEM-768 and generate your station's ML-DSA-44 provenance signature. Private keys are
              scrubbed from memory immediately after this request.
            </p>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
            Keystore Passphrase
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={passphrase}
              onChange={(e) => {
                setPassphrase(e.target.value);
                if (error) setError('');
              }}
              placeholder="Enter station passphrase..."
              disabled={loading}
              autoFocus
              className="w-full px-3.5 py-2.5 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-sm focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c] placeholder:text-[#8d8d8d] pr-10 font-mono"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8d8d8d] hover:text-[#0a0a0a] p-1 transition-colors"
              aria-label={showPassword ? 'Hide passphrase' : 'Show passphrase'}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {error && (
            <div className="mt-1.5 flex items-center gap-1.5 text-xs text-[#8b3a2a]">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#e6e5e2]">
          <Button variant="secondary" onClick={onClose} disabled={loading} size="sm">
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={loading}
            icon={ShieldCheck}
            size="sm"
          >
            Unlock & Decrypt
          </Button>
        </div>
      </form>
    </Modal>
  );
}
