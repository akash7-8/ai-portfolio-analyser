"use client";

import { motion } from "framer-motion";
import { portfolioMetrics } from "@/lib/mockData";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Shield,
  Zap,
} from "lucide-react";

interface PortfolioScoreCardProps {
  score?: any;
}

export default function PortfolioScoreCard({ score: apiData }: PortfolioScoreCardProps) {
  const {
    score,
    totalValue,
    sharpeRatio,
    volatility,
    beta,
    alpha,
  } = { ...portfolioMetrics, ...(apiData || {}) };

  const dailyChangePct = apiData?.dailyChangePct ?? portfolioMetrics.dailyChange;
  const dailyChangeDollar = apiData?.dailyChangeDollar ?? portfolioMetrics.dailyChangeAmount;

  const isPositive = dailyChangePct >= 0;
  const sign = dailyChangePct >= 0 ? "+" : "";

  // SVG arc for score ring
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Score color
  const scoreColor =
    score >= 80
      ? "#00d4aa"
      : score >= 60
        ? "#f59e0b"
        : "#f43f5e";

  const metrics = [
    { label: "Sharpe Ratio", value: sharpeRatio.toFixed(2), icon: Zap },
    { label: "Volatility", value: `${volatility}%`, icon: Activity },
    { label: "Beta", value: beta.toFixed(2), icon: BarChart3 },
    { label: "Alpha", value: `${alpha > 0 ? "+" : ""}${alpha}%`, icon: Shield },
  ];

  return (
    <motion.div
      className="glass-card p-6 flex flex-col gap-5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide uppercase text-text-secondary">
          Portfolio Score
        </h2>
        <span className="text-xs px-2.5 py-1 rounded-full bg-accent-teal-dim text-accent-teal font-medium">
          AI Rated
        </span>
      </div>

      {/* Score ring + value */}
      <div className="flex items-center gap-6">
        <div className="relative flex-shrink-0">
          <svg width="160" height="160" className="score-ring -rotate-90">
            {/* Background ring */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="10"
            />
            {/* Score arc */}
            <motion.circle
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke={scoreColor}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 1.5, ease: "easeOut" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span
              className="text-4xl font-bold"
              style={{ color: scoreColor }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              {score}
            </motion.span>
            <span className="text-xs text-text-muted mt-0.5">/ 100</span>
          </div>
        </div>

        <div className="flex flex-col gap-3 flex-1 min-w-0">
          <div>
            <p className="text-xs text-text-muted mb-1">Total Portfolio Value</p>
            <p className="text-2xl font-bold tracking-tight">
              ${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div
            className={`flex items-center gap-1.5 text-sm font-medium ${isPositive ? "text-positive" : "text-negative"}`}
          >
            {isPositive ? (
              <TrendingUp size={16} />
            ) : (
              <TrendingDown size={16} />
            )}
            <span>
              {sign}{dailyChangePct.toFixed(2)}%
            </span>
            <span className="text-text-muted text-xs">
              (${Math.abs(dailyChangeDollar).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })})
            </span>
          </div>
        </div>
      </div>

      {/* Mini metric grid */}
      <div className="grid grid-cols-2 gap-3 mt-auto">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.04]"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 + i * 0.1 }}
          >
            <m.icon size={14} className="text-text-muted flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-[11px] text-text-muted truncate">{m.label}</p>
              <p className="text-sm font-semibold">{m.value}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
