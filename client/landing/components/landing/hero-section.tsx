"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { LegalKnowledgeGraph } from "./legal-knowledge-graph";

const words = ["Search", "Connections", "Reasoning", "Verification"];

export function HeroSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [wordIndex, setWordIndex] = useState(0);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setWordIndex((prev) => (prev + 1) % words.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative min-h-screen flex flex-col justify-center overflow-hidden bg-[#E7EDF4]">
      {/* Subtle grid lines */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-40">
        {[...Array(8)].map((_, i) => (
          <div
            key={`h-${i}`}
            className="absolute h-px bg-[#CBD6E2]"
            style={{
              top: `${12.5 * (i + 1)}%`,
              left: 0,
              right: 0,
            }}
          />
        ))}
        {[...Array(12)].map((_, i) => (
          <div
            key={`v-${i}`}
            className="absolute w-px bg-[#CBD6E2]"
            style={{
              left: `${8.33 * (i + 1)}%`,
              top: 0,
              bottom: 0,
            }}
          />
        ))}
      </div>
      
      <div className="relative z-10 max-w-[1440px] mx-auto px-6 lg:px-12 py-20 lg:py-28 w-full">
        <div className="grid lg:grid-cols-12 gap-8 lg:gap-6 items-center">
          
          {/* Left Column — Text & CTAs (approx 42% width) */}
          <div className="lg:col-span-5 max-w-xl">
            {/* Eyebrow */}
            <div 
              className={`mb-6 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              <span className="inline-flex items-center gap-3 text-xs sm:text-sm font-mono text-[#2563A8] uppercase tracking-wider font-semibold">
                <span className="w-8 h-px bg-[#2563A8]/40" />
                AI-Powered Legal Research
              </span>
            </div>
            
            {/* Main headline — Desktop target 56px–68px scale */}
            <div className="mb-6">
              <h1 
                className={`text-3xl sm:text-4xl lg:text-[3.25rem] xl:text-[3.65rem] font-display leading-[1.05] tracking-tight text-[#17253A] transition-all duration-1000 ${
                  isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                }`}
              >
                <span className="block">Understand Indian</span>
                <span className="block">Law</span>
                <span className="block">
                  Beyond{" "}
                  <span className="relative inline-block">
                    <span 
                      key={wordIndex}
                      className="inline-flex text-[#2563A8]"
                    >
                      {words[wordIndex].split("").map((char, i) => (
                        <span
                          key={`${wordIndex}-${i}`}
                          className="inline-block animate-char-in"
                          style={{
                            animationDelay: `${i * 50}ms`,
                          }}
                        >
                          {char}
                        </span>
                      ))}
                    </span>
                    <span className="absolute -bottom-1 left-0 right-0 h-2 bg-[#2563A8]/15" />
                  </span>
                </span>
              </h1>
            </div>
            
            {/* Description */}
            <p 
              className={`text-base lg:text-lg text-[#526176] leading-relaxed mb-8 transition-all duration-700 delay-200 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              Juris AI connects constitutional provisions, statutes, amendments, judgments, 
              and legal authorities to deliver explainable, citation-grounded answers.
            </p>
            
            {/* CTAs */}
            <div 
              className={`flex flex-col sm:flex-row items-start gap-4 transition-all duration-700 delay-300 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              <a href={`${process.env.NEXT_PUBLIC_USER_URL || 'http://localhost:3002'}/signup`}>
                <Button 
                  size="lg" 
                  className="bg-[#2563A8] hover:bg-[#3B82D0] text-[#F5F7FA] px-8 h-14 text-base rounded-full group shadow-none cursor-pointer"
                >
                  Start Legal Research
                  <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                </Button>
              </a>
              <a href="#how-it-works">
                <Button 
                  size="lg" 
                  variant="outline" 
                  className="h-14 px-8 text-base rounded-full bg-[#EFF3F7] border-[#C9D4E1] text-[#17253A] hover:bg-[#D9E7F5]"
                >
                  See How It Works
                </Button>
              </a>
            </div>
          </div>
          
          {/* Right Column — Real Three.js 3D Isometric Legal Knowledge Graph (approx 58% width) */}
          <div 
            className={`lg:col-span-7 flex items-center justify-center transition-all duration-1000 delay-300 ${
              isVisible ? "opacity-100 scale-100" : "opacity-0 scale-95"
            }`}
          >
            <LegalKnowledgeGraph />
          </div>

        </div>
      </div>
      
      {/* Stats marquee - full width outside container */}
      <div 
        className={`absolute bottom-8 left-0 right-0 transition-all duration-700 delay-500 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="flex gap-16 marquee whitespace-nowrap">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="flex gap-16">
              {[
                { value: "GraphRAG", label: "knowledge graph engine", company: "JURIS AI" },
                { value: "Hybrid Retrieval", label: "semantic & vector search", company: "JURIS AI" },
                { value: "Multi-Hop", label: "cross-source reasoning", company: "JURIS AI" },
                { value: "Temporal", label: "amendment-aware logic", company: "JURIS AI" },
                { value: "Grounding", label: "citation verification", company: "JURIS AI" },
              ].map((stat) => (
                <div key={`${stat.value}-${i}`} className="flex items-baseline gap-4">
                  <span className="text-3xl lg:text-4xl font-display text-[#17253A]">{stat.value}</span>
                  <span className="text-sm text-[#526176]">
                    {stat.label}
                    <span className="block font-mono text-xs mt-1 text-[#2563A8]">{stat.company}</span>
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

