import React from 'react';
import { AlertOctagon, RotateCcw, Home } from 'lucide-react';
import Button from './Button';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Workstation Runtime Exception Caught:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    sessionStorage.clear();
    window.location.href = '/#/login';
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#fafaf8] text-[#111111] flex items-center justify-center p-4 font-mono select-none">
          <div className="max-w-xl w-full bg-white border border-[#8b3a2a]/40 rounded-xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center gap-3 border-b border-[#e6e5e2] pb-4">
              <div className="w-10 h-10 rounded-lg bg-[#8b3a2a]/10 border border-[#8b3a2a]/30 flex items-center justify-center text-[#8b3a2a] shrink-0">
                <AlertOctagon className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-sm font-bold uppercase tracking-wider text-[#0a0a0a]">
                  Station Anomaly / Execution Interrupted
                </h1>
                <p className="text-xs text-[#8d8d8d] font-sans">
                  A client-side runtime exception was intercepted by the forensic shield.
                </p>
              </div>
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded-lg text-xs space-y-2">
              <div className="text-[#8b3a2a] font-bold truncate">
                {this.state.error?.toString() || 'Unknown Runtime Error'}
              </div>
              {this.state.errorInfo?.componentStack && (
                <pre className="text-[11px] text-[#8d8d8d] overflow-x-auto max-h-36 scrollbar-thin">
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                variant="secondary"
                size="sm"
                icon={RotateCcw}
                onClick={this.handleReload}
              >
                Reload Workstation
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={Home}
                onClick={this.handleReset}
              >
                Reset Session to Login
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
