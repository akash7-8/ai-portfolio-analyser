"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { rebalanceDefaults } from "@/lib/mockData";
import { rebalancePortfolio } from "@/lib/api";
import { Sliders, ArrowRight, Loader2, Play, AlertCircle, CheckCircle2 } from "lucide-react";

interface Allocation {
  name: string;
  current: number;
  target: number;
  color: string;
}

export default function RebalanceSimulator() {
  const [allocations, setAllocations] = useState<Allocation[]>(
    () => rebalanceDefaults.map((d) => ({ ...d }))
  );
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [rebalanceResult, setRebalanceResult] = useState<any>(null);

  const totalTarget = allocations.reduce((sum, a) => sum + a.target, 0);

  const handleSliderChange = useCallback(
    (index: number, newValue: number) => {
      setAllocations((prev) => {
        const next = prev.map((a) => ({ ...a }));
        next[index].target = newValue;
        return next;
      });
    },
    []
  );

  // Simple expected return & risk calculation
  const expectedReturn = allocations.reduce((sum, a) => {
    const returnRates: Record<string, number> = {
      Stocks: 9.5,
      Bonds: 4.2,
      "Real Estate": 7.1,
      Crypto: 15.0,
      Commodities: 5.5,
    };
    return sum + (a.target / 100) * (returnRates[a.name] || 6);
  }, 0);

  const riskLevel = allocations.reduce((sum, a) => {
    const riskScores: Record<string, number> = {
      Stocks: 7,
      Bonds: 2,
      "Real Estate": 5,
      Crypto: 9.5,
      Commodities: 4,
    };
    return sum + (a.target / 100) * (riskScores[a.name] || 5);
  }, 0);

  const riskLabel =
    riskLevel >= 7 ? "High" : riskLevel >= 4.5 ? "Moderate" : "Low";
  const riskColor =
    riskLevel >= 7 ? "#f43f5e" : riskLevel >= 4.5 ? "#f59e0b" : "#00d4aa";

  // Handle rebalance API call
  const handleRebalance = useCallback(async () => {
    setApiError(null);
    setRebalanceResult(null);
    setIsLoading(true);

    try {
      const weights = allocations.map((a) => ({
        ticker: a.name,
        weight: a.target / 100,
      }));
      const result = await rebalancePortfolio({ assets: weights });
      setRebalanceResult(result);
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : "Rebalance simulation failed."
      );
    } finally {
      setIsLoading(false);
    }
  }, [allocations]);

  return (
    <motion.div
      className="glass-card p-6 flex flex-col gap-5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide uppercase text-text-secondary">
          Rebalancing Simulator
        </h2>
        <Sliders size={18} className="text-text-muted" />
      </div>

      {/* Sliders */}
      <div className="flex flex-col gap-4">
        {allocations.map((alloc, i) => (
          <motion.div
            key={alloc.name}
            initial={{ opacity: 0, x: -15 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 + i * 0.08 }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: alloc.color }}
                />
                <span className="text-sm text-text-secondary font-medium">
                  {alloc.name}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-text-muted">{alloc.current}%</span>
                <ArrowRight size={12} className="text-text-muted" />
                <span
                  className="font-semibold"
                  style={{
                    color:
                      alloc.target !== alloc.current
                        ? alloc.color
                        : "var(--color-text-secondary)",
                  }}
                >
                  {alloc.target}%
                </span>
              </div>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={alloc.target}
              onChange={(e) =>
                handleSliderChange(i, parseInt(e.target.value, 10))
              }
              className="w-full"
              style={
                {
                  "--tw-accent": alloc.color,
                  background: `linear-gradient(to right, ${alloc.color} 0%, ${alloc.color} ${alloc.target}%, rgba(255,255,255,0.08) ${alloc.target}%, rgba(255,255,255,0.08) 100%)`,
                } as React.CSSProperties
              }
            />
          </motion.div>
        ))}
      </div>

      {/* Summary bar */}
      <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.04]">
        <div className="text-center">
          <p className="text-[11px] text-text-muted">Total</p>
          <p
            className={`text-sm font-bold ${totalTarget === 100 ? "text-positive" : "text-negative"}`}
          >
            {totalTarget}%
          </p>
        </div>
        <div className="w-px h-8 bg-white/[0.06]" />
        <div className="text-center">
          <p className="text-[11px] text-text-muted">Exp. Return</p>
          <p className="text-sm font-bold text-accent-teal">
            {expectedReturn.toFixed(1)}%
          </p>
        </div>
        <div className="w-px h-8 bg-white/[0.06]" />
        <div className="text-center">
          <p className="text-[11px] text-text-muted">Risk Level</p>
          <p className="text-sm font-bold" style={{ color: riskColor }}>
            {riskLabel}
          </p>
        </div>
      </div>

      {/* Run Simulation button */}
      <button
        onClick={handleRebalance}
        disabled={isLoading || totalTarget !== 100}
        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-accent-teal to-accent-blue text-white font-semibold text-sm transition-all hover:shadow-lg hover:shadow-accent-teal/20 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            Simulating...
          </>
        ) : (
          <>
            <Play size={14} />
            Run Simulation
          </>
        )}
      </button>

      {/* API Error */}
      <AnimatePresence>
        {apiError && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 text-xs text-negative px-3 py-2 rounded-xl bg-negative/[0.06] border border-negative/20"
          >
            <AlertCircle size={12} className="flex-shrink-0" />
            <span>{apiError}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rebalance Result */}
      <AnimatePresence>
        {rebalanceResult && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="flex items-start gap-2 text-xs text-positive px-3 py-2.5 rounded-xl bg-positive/[0.06] border border-positive/20"
          >
            <CheckCircle2 size={12} className="flex-shrink-0 mt-0.5" />
            <span>Simulation complete. Results updated.</span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
