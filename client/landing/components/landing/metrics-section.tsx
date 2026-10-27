"use client";

import { useEffect, useState, useRef } from "react";
import { getApiBaseUrl } from "@/lib/config";

interface MetricItem {
  value: number | null;
  suffix: string;
  prefix: string;
  label: string;
}

function AnimatedCounter({ end, suffix = "", prefix = "" }: { end: number | null; suffix?: string; prefix?: string }) {
  const [count, setCount] = useState<number | null>(end);
  const ref = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    if (end === null) {
      setCount(null);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
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
      {end === null ? (
        <span className="text-[#899BB1] text-5xl">--</span>
      ) : (
        `${prefix}${(count ?? end).toLocaleString()}${suffix}`
      )}
    </div>
  );
}

const initialMetrics: MetricItem[] = [
  { value: null, suffix: "", prefix: "", label: "Knowledge Graph Nodes" },
  { value: null, suffix: "", prefix: "", label: "Graph Relationships" },
  { value: null, suffix: "", prefix: "", label: "FAISS Vector Chunks" },
  { value: null, suffix: "", prefix: "", label: "Indexed Corpus Documents" },
];

export function MetricsSection() {
  const [time, setTime] = useState<Date | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [metrics, setMetrics] = useState<MetricItem[]>(initialMetrics);
  const [statusMessage, setStatusMessage] = useState<string | null>("Loading live corpus metrics...");
  const [isError, setIsError] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const apiBase = getApiBaseUrl();
    if (!apiBase) {
      setIsError(true);
      setStatusMessage("API endpoint not configured");
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    fetch(`${apiBase}/stats`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (typeof data.graph_nodes === "number" && typeof data.total_documents === "number") {
          setMetrics([
            { value: data.graph_nodes, suffix: "", prefix: "", label: "Knowledge Graph Nodes" },
            { value: data.graph_relationships, suffix: "", prefix: "", label: "Graph Relationships" },
            { value: data.vector_count, suffix: "", prefix: "", label: "FAISS Vector Chunks" },
            { value: data.total_documents, suffix: "", prefix: "", label: "Indexed Corpus Documents" },
          ]);
          setStatusMessage(null);
          setIsError(false);
        } else {
          setIsError(true);
          setStatusMessage("Corpus metrics response malformed");
        }
      })
      .catch(() => {
        setIsError(true);
        setStatusMessage("Corpus metrics temporarily unavailable");
      })
      .finally(() => clearTimeout(timeout));

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
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
              <span className={`w-2 h-2 rounded-full ${isError ? 'bg-[#C2410C]' : 'bg-[#287A68] animate-pulse'}`} />
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
                end={metric.value}
                suffix={metric.suffix}
                prefix={metric.prefix}
              />
              <div className="mt-4 text-lg text-[#526176]">{metric.label}</div>
            </div>
          ))}
        </div>
        
        {/* Footnote */}
        <p className={`mt-6 text-xs font-mono ${isError ? 'text-[#8B2E2E]' : 'text-muted-foreground'}`}>
          {statusMessage ? `*${statusMessage}` : '*Live production corpus, vector index, and knowledge graph metrics.'}
        </p>
      </div>
    </section>
  );
}
