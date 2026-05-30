'use client';

import React, { useRef, useState } from 'react';

interface FileUploadProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function FileUpload({ onUpload, isUploading }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type === 'application/pdf') {
        onUpload(file);
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files[0]);
      // Reset so the same file can be re-uploaded
      e.target.value = '';
    }
  };

  const zoneClasses = [
    'upload-zone',
    isDragging ? 'dragging' : '',
    isUploading ? 'uploading' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      className={zoneClasses}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <div className="upload-zone-icon">
        {isUploading ? (
          <div className="spinner" />
        ) : (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        )}
      </div>

      <div className="upload-zone-text">
        {isUploading ? (
          <p>Uploading document…</p>
        ) : (
          <>
            <p>
              <strong>Click to upload</strong> or drag & drop
            </p>
            <span>PDF files only</span>
          </>
        )}
      </div>
    </div>
  );
}
