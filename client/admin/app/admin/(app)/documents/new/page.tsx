'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { DocumentTypeCategory } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { formatBytes } from '@/lib/utils';
import { Upload, ArrowLeft, CheckCircle2, AlertCircle, FileText, X, HardDrive, Cpu } from 'lucide-react';

export default function CreateDocumentPage() {
  const router = useRouter();
  const { uploadDocument } = useDocumentStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState('');
  const [documentType, setDocumentType] = useState<DocumentTypeCategory>('Act');
  const [source, setSource] = useState('');
  const [authority, setAuthority] = useState('');
  const [jurisdiction, setJurisdiction] = useState('Union of India');

  // Real File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const [errors, setErrors] = useState<{ title?: string; file?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [createdDocId, setCreatedDocId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    setSelectedFile(file);
    if (!title) {
      // Auto-populate title from filename
      const baseName = file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      setTitle(baseName.charAt(0).toUpperCase() + baseName.slice(1));
    }
    setErrors((prev) => ({ ...prev, file: undefined }));
    setUploadError(null);
  };

  const validate = (): boolean => {
    const errs: { title?: string; file?: string } = {};
    if (!title.trim()) errs.title = 'Document title is required.';
    if (!selectedFile) errs.file = 'Please select a document file to upload.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || !selectedFile) return;

    setIsLoading(true);
    setUploadError(null);
    setSuccessMessage(null);
    setCreatedDocId(null);

    try {
      const res = await uploadDocument(selectedFile, {
        title: title.trim(),
        type: documentType,
        source: source.trim() || 'Official Gazette / Parliament of India',
        source_url: authority.trim() || undefined,
      });

      if (res && res.document_id) {
        setCreatedDocId(res.document_id);
        setSuccessMessage(
          `Document accepted by backend pipeline. Document ID: ${res.document_id}${
            res.duplicate ? ' (Existing file hash detected)' : ''
          }`
        );
      } else {
        throw new Error('Backend did not return a valid document identity.');
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed. Please check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Upload Legal Document"
        actions={
          <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Back to Documents
          </Button>
        }
      />

      {/* Success Notification */}
      {successMessage && createdDocId && (
        <div className="p-4 rounded-xl bg-[#D0EDDB] border border-[#B2E2C3] text-[#1E6B45] text-xs font-mono space-y-3 animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <span className="font-semibold">{successMessage}</span>
          </div>
          <div className="flex items-center gap-3 pt-2 border-t border-[#B2E2C3]/60">
            <Link href={ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(createdDocId)}>
              <Button variant="primary" size="sm">
                <Cpu className="h-3.5 w-3.5 mr-1.5" />
                Track Ingestion Stages
              </Button>
            </Link>
            <Link href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(createdDocId)}>
              <Button variant="secondary" size="sm">
                <FileText className="h-3.5 w-3.5 mr-1.5" />
                View Document
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Upload Error Alert */}
      {uploadError && (
        <div className="p-4 rounded-xl bg-[#F5D9D9] border border-[#E8B8B8] text-[#8B2E2E] text-xs font-mono flex items-center gap-2">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>Upload failed: {uploadError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Drag and Drop Selection */}
        <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
          <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
            1. Document File Selection
          </h3>

          <input
            type="file"
            ref={fileInputRef}
            accept=".pdf,.txt,.docx"
            className="hidden"
            onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
          />

          {!selectedFile ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files?.[0]) handleFileChange(e.dataTransfer.files[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`p-8 border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors flex flex-col items-center justify-center ${
                isDragging
                  ? 'border-[#2563A8] bg-[#D9E7F5]/30'
                  : 'border-[#C9D4E1] hover:border-[#3B82D0] bg-[#EFF3F7]/40'
              }`}
            >
              <div className="p-3 rounded-full bg-[#D9E7F5] text-[#2563A8] mb-3">
                <Upload className="h-6 w-6" />
              </div>
              <p className="text-sm font-semibold text-[#17253A]">
                Drag and drop legal document file here, or <span className="text-[#2563A8] underline">browse files</span>
              </p>
              <p className="text-xs text-[#718096] font-mono mt-1">
                Accepted: PDF, TXT, DOCX &bull; Maximum upload size: 50 MB
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-[#2563A8] text-white">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-[#17253A] font-mono">{selectedFile.name}</h4>
                  <p className="text-[11px] text-[#718096] font-mono">
                    {formatBytes(selectedFile.size)} &bull; {selectedFile.type || 'application/octet-stream'}
                  </p>
                </div>
              </div>

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSelectedFile(null)}
                className="text-[#8B2E2E]"
                disabled={isLoading}
              >
                <X className="h-4 w-4 mr-1" /> Remove
              </Button>
            </div>
          )}

          {errors.file && (
            <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" /> {errors.file}
            </p>
          )}
        </div>

        {/* Metadata Inputs */}
        <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
          <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
            2. Legal Corpus Metadata
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                Document Title <span className="text-[#8B2E2E]">*</span>
              </label>
              <Input
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
                }}
                placeholder="e.g. Bharatiya Nagarik Suraksha Sanhita, 2023"
                error={!!errors.title}
                disabled={isLoading}
              />
              {errors.title && (
                <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" /> {errors.title}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Document Type
                </label>
                <Select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as DocumentTypeCategory)}
                  disabled={isLoading}
                >
                  <option value="Constitution">Constitution</option>
                  <option value="Act">Act</option>
                  <option value="Rule">Rule</option>
                  <option value="Regulation">Regulation</option>
                  <option value="Judgment">Judgment</option>
                  <option value="Notification">Notification</option>
                  <option value="Other">Other</option>
                </Select>
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Legal Source
                </label>
                <Input
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  placeholder="e.g. Ministry of Law and Justice"
                  disabled={isLoading}
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Enacting Authority / Source URL
                </label>
                <Input
                  value={authority}
                  onChange={(e) => setAuthority(e.target.value)}
                  placeholder="e.g. Parliament of India / https://indiacode.nic.in"
                  disabled={isLoading}
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Jurisdiction
                </label>
                <Input
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                  placeholder="e.g. Union of India"
                  disabled={isLoading}
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#D9E1EA]">
            <Button
              type="button"
              variant="ghost"
              onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isLoading}>
              <HardDrive className="h-4 w-4 mr-1.5" />
              Upload & Ingest Document
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
