import React, { useState, useEffect } from 'react';
import { Users, UserPlus } from 'lucide-react';
import { recipientsApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Modal from '../../components/common/Modal';
import Alert from '../../components/common/Alert';

export default function PersonnelManager() {
  const [recipients, setRecipients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // New Officer Enrollment Modal
  const [enrolModalOpen, setEnrolModalOpen] = useState(false);
  const [newId, setNewId] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole] = useState('RECIPIENT');
  const [enrolling, setEnrolling] = useState(false);
  const [enrolResult, setEnrolResult] = useState(null);

  const loadRecipients = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await recipientsApi.list();
      setRecipients(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load recipients list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecipients();
  }, []);

  const handleEnrol = async (e) => {
    e.preventDefault();
    if (!newId || !newName) return;
    setEnrolling(true);
    setError(null);
    try {
      const res = await recipientsApi.create(newId, newName, newRole);
      setEnrolResult(res);
      await loadRecipients();
    } catch (err) {
      setError(err.message || 'Failed to create recipient identity.');
    } finally {
      setEnrolling(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Users className="w-5 h-5 text-[#b15f2c]" />
            Personnel Registry & Public Key Directory
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            AUTHORIZED FLEET STATIONS AND POST-QUANTUM PUBLIC KEY ATTESTATIONS
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={loadRecipients} loading={loading} size="sm">
            Refresh Directory
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              setEnrolResult(null);
              setEnrolModalOpen(true);
            }}
            icon={UserPlus}
            size="sm"
          >
            Enrol Station
          </Button>
        </div>
      </div>

      {error && <Alert type="error" title="Error" message={error} onDismiss={() => setError(null)} />}

      <Card
        title="Active Officer Directory"
        subtitle={`Total registered stations: ${recipients.length}`}
        icon={Users}
        bodyClassName="p-0"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#fafaf8] text-[#8d8d8d] font-mono border-b border-[#e6e5e2]">
              <tr>
                <th className="px-4 py-3">STATION ID</th>
                <th className="px-4 py-3">OFFICER NAME</th>
                <th className="px-4 py-3">STATUS</th>
                <th className="px-4 py-3">ML-KEM-768 PUBLIC KEY</th>
                <th className="px-4 py-3">ML-DSA-44 PUBLIC KEY</th>
                <th className="px-4 py-3">REGISTERED</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e6e5e2] font-mono">
              {recipients.map((r) => (
                <tr key={r.recipient_id} className="hover:bg-[#fafaf8] transition-colors">
                  <td className="px-4 py-3 font-semibold text-[#0a0a0a]">
                    <div>{r.recipient_id}</div>
                    <div className="text-[10px] text-[#8d8d8d]">{r.role}</div>
                  </td>
                  <td className="px-4 py-3 text-[#111111] font-sans">{r.name}</td>
                  <td className="px-4 py-3">
                    <Badge status={r.status} size="xs" />
                  </td>
                  <td className="px-4 py-3">
                    <HashDisplay hash={r.mlkem_public_key} length={6} />
                  </td>
                  <td className="px-4 py-3">
                    <HashDisplay hash={r.mldsa_public_key} length={6} />
                  </td>
                  <td className="px-4 py-3 text-[11px] text-[#8d8d8d]">
                    {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'Baseline'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Enrol Station Modal */}
      <Modal
        isOpen={enrolModalOpen}
        onClose={() => setEnrolModalOpen(false)}
        title="Enrol Fleet Station Identity"
        subtitle="Generates one-time enrollment code for decentralized key generation"
      >
        {enrolResult ? (
          <div className="space-y-4">
            <Alert
              type="success"
              title="Station Identity Created"
              message={`Identity ${enrolResult.principal_id || newId} created awaiting enrollment.`}
            />

            <div className="p-4 bg-[#fafaf8] border border-[#e6e5e2] rounded font-mono text-xs space-y-2">
              <div className="text-[#8d8d8d] font-semibold text-[11px]">ONE-TIME ENROLLMENT CODE:</div>
              <div className="p-2.5 bg-white border border-[#b15f2c]/30 rounded text-[#b15f2c] text-sm font-bold select-all break-all shadow-xs">
                {enrolResult.enrollment_code || 'CODE-CONFIRMED-ATTESTATION'}
              </div>
              <p className="text-[11px] text-[#8d8d8d] pt-2 font-sans">
                {enrolResult.next_step ||
                  'Deliver this enrollment code to the station officer out of band. After enrollment, confirm fingerprint and attest.'}
              </p>
            </div>

            <Button
              variant="primary"
              onClick={() => {
                setEnrolModalOpen(false);
                setEnrolResult(null);
              }}
              className="w-full"
            >
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleEnrol} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                Station Identifier
              </label>
              <input
                type="text"
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                required
                placeholder="R004 / OFFICER_SIG"
                className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                Officer / Station Name
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                placeholder="Lieutenant Commander Echo"
                className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c]"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#e6e5e2]">
              <Button variant="secondary" onClick={() => setEnrolModalOpen(false)} disabled={enrolling} size="sm">
                Cancel
              </Button>
              <Button type="submit" variant="primary" loading={enrolling} size="sm">
                Create Identity
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
