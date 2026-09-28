import React, { useState, useEffect } from 'react';
import { Inbox, FileText, ArrowRight, RefreshCw } from 'lucide-react';
import { documentsApi } from '../../services/api';
import { useAuth } from '../../app/AuthContext';
import { useRouter } from '../../app/RouterContext';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function InboxView({ onSelectDirective }) {
  const { user } = useAuth();
  const { navigate } = useRouter();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadInbox = async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await documentsApi.list();
      setDocuments(docs || []);
    } catch (err) {
      setError(err.message || 'Failed to load assigned directives.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInbox();
  }, []);

  const handleSelect = (doc) => {
    if (onSelectDirective) {
      onSelectDirective(doc.document_id);
    } else {
      navigate('/recipient/decrypt');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Inbox className="w-5 h-5 text-[#b15f2c]" />
            Directive Inbox — Station {user?.principal_id}
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            AUTHORIZED INCOMING BROADCAST-ENCRYPTED FLEET DIRECTIVES
          </p>
        </div>
        <Button variant="secondary" onClick={loadInbox} loading={loading} size="sm" icon={RefreshCw}>
          Refresh Inbox
        </Button>
      </div>

      {error && <Alert type="error" title="Inbox Notice" message={error} onDismiss={() => setError(null)} />}

      <Card
        title="Incoming Assigned Directives"
        subtitle={`Total assigned packages: ${documents.length}`}
        icon={FileText}
        bodyClassName="p-0"
      >
        {documents.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={Inbox}
              title="No Directives Available"
              description="No protected directives are currently assigned to this station. When an authority broadcasts a directive to your station ID, it will appear here for step-up decryption."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#fafaf8] text-[#8d8d8d] font-mono border-b border-[#e6e5e2]">
                <tr>
                  <th className="px-4 py-3">DIRECTIVE ID</th>
                  <th className="px-4 py-3">CLASSIFICATION</th>
                  <th className="px-4 py-3">STATUS</th>
                  <th className="px-4 py-3">ORIGINAL SHA-256</th>
                  <th className="px-4 py-3">ASSIGNED</th>
                  <th className="px-4 py-3 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e6e5e2] font-mono">
                {documents.map((d) => (
                  <tr key={d.document_id} className="hover:bg-[#fafaf8] transition-colors">
                    <td className="px-4 py-3 font-semibold text-[#0a0a0a]">
                      <div>{d.document_id}</div>
                      <div className="text-[10px] text-[#8d8d8d] font-sans">{d.filename || 'Brief.pdf'}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[#b15f2c] font-bold font-mono">{d.classification}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge status={d.status} size="xs" />
                    </td>
                    <td className="px-4 py-3">
                      <HashDisplay hash={d.original_hash} length={6} />
                    </td>
                    <td className="px-4 py-3 text-[11px] text-[#8d8d8d]">
                      {new Date(d.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleSelect(d)}
                        icon={ArrowRight}
                      >
                        Open Terminal
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
