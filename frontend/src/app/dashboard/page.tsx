"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import PortfolioScoreCard from "@/components/PortfolioScoreCard";
import DiversificationGauge from "@/components/DiversificationGauge";
import SectorExposure from "@/components/SectorExposure";
import MonteCarloChart from "@/components/MonteCarloChart";
import RebalanceSimulator from "@/components/RebalanceSimulator";
import AIExplanationPanel from "@/components/AIExplanationPanel";
import { Shield, Lock } from "lucide-react";

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const stored = localStorage.getItem("portfolioData");
    if (stored) setData(JSON.parse(stored));
  }, []);

  return (
    <div className="min-h-screen relative z-10 flex flex-col">
      <Navbar showUserActions />

      {/* ─── Main Content ─── */}
      <main className="flex-1 max-w-[1440px] mx-auto w-full px-6 py-6">
        {/* Page title */}
        <motion.div
          className="mb-6"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h2 className="text-xl font-bold">Dashboard Overview</h2>
          <p className="text-sm text-text-muted mt-1">
            Real-time AI analysis of your portfolio · Last updated 2 min ago
          </p>
        </motion.div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Row 1 */}
          <PortfolioScoreCard score={data?.portfolio_score} />
          <DiversificationGauge value={data?.diversification_score} />

          {/* Row 2 */}
          <SectorExposure data={data?.sector_exposure} />
          <MonteCarloChart data={data?.simulation} />

          {/* Row 3 */}
          <RebalanceSimulator />
          <AIExplanationPanel data={data?.explanation} />
        </div>
      </main>

      {/* ─── Footer ─── */}
      <footer className="max-w-[1440px] mx-auto w-full px-6 py-6 mt-4">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-text-muted">
          <div className="flex items-center gap-4">
            <p>© 2026 AI Portfolio Analyser</p>
            <p className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-positive animate-pulse" />
              All systems operational
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Shield size={11} className="text-accent-teal" />
              <span>Secure</span>
            </div>
            <span className="w-1 h-1 rounded-full bg-text-muted/40" />
            <div className="flex items-center gap-1.5">
              <Lock size={11} className="text-accent-teal" />
              <span>We do not store your financial data. All analysis is done securely.</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
