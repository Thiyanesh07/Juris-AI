"use client";

import { ArrowUpRight } from "lucide-react";
import { AnimatedWave } from "./animated-wave";

const footerLinks = {
  Product: [
    { name: "Features", href: "#features" },
    { name: "How It Works", href: "#how-it-works" },
    { name: "Knowledge Graph", href: "#knowledge-graph" },
    { name: "Technology", href: "#technology-stack" },
  ],
  Research: [
    { name: "Legal Research", href: "#" },
    { name: "Retrieval", href: "#features" },
    { name: "Reasoning", href: "#how-it-works" },
    { name: "Evaluation", href: "#pricing" },
  ],
  Project: [
    { name: "About", href: "#about" },
    { name: "Architecture", href: "#technology-stack" },
    { name: "Documentation", href: "#" },
  ],
  Legal: [
    { name: "Privacy", href: "#" },
    { name: "Terms", href: "#" },
    { name: "Security & Trust", href: "#security" },
  ],
};

const socialLinks = [
  { name: "GitHub", href: "#" },
  { name: "Documentation", href: "#" },
  { name: "Architecture", href: "#technology-stack" },
];

export function FooterSection() {
  return (
    <footer className="relative bg-[#DCE5EE] border-t border-[#C1CEDB]">
      {/* Animated wave background */}
      <div className="absolute inset-0 h-64 opacity-25 pointer-events-none overflow-hidden">
        <AnimatedWave />
      </div>
      
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Main Footer */}
        <div className="py-16 lg:py-24">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-12 lg:gap-8">
            {/* Brand Column */}
            <div className="col-span-2">
              <a href="#" className="inline-flex items-center gap-2 mb-6">
                <span className="text-2xl font-display text-[#17253A]">Juris AI</span>
              </a>

              <p className="text-[#526176] leading-relaxed mb-6 max-w-xs text-sm">
                AI-powered legal intelligence for Indian constitutional and statutory law.
              </p>

              <p className="text-xs text-[#526176]/80 leading-normal max-w-xs mb-8 italic">
                Disclaimer: Juris AI is a research and technology project and does not replace professional legal advice.
              </p>

              {/* Social Links */}
              <div className="flex gap-6">
                {socialLinks.map((link) => (
                  <a
                    key={link.name}
                    href={link.href}
                    className="text-sm text-[#526176] hover:text-[#2563A8] transition-colors flex items-center gap-1 group"
                  >
                    {link.name}
                    <ArrowUpRight className="w-3 h-3 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                  </a>
                ))}
              </div>
            </div>

            {/* Link Columns */}
            {Object.entries(footerLinks).map(([title, links]) => (
              <div key={title}>
                <h3 className="text-sm font-semibold text-[#17253A] mb-6">{title}</h3>
                <ul className="space-y-4">
                  {links.map((link) => (
                    <li key={link.name}>
                      <a
                        href={link.href}
                        className="text-sm text-[#526176] hover:text-[#2563A8] transition-colors inline-flex items-center gap-2"
                      >
                        {link.name}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="py-8 border-t border-[#C1CEDB] flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-[#526176]">
            © 2026 Juris AI. All rights reserved.
          </p>

          <div className="flex items-center gap-4 text-sm text-[#526176]">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#287A68]" />
              Research Prototype Status
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
