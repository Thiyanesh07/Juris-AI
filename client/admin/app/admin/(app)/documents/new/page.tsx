'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { DocumentTypeCategory } from '@/lib/types';
import { ADMIN_ROUTES } from '@/constants/routes';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { formatBytes } from '@/lib/utils';
import { Upload, ArrowLeft, CheckCircle2, AlertCircle, FileText, X, HardDrive } from 'lucide-react';

export default function CreateDocumentPage() {
  const router = useRouter();
  const { addDocument } = useDocumentStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState('');
  const [documentType, setDocumentType] = useState<DocumentTypeCategory>('Act');
  const [source, setSource] = useState('');
  const [authority, setAuthority] = useState('');
  const [jurisdiction, setJurisdiction] = useState('Union of India');
  const [publicationDate, setPublicationDate] = useState('');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [version, setVersion] = useState('');

  // Selected file state (simulation)
  const [selectedFile, setSelectedFile] = useState<{ name: string; size: number; type: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const [errors, setErrors] = useState<{ title?: string; file?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    setSelectedFile({
      name: file.name,
      size: file.size,
      type: file.type || 'application/pdf',
    });
    if (!title) {
      // Auto-populate title from filename
      const baseName = file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      setTitle(baseName.charAt(0).toUpperCase() + baseName.slice(1));
    }
    setErrors((prev) => ({ ...prev, file: undefined }));
  };

  const validate = (): boolean => {
    const errs: { title?: string; file?: string } = {};
    if (!title.trim()) errs.title = 'Document title is required.';
    if (!selectedFile) errs.file = 'Please select a document file to upload.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setSuccessMessage(null);

    setTimeout(() => {
      addDocument({
        title,
        fileName: selectedFile?.name || 'document.pdf',
        fileSizeBytes: selectedFile?.size || 5242880,
        mimeType: selectedFile?.type || 'application/pdf',
        documentType,
        source: source || 'Ministry of Law and Justice',
        authority: authority || 'Parliament of India',
        jurisdiction: jurisdiction || 'Union of India',
        publicationDate,
        effectiveDate,
        version,
        uploadedBy: 'admin@example.com',
      });

      setIsLoading(false);
      setSuccessMessage('Document added to development workspace.');

      setTimeout(() => {
        router.push(ADMIN_ROUTES.DOCUMENTS);
      }, 800);
    }, 400);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Upload Document"
        subtitle="Ingest legal statutory texts, acts, constitutional provisions, or precedent judgments."
        actions={
          <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Back to Documents
          </Button>
        }
      />

      {successMessage && (
        <div className="p-4 rounded-xl bg-[#D0EDDB] border border-[#B2E2C3] text-[#1E6B45] text-sm font-mono flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Drag and Drop Upload Area */}
        <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
          <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
            1. Document File Selection
          </h3>

          <input
            type="file"
            ref={fileInputRef}
            accept=".pdf,.docx,.txt"
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
                Drag and drop document file here, or <span className="text-[#2563A8] underline">browse</span>
              </p>
              <p className="text-xs text-[#718096] font-mono mt-1">
                Supported formats: PDF, TXT, DOCX &bull; Max file size ~50 MB
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
                    {formatBytes(selectedFile.size)} &bull; {selectedFile.type}
                  </p>
                </div>
              </div>

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSelectedFile(null)}
                className="text-[#8B2E2E]"
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
                >
                  <option value="Constitution">Constitution</option>
                  <option value="Act">Act</option>
                  <option value="Amendment Act">Amendment Act</option>
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
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Enacting Authority
                </label>
                <Input
                  value={authority}
                  onChange={(e) => setAuthority(e.target.value)}
                  placeholder="e.g. Parliament of India / Supreme Court"
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
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Publication Date
                </label>
                <Input
                  type="date"
                  value={publicationDate}
                  onChange={(e) => setPublicationDate(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Effective Date
                </label>
                <Input
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Version / Act Number Reference
                </label>
                <Input
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="e.g. Act No. 46 of 2023"
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
              Add Document to Workspace
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
