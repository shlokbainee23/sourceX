import React from 'react';
import { RouterProvider, useRouter } from './app/RouterContext';
import { AuthProvider, useAuth } from './app/AuthContext';
import AppShell from './components/layout/AppShell';
import LoginPage from './features/auth/LoginPage';
import AuthorityWorkspace from './features/authority/AuthorityWorkspace';
import RecipientWorkspace from './features/recipient/RecipientWorkspace';
import InvestigatorWorkspace from './features/investigation/InvestigatorWorkspace';
import AuditorWorkspace from './features/auditor/AuditorWorkspace';
import SourceXLanding from './landing/SourceXLanding';
import { Anchor, ShieldAlert } from 'lucide-react';

function AppContent() {
  const { user, isAuthenticated, isLoading, getDefaultRouteForRole } = useAuth();
  const { currentPath, navigate } = useRouter();

  React.useEffect(() => {
    // If authenticated user visits /login, redirect to their role home
    if (isAuthenticated && currentPath === '/login') {
      navigate(getDefaultRouteForRole(user?.role));
    }
  }, [isAuthenticated, currentPath, user, navigate, getDefaultRouteForRole]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#fafaf8] text-[#111111] flex flex-col items-center justify-center p-4 font-mono select-none">
        <div className="w-12 h-12 rounded bg-[#fafaf8] border border-[#d8d6d2] flex items-center justify-center text-[#b15f2c] mb-4 animate-pulse">
          <Anchor className="w-6 h-6" />
        </div>
        <div className="text-sm font-bold tracking-wider uppercase text-[#0a0a0a]">
          WESEE / MoD Offline Forensic Workstation
        </div>
        <div className="text-xs text-[#8d8d8d] mt-1 font-mono">
          Validating local cryptographic keystore session...
        </div>
      </div>
    );
  }

  // Public Landing Experience
  if (currentPath === '/' || currentPath === '/landing') {
    return <SourceXLanding />;
  }

  if (!isAuthenticated || currentPath === '/login') {
    return <LoginPage />;
  }

  // Render role-specific workspace inside authenticated AppShell
  const renderWorkspace = () => {
    switch (user.role) {
      case 'AUTHORITY':
        return <AuthorityWorkspace />;
      case 'RECIPIENT':
        return <RecipientWorkspace />;
      case 'INVESTIGATOR':
        return <InvestigatorWorkspace />;
      case 'AUDITOR':
        return <AuditorWorkspace />;
      default:
        return (
          <div className="p-8 text-center space-y-2">
            <ShieldAlert className="w-8 h-8 text-[#8b3a2a] mx-auto" />
            <h3 className="text-sm font-semibold text-[#0a0a0a] uppercase">
              Unrecognized Role: {user.role}
            </h3>
            <p className="text-xs text-[#8d8d8d]">
              Your station identity does not map to a recognized operational workspace.
            </p>
          </div>
        );
    }
  };

  return <AppShell>{renderWorkspace()}</AppShell>;
}

export default function App() {
  return (
    <RouterProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </RouterProvider>
  );
}
