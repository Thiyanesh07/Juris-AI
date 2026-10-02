"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { AnimatedTetrahedron } from "./animated-tetrahedron";

export function CtaSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.2 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePosition({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <section ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div
          className={`relative border border-[#C9D4E1] bg-[#D9E5F0] rounded-xl transition-all duration-1000 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          onMouseMove={handleMouseMove}
        >
          <div 
            className="absolute inset-0 opacity-40 pointer-events-none transition-opacity duration-300 rounded-xl"
            style={{
              background: `radial-gradient(600px circle at ${mousePosition.x}% ${mousePosition.y}%, rgba(37,99,168,0.15), transparent 40%)`
            }}
          />
          
          <div className="relative z-10 px-8 lg:px-16 py-16 lg:py-24">
            <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
              {/* Left content */}
              <div className="flex-1">
                <h2 className="text-4xl lg:text-7xl font-display tracking-tight text-[#17253A] mb-8 leading-[0.95]">
                  Explore Indian Law
                  <br />
                  Through Its Connections.
                </h2>

                <p className="text-xl text-[#526176] mb-12 leading-relaxed max-w-xl">
                  Ask complex legal questions and trace the evidence, relationships, 
                  and reasoning behind the answer.
                </p>

                <div className="flex flex-col sm:flex-row items-start gap-4">
                  <Button
                    size="lg"
                    className="bg-[#2563A8] hover:bg-[#3B82D0] text-[#F5F7FA] px-8 h-14 text-base rounded-full group shadow-none"
                  >
                    Start Legal Research
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                  </Button>
                  <a href="#knowledge-graph">
                    <Button
                      size="lg"
                      variant="outline"
                      className="h-14 px-8 text-base rounded-full bg-[#EFF3F7] border-[#C9D4E1] text-[#17253A] hover:bg-[#D9E7F5]"
                    >
                      Explore the Knowledge Graph
                    </Button>
                  </a>
                </div>
              </div>

              {/* Right animation */}
              <div className="hidden lg:flex items-center justify-center w-[500px] h-[500px] -mr-16">
                <AnimatedTetrahedron />
              </div>
            </div>
          </div>

          {/* Decorative corner */}
          <div className="absolute top-0 right-0 w-32 h-32 border-b border-l border-foreground/10" />
          <div className="absolute bottom-0 left-0 w-32 h-32 border-t border-r border-foreground/10" />
        </div>
      </div>
    </section>
  );
}
