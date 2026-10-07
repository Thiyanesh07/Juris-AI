"use client";

import { useEffect, useState, useRef } from "react";

function AnimatedCounter({ end, suffix = "", prefix = "" }: { end: number; suffix?: string; prefix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          let start = 0;
          const duration = 2000;
          const startTime = performance.now();

          const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(eased * end));

            if (progress < 1) {
              requestAnimationFrame(animate);
            }
          };

          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.5 }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, hasAnimated]);

  return (
    <div ref={ref} className="text-6xl lg:text-8xl font-display tracking-tight text-[#183B5B]">
      {prefix}{count.toLocaleString()}{suffix}
    </div>
  );
}

const defaultMetrics = [
  { 
    value: 6235, 
    suffix: "", 
    prefix: "",
    label: "Knowledge Graph Nodes",
  },
  { 
    value: 26014, 
    suffix: "", 
    prefix: "",
    label: "Graph Relationships",
  },
  { 
    value: 2412, 
    suffix: "", 
    prefix: "",
    label: "FAISS Vector Chunks",
  },
  { 
    value: 34, 
    suffix: "", 
    prefix: "",
    label: "Indexed Corpus Documents",
  },
];

export function MetricsSection() {
  const [time, setTime] = useState<Date | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [metrics, setMetrics] = useState(defaultMetrics);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.endsWith('.local'));
    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    const apiBase = isLocal
      ? (envUrl && envUrl.trim() !== '' ? envUrl.trim() : 'http://localhost:8000')
      : (envUrl && envUrl.trim() !== '' && !envUrl.includes('localhost') && !envUrl.includes('127.0.0.1') ? envUrl.trim() : 'https://juris-ai-fhjw.onrender.com');
    fetch(`${apiBase.replace(/\/+$/, '')}/api/v1/public/stats`)
      .then((res) => res.json())
      .then((data) => {
        if (data.graph && data.vector && data.documents) {
          setMetrics([
            { value: data.graph.total_nodes || 6235, suffix: "", prefix: "", label: "Knowledge Graph Nodes" },
            { value: data.graph.total_relationships || 26014, suffix: "", prefix: "", label: "Graph Relationships" },
            { value: data.vector.total_vectors || 2412, suffix: "", prefix: "", label: "FAISS Vector Chunks" },
            { value: data.documents.total_documents || 34, suffix: "", prefix: "", label: "Indexed Corpus Documents" },
          ]);
        }
      })
      .catch((err) => console.log("Public stats fetch fallback:", err));
  }, []);

  useEffect(() => {
    setMounted(true);
    setTime(new Date());
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

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
    <section id="studio" ref={sectionRef} className="relative py-24 lg:py-32 border-y border-[#C9D4E1]">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8 mb-16 lg:mb-24">
          <div>
            <span className="inline-flex items-center gap-3 text-sm font-mono text-[#526176] mb-6 uppercase tracking-wider">
              <span className="w-8 h-px bg-[#2563A8]" />
              Research Metrics
            </span>
            <h2
              className={`text-4xl lg:text-6xl font-display tracking-tight text-[#17253A] transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              Measure What
              <br />
              Matters.
            </h2>
          </div>
          <div className="flex items-center gap-4 font-mono text-sm text-[#526176]">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#287A68] animate-pulse" />
              Research System
            </span>
            <span className="text-[#C9D4E1]">|</span>
            <span suppressHydrationWarning>{mounted && time ? time.toLocaleTimeString() : "--:--:--"}</span>
          </div>
        </div>
        
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[#C9D4E1] border border-[#C9D4E1]">
          {metrics.map((metric, index) => (
            <div
              key={metric.label}
              className={`bg-[#F5F7FA] p-8 lg:p-12 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              <AnimatedCounter 
                end={typeof metric.value === 'number' ? metric.value : 0} 
                suffix={metric.suffix} 
                prefix={metric.prefix}
              />
              <div className="mt-4 text-lg text-[#526176]">{metric.label}</div>
            </div>
          ))}
        </div>
        
        {/* Footnote */}
        <p className="mt-6 text-xs text-muted-foreground font-mono">
          *Live production corpus, vector index, and knowledge graph metrics.
        </p>
      </div>
    </section>
  );
}
