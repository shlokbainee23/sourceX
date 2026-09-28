import React from 'react';
import { useRouter } from '../../app/RouterContext';
import IntakeVerification from './IntakeVerification';
import VisualInvarianceTool from './VisualInvarianceTool';
import DossierArchive from './DossierArchive';

export default function InvestigatorWorkspace() {
  const { currentPath } = useRouter();

  if (currentPath.includes('/invariance')) {
    return <VisualInvarianceTool />;
  }
  if (currentPath.includes('/dossiers')) {
    return <DossierArchive />;
  }

  return <IntakeVerification />;
}
