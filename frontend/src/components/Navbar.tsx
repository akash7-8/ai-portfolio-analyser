"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Brain, Bell, ChevronDown } from "lucide-react";

interface NavbarProps {
  showUserActions?: boolean;
}

export default function Navbar({ showUserActions = false }: NavbarProps) {
  return (
    <motion.header
      className="sticky top-0 z-50 backdrop-blur-xl bg-bg-primary/70 border-b border-white/[0.06]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="max-w-[1440px] mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-teal to-accent-blue flex items-center justify-center transition-transform group-hover:scale-105">
            <Brain size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight">
              AI Portfolio<span className="text-accent-teal"> Analyser</span>
            </h1>
            <p className="text-[10px] text-text-muted -mt-0.5">
              AI-Powered Analysis
            </p>
          </div>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-4">
          {showUserActions && (
            <>
              <button className="relative p-2 rounded-xl hover:bg-white/[0.04] transition-colors">
                <Bell size={18} className="text-text-muted" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-accent-teal" />
              </button>
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-white/[0.04] transition-colors">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent-purple to-accent-blue flex items-center justify-center text-xs font-bold text-white">
                  JD
                </div>
                <ChevronDown size={14} className="text-text-muted" />
              </button>
            </>
          )}
          {!showUserActions && (
            <Link
              href="/dashboard"
              className="text-xs px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-text-secondary hover:bg-white/[0.08] hover:text-text-primary transition-all font-medium"
            >
              View Dashboard →
            </Link>
          )}
        </div>
      </div>
    </motion.header>
  );
}
