'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useAuth } from '@/lib/AuthContext';
import FileUpload from '@/components/FileUpload';
import ChatInterface from '@/components/ChatInterface';
import {
  uploadPDF,
  getDocuments,
  deleteDocument,
  streamChat,
  type Message,
  type DocumentInfo,
  type SourceChunk,
} from '@/lib/api';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(isoString: string): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function Home() {
  const { user, isLoading: authLoading, logout } = useAuth();
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);

  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const loadDocuments = useCallback(async () => {
    if (!user) return;
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, [user]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadDocuments();
    }
  }, [user, loadDocuments]);

  // Clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  if (authLoading || !user) {
    return (
      <div className="auth-container">
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    );
  }

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      await uploadPDF(file);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (query: string) => {
    const userMsg: Message = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    const assistantMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    let currentAnswer = '';
    let currentSources: SourceChunk[] = [];

    await streamChat({
      query,
      onToken: (token) => {
        setIsChatLoading(false);
        currentAnswer += token;
        setMessages((prev) => {
          const newMsgs = [...prev];
          if (newMsgs[assistantMsgIndex]) {
            newMsgs[assistantMsgIndex] = { 
              ...newMsgs[assistantMsgIndex], 
              content: currentAnswer 
            };
          }
          return newMsgs;
        });
      },
      onSources: (sources) => {
        currentSources = sources;
        setMessages((prev) => {
          const newMsgs = [...prev];
          if (newMsgs[assistantMsgIndex]) {
            newMsgs[assistantMsgIndex] = { 
              ...newMsgs[assistantMsgIndex], 
              sources: currentSources 
            };
          }
          return newMsgs;
        });
      },
      onDone: () => {
        setIsChatLoading(false);
      },
      onError: (err) => {
        setIsChatLoading(false);
        setError(err);
        if (currentAnswer === '') {
           setMessages((prev) => {
             const newMsgs = [...prev];
             if (newMsgs[assistantMsgIndex]) {
               newMsgs[assistantMsgIndex] = { 
                 role: 'assistant', 
                 content: 'Sorry, I encountered an error processing your request.' 
               };
             }
             return newMsgs;
           });
        }
      }
    }, activeDocumentId ? [activeDocumentId] : undefined);
  };

  const handleDeleteDocument = async (documentId: string) => {
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
      if (activeDocumentId === documentId) {
        setActiveDocumentId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
  };

  return (
    <div className="app-container">
      {error && (
        <div className="error-toast">
          {error}
          <button className="error-toast-close" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="4" />
                <path d="M8 12h8" />
                <path d="M12 8v8" />
              </svg>
            </div>
            <div>
              <h1>Research agent</h1>
              <p>v2 · arc</p>
            </div>
          </div>
        </div>

        <div className="sidebar-user-card">
          <div className="user-avatar">{getInitials(user.full_name)}</div>
          <div className="user-details">
            <span className="user-name">{user.full_name}</span>
          </div>
          <button onClick={logout} className="sign-out-btn">Sign out</button>
          {mounted && (
            <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Toggle theme">
              {theme === 'dark' ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
              )}
            </button>
          )}
        </div>

        <div className="sidebar-section">
          <FileUpload onUpload={handleUpload} isUploading={isUploading} />
        </div>

        <div className="sidebar-section" style={{ flex: 1, overflowY: 'auto' }}>
          <div className="sidebar-section-title">
            Documents <span className="doc-count">{documents.length}</span>
          </div>

          {documents.length === 0 ? (
            <div className="no-documents">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <p>No documents uploaded yet.<br />Upload a PDF to get started.</p>
            </div>
          ) : (
            <div className="document-list">
              {documents.map((doc) => (
                <div 
                  key={doc.document_id} 
                  className={`document-card ${activeDocumentId === doc.document_id ? 'active' : ''}`}
                  onClick={() => setActiveDocumentId(activeDocumentId === doc.document_id ? null : doc.document_id)}
                >
                  <div className="document-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                    </svg>
                  </div>
                  <div className="document-info">
                    <div className="document-name" title={doc.filename}>
                      {doc.filename}
                    </div>
                    <div className="document-meta">
                      <span>{doc.page_count} pg</span>
                      <span className="separator">·</span>
                      <span>{formatFileSize(doc.file_size_bytes)}</span>
                      <span className="separator">·</span>
                      <span>{formatDate(doc.upload_time)}</span>
                    </div>
                  </div>
                  {activeDocumentId === doc.document_id && (
                    <div className="active-badge">active</div>
                  )}
                  <button
                    className="delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteDocument(doc.document_id);
                    }}
                    title="Delete document"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="1" />
                      <circle cx="19" cy="12" r="1" />
                      <circle cx="5" cy="12" r="1" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <button className="new-conversation-btn" onClick={() => setMessages([])}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            New conversation
          </button>
        </div>
      </aside>

      <main className="main-content">
        <ChatInterface
          messages={messages}
          isLoading={isChatLoading}
          onSendMessage={handleSendMessage}
          activeDocument={documents.find(d => d.document_id === activeDocumentId) || null}
        />
      </main>
    </div>
  );
}
