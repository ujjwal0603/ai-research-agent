'use client';

import React from 'react';
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
  return (
    <div className={`message ${message.role}`}>
      <div className="message-avatar">
        {message.role === 'user' ? (
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        )}
      </div>
      <div>
        <div className="bubble">
          <div className="bubble-content">{message.content}</div>
        </div>
        {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
          <SourceChunks sources={message.sources} />
        )}
      </div>
    </div>
  );
}
