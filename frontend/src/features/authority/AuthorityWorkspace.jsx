import React from 'react';
import { useRouter } from '../../app/RouterContext';
import DirectivesManager from './DirectivesManager';
import PersonnelManager from './PersonnelManager';
import TrustDesk from './TrustDesk';
import AuditTrailViewer from '../auditor/AuditTrailViewer';

export default function AuthorityWorkspace() {
  const { currentPath } = useRouter();

  if (currentPath.includes('/personnel')) {
    return <PersonnelManager />;
  }
  if (currentPath.includes('/trust')) {
    return <TrustDesk />;
  }
  if (currentPath.includes('/audit')) {
    return <AuditTrailViewer />;
  }

  return <DirectivesManager />;
}
