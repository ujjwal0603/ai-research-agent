'use client';

import React, { useState } from 'react';

import { SourceChunk } from '@/lib/api';

interface SourceChunksProps {
  sources: SourceChunk[];
}

export default function SourceChunks({ sources }: SourceChunksProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="source-container">
      <button
        className={`source-header ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        {sources.length} source{sources.length !== 1 ? 's' : ''} used
      </button>
      {isOpen && (
        <div className="source-list">
          {sources.map((source, index) => (
            <div key={index} className="source-item">
              <div className="source-item-header">
                <span className="source-item-doc">{source.document_name}</span>
                <span className="source-item-page">Page {source.page_number}</span>
                <span className="score-badge">
                  {(source.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="source-item-text">
                {source.text.length > 200
                  ? source.text.slice(0, 200) + '…'
                  : source.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
