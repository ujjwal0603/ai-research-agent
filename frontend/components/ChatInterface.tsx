'use client';

import React, { useRef, useEffect, useState } from 'react';
import MessageBubble from './MessageBubble';
import { Message, SourceChunk } from '@/lib/api';

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (query: string) => void;
  activeDocument?: { filename: string; page_count: number } | null;
}

export default function ChatInterface({
  messages,
  isLoading,
  onSendMessage,
  activeDocument,
}: ChatInterfaceProps) {
  const [query, setQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }
  }, [query]);

  const handleSend = () => {
    const trimmed = query.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setQuery('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {activeDocument && (
        <div className="chat-header">
          <div className="chat-header-doc">
            <span className="doc-indicator" />
            <span className="doc-name">{activeDocument.filename}</span>
          </div>
          <div className="chat-header-meta">
            <span>{activeDocument.page_count} pages</span>
          </div>
        </div>
      )}

      {/* Chat messages area */}
      <div className="chat-area">
        <div className="chat-messages-wrapper">
          {messages.length === 0 && !isLoading ? (
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  <line x1="9" y1="9" x2="15" y2="9" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                </svg>
              </div>
              <h2>Start a conversation</h2>
              <p>
                Upload PDF documents and ask questions. The AI will analyze your
                documents and provide answers with source references.
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <MessageBubble key={index} message={msg} />
              ))}
              {isLoading && (
                <div className="message assistant">
                  <div className="message-avatar">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <div className="bubble">
                    <div className="loading-dots"><span /><span /><span /></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>

      {/* Input area */}
      <div className="input-area-container">
        <div className="input-area">
          <div className="input-area-inner">
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents…"
              rows={1}
              disabled={isLoading}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={!query.trim() || isLoading}
              title="Send message"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
        <div className="input-footer">
          <span className="footer-left">Press <kbd>↵</kbd> to send · <kbd>⇧</kbd><kbd>↵</kbd> for newline</span>
          <span className="footer-right">
            {activeDocument ? <span className="active-dot">● 1 active document</span> : 'No active document'}
          </span>
        </div>
      </div>
    </>
  );
}
