'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Search,
  Clock,
  Bookmark,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Scale,
  GitFork,
  Cpu,
  BookOpen,
  Layers,
} from 'lucide-react';
import { formatDate, truncate } from '@/lib/utils';
import { useResearchStore } from '@/context/ResearchStoreContext';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ResearchHistoryRecord } from '@/lib/types';

const EXAMPLE_QUERIES = [
  'What constitutional provisions are relevant to the right to life under Article 21?',
  'How has Article 21 been interpreted in Maneka Gandhi v Union of India?',
  'What is the relationship between Article 14 and Article 21 in Indian constitutional jurisprudence?',
  'Which constitutional amendment affected Article 21 and when?',
];

const CAPABILITIES = [
  {
    icon: <GitFork className="h-5 w-5 text-[#1D4E8A]" />,
    title: 'Knowledge Graph Traversal',
    description: 'Multi-hop reasoning across typed legal relationships: articles, judgments, amendments, and statutes.',
  },
  {
    icon: <Cpu className="h-5 w-5 text-[#1D4E8A]" />,
    title: 'Hybrid Retrieval',
    description: 'Combines dense vector semantic search with structured graph traversal for comprehensive coverage.',
  },
  {
    icon: <BookOpen className="h-5 w-5 text-[#1D4E8A]" />,
    title: 'Citation Grounding',
    description: 'Every legal claim is anchored to verified constitutional provisions, statutes, or judicial authorities.',
  },
  {
    icon: <Layers className="h-5 w-5 text-[#1D4E8A]" />,
    title: 'Temporal Legal Analysis',
    description: 'Traces how law has evolved — from original provisions through amendments and landmark judgments.',
  },
];

const getCitationStatusBadge = (status?: ResearchHistoryRecord['citationStatus']) => {
  switch (status) {
    case 'ALL_VERIFIED':
      return <Badge variant="success"><CheckCircle2 className="h-2.5 w-2.5 mr-1" />Verified</Badge>;
    case 'PARTIAL':
      return <Badge variant="warning"><AlertCircle className="h-2.5 w-2.5 mr-1" />Partial</Badge>;
    default:
      return <Badge variant="default"><HelpCircle className="h-2.5 w-2.5 mr-1" />Grounded</Badge>;
  }
};

export default function HomePage() {
  const router = useRouter();
  const { history, savedResearch } = useResearchStore();

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-10 pb-16">
      {/* Hero */}
      <section className="pt-6">
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 rounded-xl bg-[#1D4E8A] shadow-md">
            <Scale className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl text-[#17253A] leading-tight font-display font-semibold">
              Legal Research, Connected.
            </h1>
            <p className="text-[#526176] mt-2 text-base max-w-2xl leading-relaxed">
              Juris AI connects constitutional provisions, statutes, amendments, judicial decisions, and legal doctrine through a typed Knowledge Graph — enabling multi-hop legal reasoning across Indian law.
            </p>
          </div>
        </div>

        {/* Quick start actions */}
        <div className="flex flex-wrap gap-3">
          <Link href="/research">
            <Button variant="primary" size="lg" className="gap-2">
              <Search className="h-4 w-4" />
              Start New Research
            </Button>
          </Link>
          <Link href="/history">
            <Button variant="secondary" size="lg" className="gap-2">
              <Clock className="h-4 w-4" />
              View Research History
            </Button>
          </Link>
        </div>

        {/* Example queries */}
        <div className="mt-5 p-4 rounded-xl bg-white border border-[#CBD5E0] shadow-sm">
          <p className="text-xs font-mono font-bold text-[#526176] uppercase tracking-wider mb-3">Verified Research Queries:</p>
          <div className="space-y-2">
            {EXAMPLE_QUERIES.map((q, i) => (
              <button
                key={i}
                onClick={() => router.push(`/research?q=${encodeURIComponent(q)}`)}
                className="w-full text-left flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-[#F0F4F8] hover:bg-[#E8F0FD] hover:border-[#BFDBFE] border border-transparent transition-colors group cursor-pointer"
              >
                <span className="text-sm text-[#17253A] group-hover:text-[#1D4E8A] font-medium">{q}</span>
                <ArrowRight className="h-4 w-4 text-[#718096] group-hover:text-[#1D4E8A] shrink-0" />
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Recent Research */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg text-[#17253A] font-semibold">Recent Research</h2>
          {history.length > 0 && (
            <Link href="/history" className="text-xs font-mono text-[#1D4E8A] hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        {history.length === 0 ? (
          <div className="card p-8 text-center space-y-2 border-[#CBD5E0]">
            <Clock className="h-8 w-8 text-[#94A3B8] mx-auto" />
            <p className="text-sm text-[#17253A] font-medium">No research sessions yet</p>
            <p className="text-xs text-[#64748B]">Submit a query above to execute hybrid GraphRAG retrieval against the legal corpus.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {history.slice(0, 4).map(record => (
              <div
                key={record.id}
                onClick={() => router.push(`/research?from=${record.id}`)}
                className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer hover:border-[#1D4E8A]/30 hover:shadow-md transition-all"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#17253A] leading-snug">
                    {truncate(record.query, 90)}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs font-mono text-[#718096]">
                    <span>{formatDate(record.createdAt)}</span>
                    <span>·</span>
                    <Badge variant="default">{record.mode}</Badge>
                    <span>{record.sourcesCount} sources</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {getCitationStatusBadge(record.citationStatus)}
                  {record.saved && <Badge variant="primary"><Bookmark className="h-2.5 w-2.5 mr-0.5" />Saved</Badge>}
                  <ArrowRight className="h-4 w-4 text-[#718096]" />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Saved Research */}
      {savedResearch.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg text-[#17253A] font-semibold">Saved Research</h2>
            <Link href="/saved" className="text-xs font-mono text-[#1D4E8A] hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {savedResearch.slice(0, 3).map(saved => (
              <div key={saved.id} className="card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="text-sm font-semibold text-[#17253A] leading-snug line-clamp-2">{saved.title}</p>
                  <Bookmark className="h-4 w-4 text-[#1D4E8A] shrink-0 mt-0.5" />
                </div>
                <p className="text-xs text-[#526176] leading-relaxed line-clamp-2 mb-3">{saved.summary}</p>
                <div className="flex flex-wrap gap-1 mb-3">
                  {saved.tags.slice(0, 3).map(tag => (
                    <span key={tag} className="badge badge-default text-[10px]">{tag}</span>
                  ))}
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-[#718096] border-t border-[#E2E8F0] pt-2.5">
                  <span>{formatDate(saved.savedAt)}</span>
                  <button className="text-[#1D4E8A] hover:underline font-semibold cursor-pointer">Open →</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Research Capabilities */}
      <section className="space-y-4">
        <h2 className="text-lg text-[#17253A] font-semibold">System Capabilities</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {CAPABILITIES.map((cap, i) => (
            <div key={i} className="card p-5 flex gap-4">
              <div className="p-2.5 rounded-xl bg-[#E8F0FD] border border-[#BFDBFE] h-fit">
                {cap.icon}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#17253A] mb-1 font-sans">{cap.title}</h3>
                <p className="text-xs text-[#526176] leading-relaxed">{cap.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

