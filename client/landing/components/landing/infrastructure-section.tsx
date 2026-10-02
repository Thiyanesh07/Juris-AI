"use client";

import { useEffect, useState, useRef } from "react";

const locations = [
  { city: "Document Ingestion", region: "Statutory PDF & Judgment OCR Pipeline", latency: "Ingestion" },
  { city: "Legal Processing", region: "Entity & Provision Extraction Engine", latency: "Extraction" },
  { city: "Knowledge Graph", region: "Relational Precedent Traversal", latency: "Graph Index" },
  { city: "Vector Index", region: "Dense Semantic Embedding Space", latency: "Vector Store" },
  { city: "Hybrid Retrieval", region: "Reciprocal Rank Fusion (RRF) Layer", latency: "Fusion Layer" },
  { city: "Reasoning & Grounding", region: "Multi-Hop Evidence & Citation Audit", latency: "Reasoning Engine" },
];

export function InfrastructureSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activeLocation, setActiveLocation] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);

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

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveLocation((prev) => (prev + 1) % locations.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="technology" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left: Content */}
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6 uppercase tracking-wider">
              <span className="w-8 h-px bg-foreground/30" />
              Legal Knowledge Infrastructure
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-8">
              Built Around Connected
              <br />
              Legal Knowledge.
            </h2>
            <p className="text-xl text-muted-foreground leading-relaxed mb-12">
              Juris AI combines document processing, legal knowledge graphs, 
              semantic retrieval, and reasoning components to connect the evidence needed for legal research.
            </p>

            {/* System Pillars */}
            <div className="grid grid-cols-3 gap-8">
              <div>
                <div className="text-3xl lg:text-4xl font-display mb-2">GraphRAG</div>
                <div className="text-sm text-muted-foreground">Knowledge Graph</div>
              </div>
              <div>
                <div className="text-3xl lg:text-4xl font-display mb-2">Hybrid</div>
                <div className="text-sm text-muted-foreground">Vector + Graph</div>
              </div>
              <div>
                <div className="text-3xl lg:text-4xl font-display mb-2">Grounded</div>
                <div className="text-sm text-muted-foreground">Citation Audit</div>
              </div>
            </div>
          </div>

          {/* Right: Location/Layer list */}
          <div
            className={`transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"
            }`}
          >
            <div className="border border-foreground/10">
              {/* Header */}
              <div className="px-6 py-4 border-b border-foreground/10 flex items-center justify-between">
                <span className="text-sm font-mono text-muted-foreground">Architecture Pipeline</span>
                <span className="flex items-center gap-2 text-xs font-mono text-[#287A68]">
                  <span className="w-2 h-2 rounded-full bg-[#287A68] animate-pulse" />
                  Active Pipeline
                </span>
              </div>

              {/* Locations */}
              <div>
                {locations.map((location, index) => (
                  <div
                    key={location.city}
                    className={`px-6 py-5 border-b border-border/50 last:border-b-0 flex items-center justify-between transition-all duration-300 ${
                      activeLocation === index ? "bg-primary/[0.04]" : ""
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <span 
                        className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                          activeLocation === index ? "bg-primary" : "bg-foreground/20"
                        }`}
                      />
                      <div>
                        <div className="font-medium">{location.city}</div>
                        <div className="text-sm text-muted-foreground">{location.region}</div>
                      </div>
                    </div>
                    <span className="font-mono text-sm text-muted-foreground">{location.latency}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
