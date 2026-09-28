import React from 'react';
import { useRouter } from '../../app/RouterContext';
import LedgerExplorer from './LedgerExplorer';
import AuditTrailViewer from './AuditTrailViewer';
import TamperSandbox from './TamperSandbox';

export default function AuditorWorkspace() {
  const { currentPath } = useRouter();

  if (currentPath.includes('/audit')) {
    return <AuditTrailViewer />;
  }
  if (currentPath.includes('/tamper')) {
    return <TamperSandbox />;
  }

  return <LedgerExplorer />;
}
