import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, RefreshCw, Eye, Search } from 'lucide-react';
import { ledgerApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Modal from '../../components/common/Modal';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function AuditTrailViewer() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [outcomeFilter, setOutcomeFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Event Modal
  const [selectedEvent, setSelectedEvent] = useState(null);

  const loadAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ledgerApi.getAuditTrail(150);
      setEvents(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load system audit trail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filteredEvents = events.filter((ev) => {
    if (outcomeFilter !== 'ALL' && ev.outcome !== outcomeFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchEvent = ev.event?.toLowerCase().includes(q);
      const matchPrincipal = ev.principal_id?.toLowerCase().includes(q);
      if (!matchEvent && !matchPrincipal) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <FileSpreadsheet className="w-5 h-5 text-[#b15f2c]" />
            System Audit Trail
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            APPEND-ONLY SERVER AUDIT LOG · CERT-IN COMPLIANT OPERATIONAL LOGGING
          </p>
        </div>
        <Button variant="secondary" onClick={loadAudit} loading={loading} size="sm" icon={RefreshCw}>
          Refresh Audit Log
        </Button>
      </div>

      {error && <Alert type="error" title="Audit Notice" message={error} onDismiss={() => setError(null)} />}

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 bg-white p-3 rounded-lg border border-[#e6e5e2] shadow-xs">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-[#8d8d8d] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by event type or principal ID..."
            className="w-full pl-9 pr-3 py-1.5 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#8d8d8d] font-mono font-semibold">OUTCOME:</span>
          <select
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(e.target.value)}
            className="px-3 py-1.5 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
          >
            <option value="ALL">ALL EVENTS</option>
            <option value="SUCCESS">SUCCESS</option>
            <option value="DENIED">DENIED</option>
            <option value="FAILED">FAILED</option>
            <option value="DEMO">DEMO</option>
          </select>
        </div>
      </div>

      {/* Audit Events Table */}
      <Card
        title="Recorded Operational Events"
        subtitle={`Displaying ${filteredEvents.length} of ${events.length} recorded events`}
        icon={FileSpreadsheet}
        bodyClassName="p-0"
      >
        {filteredEvents.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={FileSpreadsheet}
              title="No Audit Events Found"
              description="No audit records match the current filter or search criteria."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#fafaf8] text-[#8d8d8d] border-b border-[#e6e5e2]">
                <tr>
                  <th className="px-4 py-3">TIMESTAMP</th>
                  <th className="px-4 py-3">EVENT</th>
                  <th className="px-4 py-3">PRINCIPAL</th>
                  <th className="px-4 py-3">OUTCOME</th>
                  <th className="px-4 py-3">DETAILS SUMMARY</th>
                  <th className="px-4 py-3 text-right">INSPECT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e6e5e2]">
                {filteredEvents.map((ev, idx) => (
                  <tr key={idx} className="hover:bg-[#fafaf8] transition-colors">
                    <td className="px-4 py-3 text-[#8d8d8d] text-[11px] whitespace-nowrap">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 font-semibold text-[#0a0a0a]">
                      {ev.event}
                    </td>
                    <td className="px-4 py-3 text-[#b15f2c] font-semibold">
                      {ev.principal_id || 'ANONYMOUS'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge status={ev.outcome} size="xs" />
                    </td>
                    <td className="px-4 py-3 text-[#8d8d8d] text-[11px] truncate max-w-xs font-sans">
                      {typeof ev.details === 'string'
                        ? ev.details
                        : JSON.stringify(ev.details)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setSelectedEvent(ev)}
                        icon={Eye}
                      >
                        Inspect
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Audit Event Modal */}
      <Modal
        isOpen={!!selectedEvent}
        onClose={() => setSelectedEvent(null)}
        title={`Audit Event: ${selectedEvent?.event}`}
        subtitle={`Timestamp: ${selectedEvent?.timestamp}`}
        maxWidth="max-w-xl"
      >
        {selectedEvent && (
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">ACTING PRINCIPAL:</span>
                <div className="text-[#0a0a0a] font-bold">
                  {selectedEvent.principal_id || 'SYSTEM / ANONYMOUS'}
                </div>
              </div>
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">EVENT OUTCOME:</span>
                <div>
                  <Badge status={selectedEvent.outcome} size="xs" />
                </div>
              </div>
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-2">
              <span className="text-[#0a0a0a] text-[10px] uppercase font-bold">
                AUDIT METADATA & TELEMETRY:
              </span>
              <pre className="p-3 bg-white border border-[#e6e5e2] rounded overflow-x-auto text-[11px] text-[#0a0a0a] max-h-60 overflow-y-auto font-mono">
                {typeof selectedEvent.details === 'string'
                  ? selectedEvent.details
                  : JSON.stringify(selectedEvent.details, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
