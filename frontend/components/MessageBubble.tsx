'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SourceChunks from './SourceChunks';
import { SourceChunk } from '@/lib/api';

interface MessageBubbleProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
    sources?: SourceChunk[];
  };
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className="message-row user-row">
        <div className="user-bubble">
          <div className="bubble-content">{message.content}</div>
        </div>
      </div>
    );
  }

  // Assistant message formatting
  return (
    <div className="message-row assistant-row">
      <div className="assistant-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="4" />
          <path d="M8 12h8" />
          <path d="M12 8v8" />
        </svg>
      </div>
      <div className="assistant-card">
        <div className="assistant-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h3: ({ node, ...props }) => (
                <h3 className="markdown-h3">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '6px'}}><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                  {props.children}
                </h3>
              ),
              h4: ({ node, ...props }) => (
                <h4 className="markdown-h4">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '6px'}}><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
                  {props.children}
                </h4>
              ),
              p: ({ node, ...props }) => {
                // If it contains a [S1] or [Source 1] marker, we can style it via CSS regex later,
                // but standard p tag is fine for now.
                return <p className="markdown-p">{props.children}</p>;
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        {message.sources && message.sources.length > 0 && (
          <SourceChunks sources={message.sources} />
        )}
      </div>
    </div>
  );
}
