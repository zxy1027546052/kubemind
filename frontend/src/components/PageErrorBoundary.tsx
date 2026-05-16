import { ReactNode } from 'react';
import ErrorBoundary from './ErrorBoundary';

interface Props {
  children: ReactNode;
  title?: string;
}

export default function PageErrorBoundary({ children, title }: Props) {
  return (
    <ErrorBoundary
      fallback={
        <div style={{
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 400,
          gap: 16,
        }}>
          <span style={{ fontSize: 32 }}>⚠️</span>
          <h3>{title || 'Page Error'}</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            This section encountered an error. Try refreshing.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 20px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              borderRadius: 4,
              cursor: 'pointer',
              fontFamily: 'var(--font-display)',
              fontSize: '0.8125rem',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Reload
          </button>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
