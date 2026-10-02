"use client";

import { useState, useEffect, useRef } from "react";
import { Copy, Check } from "lucide-react";

const codeExamples = [
  {
    label: "Frontend",
    code: `// Next.js + React + TypeScript Layer
import { Navigation } from "@/components/landing/navigation"
import { GraphRAGViewer } from "@/components/legal/graph-viewer"

export default function LegalResearchPage() {
  return <GraphRAGViewer query="Article" />
}`,
  },
  {
    label: "Backend",
    code: `# FastAPI + PostgreSQL + Neo4j + FAISS
from fastapi import FastAPI
from juris_ai.graph_rag import GraphRAGPipeline

app = FastAPI(title="Juris AI Engine API")
pipeline = GraphRAGPipeline(
    neo4j_uri="bolt://localhost:7687",
    faiss_index="./data/index.faiss"
)`,
  },
  {
    label: "GraphRAG Pipeline",
    code: `// GraphRAG Execution Chain
Legal Query
  └─> Hybrid Retrieval (Vector + Graph)
        └─> Knowledge Graph Traversal
              └─> Multi-Hop Reasoning
                    └─> Citation Grounding & Validation`,
  },
];

const features = [
  { 
    title: "Layered Stack", 
    description: "Decoupled web interface, API backend, and GraphRAG engine."
  },
  { 
    title: "Vector + Knowledge Graph", 
    description: "FAISS dense embeddings paired with Neo4j graph relationships."
  },
  { 
    title: "FastAPI & Next.js", 
    description: "High-throughput REST API with a reactive, modern frontend."
  },
  { 
    title: "Auditability & Grounding", 
    description: "Full citation provenance for every generated response."
  },
];

const codeAnimationStyles = `
  .dev-code-line {
    opacity: 0;
    transform: translateX(-8px);
    animation: devLineReveal 0.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }
  
  @keyframes devLineReveal {
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
  
  .dev-code-char {
    opacity: 0;
    filter: blur(8px);
    animation: devCharReveal 0.3s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }
  
  @keyframes devCharReveal {
    to {
      opacity: 1;
      filter: blur(0);
    }
  }
`;

export function DevelopersSection() {
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeExamples[activeTab].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="technology-stack" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <style dangerouslySetInnerHTML={{ __html: codeAnimationStyles }} />
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-start">
          {/* Left: Content */}
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6 uppercase tracking-wider">
              <span className="w-8 h-px bg-foreground/30" />
              Technology
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-8">
              Under the Hood of
              <br />
              <span className="text-muted-foreground">Juris AI.</span>
            </h2>
            <p className="text-xl text-muted-foreground mb-12 leading-relaxed">
              A layered architecture combining modern web technologies, 
              legal language models, vector retrieval, knowledge graphs, and agent-based reasoning.
            </p>
            
            {/* Features */}
            <div className="grid grid-cols-2 gap-6">
              {features.map((feature, index) => (
                <div
                  key={feature.title}
                  className={`transition-all duration-500 ${
                    isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                  }`}
                  style={{ transitionDelay: `${index * 50 + 200}ms` }}
                >
                  <h3 className="font-medium mb-1">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
          
          {/* Right: Code block */}
          <div
            className={`lg:sticky lg:top-32 transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"
            }`}
          >
            <div className="border border-[#C1CEDB] rounded-lg overflow-hidden bg-[#DCE5EE] shadow-sm">
              {/* Tabs */}
              <div className="flex items-center border-b border-[#C1CEDB] bg-[#D3E0EC]">
                {codeExamples.map((example, idx) => (
                  <button
                    key={example.label}
                    type="button"
                    onClick={() => setActiveTab(idx)}
                    className={`px-6 py-4 text-sm font-mono transition-colors relative ${
                      activeTab === idx
                        ? "text-[#17253A] font-semibold"
                        : "text-[#526176] hover:text-[#17253A]"
                    }`}
                  >
                    {example.label}
                    {activeTab === idx && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2563A8]" />
                    )}
                  </button>
                ))}
                <div className="flex-1" />
                <button
                  type="button"
                  onClick={handleCopy}
                  className="px-4 py-4 text-[#526176] hover:text-[#17253A] transition-colors"
                  aria-label="Copy code"
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-[#287A68]" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
              
              {/* Code content */}
              <div className="p-8 font-mono text-sm bg-[#DCE5EE] min-h-[220px]">
                <pre className="text-[#17253A]">
                  {codeExamples[activeTab].code.split('\n').map((line, lineIndex) => (
                    <div 
                      key={`${activeTab}-${lineIndex}`} 
                      className="leading-loose dev-code-line"
                      style={{ animationDelay: `${lineIndex * 80}ms` }}
                    >
                      <span className="inline-flex text-[#17253A]">
                        {line.split('').map((char, charIndex) => (
                          <span
                            key={`${activeTab}-${lineIndex}-${charIndex}`}
                            className="dev-code-char"
                            style={{
                              animationDelay: `${lineIndex * 80 + charIndex * 15}ms`,
                            }}
                          >
                            {char === ' ' ? '\u00A0' : char}
                          </span>
                        ))}
                      </span>
                    </div>
                  ))}
                </pre>
              </div>
            </div>
            
            {/* Links */}
            <div className="mt-6 flex items-center gap-6 text-sm">
              <a href="#how-it-works" className="text-accent hover:underline underline-offset-4">
                Read Architecture
              </a>
              <span className="text-foreground/20">|</span>
              <a href="#knowledge-graph" className="text-muted-foreground hover:text-foreground">
                Explore Knowledge Graph
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
