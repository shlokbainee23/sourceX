import React, { useState } from 'react';
import { useRouter } from '../../app/RouterContext';
import InboxView from './InboxView';
import DecryptionTerminal from './DecryptionTerminal';
import StationKeyStatus from './StationKeyStatus';

export default function RecipientWorkspace() {
  const { currentPath, navigate } = useRouter();
  const [selectedDocId, setSelectedDocId] = useState('');

  const handleSelectFromInbox = (docId) => {
    setSelectedDocId(docId);
    navigate('/recipient/decrypt');
  };

  if (currentPath.includes('/keys')) {
    return <StationKeyStatus />;
  }
  if (currentPath.includes('/decrypt')) {
    return <DecryptionTerminal preselectedDocId={selectedDocId} />;
  }

  return <InboxView onSelectDirective={handleSelectFromInbox} />;
}
