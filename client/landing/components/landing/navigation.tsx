"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";

const navLinks = [
  { name: "Features", href: "#features" },
  { name: "How It Works", href: "#how-it-works" },
  { name: "Knowledge Graph", href: "#knowledge-graph" },
  { name: "Technology", href: "#technology" },
  { name: "About", href: "#about" },
];

export function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={`fixed z-50 transition-all duration-500 ${
        isScrolled 
          ? "top-4 left-4 right-4" 
          : "top-0 left-0 right-0"
      }`}
    >
      <nav 
        className={`mx-auto transition-all duration-500 ${
          isScrolled || isMobileMenuOpen
            ? "bg-background/80 backdrop-blur-xl border border-foreground/10 rounded-2xl shadow-lg max-w-[1200px]"
            : "bg-transparent max-w-[1400px]"
        }`}
      >
        <div 
          className={`flex items-center justify-between transition-all duration-500 px-6 lg:px-8 ${
            isScrolled ? "h-14" : "h-20"
          }`}
        >
          {/* Logo */}
          <a href="#" className="flex items-center gap-2 group">
            <span className={`font-display tracking-tight transition-all duration-500 ${isScrolled ? "text-xl" : "text-2xl"}`}>Juris AI</span>
          </a>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-12">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-sm text-muted-foreground hover:text-primary transition-colors duration-300 relative group"
              >
                {link.name}
                <span className="absolute -bottom-1 left-0 w-0 h-px bg-primary transition-all duration-300 group-hover:w-full" />
              </a>
            ))}
          </div>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-4">
            <a
              href="http://localhost:3002/login"
              className={`text-muted-foreground hover:text-foreground transition-all duration-500 ${isScrolled ? "text-xs" : "text-sm"}`}
            >
              Sign In
            </a>
            <a
              href="http://localhost:3002/signup"
              className={`text-muted-foreground hover:text-foreground transition-all duration-500 ${isScrolled ? "text-xs" : "text-sm"}`}
            >
              Sign Up
            </a>
            <a href="http://localhost:3002/signup">
              <Button
                size="sm"
                className={`bg-primary hover:bg-[#3B82D0] text-[#F5F7FA] rounded-full transition-all duration-500 ${isScrolled ? "px-4 h-8 text-xs" : "px-6"}`}
              >
                Start Research
              </Button>
            </a>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2"
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

      </nav>
      
      {/* Mobile Menu - Full Screen Overlay */}
      <div
        className={`md:hidden fixed inset-0 bg-background z-40 transition-all duration-500 ${
          isMobileMenuOpen 
            ? "opacity-100 pointer-events-auto" 
            : "opacity-0 pointer-events-none"
        }`}
        style={{ top: 0 }}
      >
        <div className="flex flex-col h-full px-8 pt-28 pb-8">
          {/* Navigation Links */}
          <div className="flex-1 flex flex-col justify-center gap-8">
            {navLinks.map((link, i) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`text-5xl font-display text-foreground hover:text-muted-foreground transition-all duration-500 ${
                  isMobileMenuOpen 
                    ? "opacity-100 translate-y-0" 
                    : "opacity-0 translate-y-4"
                }`}
                style={{ transitionDelay: isMobileMenuOpen ? `${i * 75}ms` : "0ms" }}
              >
                {link.name}
              </a>
            ))}
          </div>
          
          {/* Bottom CTAs */}
          <div className={`flex flex-col gap-3 pt-8 border-t border-foreground/10 transition-all duration-500 ${
            isMobileMenuOpen 
              ? "opacity-100 translate-y-0" 
              : "opacity-0 translate-y-4"
          }`}
          style={{ transitionDelay: isMobileMenuOpen ? "300ms" : "0ms" }}
          >
            <div className="flex gap-3">
              <a href="http://localhost:3002/login" className="flex-1">
                <Button 
                  variant="outline" 
                  className="w-full rounded-full h-12 text-sm border-border text-foreground hover:bg-secondary"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Button>
              </a>
              <a href="http://localhost:3002/signup" className="flex-1">
                <Button 
                  variant="outline" 
                  className="w-full rounded-full h-12 text-sm border-border text-foreground hover:bg-secondary"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign Up
                </Button>
              </a>
            </div>
            <a href="http://localhost:3002/signup" className="w-full">
              <Button 
                className="w-full bg-primary hover:bg-accent text-primary-foreground rounded-full h-12 text-sm"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Start Legal Research
              </Button>
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
