"use client";

import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";

const plans = [
  {
    name: "Retrieval",
    description: "Hybrid semantic and graph-based evidence retrieval.",
    badgeLabel: "Vector + Graph",
    features: [
      "Vector embedding search (FAISS)",
      "Knowledge graph entity linking",
      "Reciprocal Rank Fusion (RRF)",
      "Statute & judgment indexing",
      "Constitutional article mapping",
    ],
    cta: "Explore Retrieval",
    popular: false,
  },
  {
    name: "Reasoning",
    description: "Multi-hop reasoning over connected legal authorities.",
    badgeLabel: "Multi-Hop Traversal",
    features: [
      "Cross-provision relationship mapping",
      "Temporal amendment-aware logic",
      "Multi-step context aggregation",
      "Explainable reasoning paths",
      "Precedent hierarchy analysis",
    ],
    cta: "Explore Reasoning",
    popular: true,
  },
  {
    name: "Validation",
    description: "Citation grounding, provenance, and answer validation.",
    badgeLabel: "Citation Grounding",
    features: [
      "Source provenance tracking",
      "Verifiable authority references",
      "Hallucination reduction audit",
      "Grounding feedback loop",
      "Transparent evidence chains",
    ],
    cta: "Explore Validation",
    popular: false,
  },
];

export function PricingSection() {
  return (
    <section id="pricing" className="relative py-32 lg:py-40 border-t border-foreground/10">
      <div className="max-w-7xl mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="max-w-3xl mb-20">
          <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase block mb-6">
            Research &amp; Evaluation
          </span>
          <h2 className="font-display text-5xl md:text-6xl lg:text-7xl tracking-tight text-foreground mb-6">
            Built to Be
            <br />
            <span className="text-stroke">Evaluated.</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-xl">
            Juris AI is designed as an explainable legal intelligence system that can be evaluated across retrieval, reasoning, graph traversal, and citation grounding.
          </p>
        </div>

        {/* Pricing/Evaluation Cards */}
        <div className="grid md:grid-cols-3 gap-px bg-foreground/10">
          {plans.map((plan, idx) => (
            <div
              key={plan.name}
              className={`relative p-8 lg:p-12 bg-background ${
                plan.popular ? "md:-my-4 md:py-12 lg:py-16 border-2 border-primary" : ""
              }`}
            >
              {plan.popular && (
                <span className="absolute -top-3 left-8 px-3 py-1 bg-primary text-primary-foreground text-xs font-mono uppercase tracking-widest">
                  Core Engine
                </span>
              )}

              {/* Plan Header */}
              <div className="mb-8">
                <span className="font-mono text-xs text-muted-foreground">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <h3 className="font-display text-3xl text-foreground mt-2">{plan.name}</h3>
                <p className="text-sm text-muted-foreground mt-2">{plan.description}</p>
              </div>

              {/* Badge Label */}
              <div className="mb-8 pb-8 border-b border-foreground/10">
                <span className="font-display text-3xl text-foreground">{plan.badgeLabel}</span>
              </div>

              {/* Features */}
              <ul className="space-y-4 mb-10">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <Check className="w-4 h-4 text-foreground mt-0.5 shrink-0" />
                    <span className="text-sm text-muted-foreground">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <a href="#how-it-works" className="block w-full">
                <button
                  type="button"
                  className={`w-full py-4 flex items-center justify-center gap-2 text-sm font-medium transition-all group ${
                    plan.popular
                      ? "bg-primary text-primary-foreground hover:bg-accent"
                      : "border border-border text-foreground hover:border-primary hover:bg-primary/5"
                  }`}
                >
                  {plan.cta}
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
              </a>
            </div>
          ))}
        </div>

        {/* Bottom Note */}
        <p className="mt-12 text-center text-sm text-muted-foreground">
          Juris AI is an explainable legal research system focusing on Indian constitutional and statutory law.
        </p>
      </div>
    </section>
  );
}
