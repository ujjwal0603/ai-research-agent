'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
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
    const userMessage: Message = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMessage]);
    setIsChatLoading(true);
    setError(null);

    let currentAnswer = '';
    let currentSources: SourceChunk[] = [];
    
    // Add empty assistant message that we will populate
    const assistantMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: 'assistant', content: '', sources: [] }]);

    await streamChat(query, {
      onToken: (token) => {
        setIsChatLoading(false); // We have started receiving tokens
        currentAnswer += token;
        setMessages((prev) => {
          const newMsgs = [...prev];
          if (newMsgs[assistantMsgIndex]) {
            newMsgs[assistantMsgIndex] = { ...newMsgs[assistantMsgIndex], content: currentAnswer };
          }
          return newMsgs;
        });
      },
      onSources: (sources) => {
        currentSources = sources;
        setMessages((prev) => {
          const newMsgs = [...prev];
          if (newMsgs[assistantMsgIndex]) {
            newMsgs[assistantMsgIndex] = { ...newMsgs[assistantMsgIndex], sources: currentSources };
          }
          return newMsgs;
        });
      },
      onDone: (fullAnswer) => {
        setIsChatLoading(false);
        setMessages((prev) => {
          const newMsgs = [...prev];
          if (newMsgs[assistantMsgIndex]) {
            newMsgs[assistantMsgIndex] = { role: 'assistant', content: fullAnswer, sources: currentSources };
          }
          return newMsgs;
        });
      },
      onError: (errorMsg) => {
        setIsChatLoading(false);
        setError(errorMsg);
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
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <h1>AI Research Agent</h1>
              <p>v2 architecture</p>
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
             <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
               Welcome, <strong style={{color: 'white'}}>{user.full_name}</strong>
             </div>
             <button onClick={logout} className="auth-button" style={{ padding: '6px 12px', marginTop: '0', fontSize: '12px' }}>
               Sign out
             </button>
          </div>

          <FileUpload onUpload={handleUpload} isUploading={isUploading} />

          <div className="sidebar-section-title">
            Documents ({documents.length})
            {activeDocumentId && (
              <span style={{ fontSize: '11px', fontWeight: 'normal', color: 'var(--primary-color)', marginLeft: '8px' }}>
                (1 Active)
              </span>
            )}
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
                  style={{ cursor: 'pointer' }}
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
                      <span>{doc.page_count} pages</span>
                      <span className="separator" />
                      <span>{formatFileSize(doc.file_size_bytes)}</span>
                      <span className="separator" />
                      <span>{formatDate(doc.upload_time)}</span>
                    </div>
                  </div>
                  <button
                    className="delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteDocument(doc.document_id);
                    }}
                    title="Delete document"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      <line x1="10" y1="11" x2="10" y2="17" />
                      <line x1="14" y1="11" x2="14" y2="17" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <ChatInterface
          messages={messages}
          isLoading={isChatLoading}
          onSendMessage={handleSendMessage}
        />
      </main>
    </div>
  );
}
