"use client";

import { motion } from "framer-motion";
import { diversification } from "@/lib/mockData";
import { Gauge } from "lucide-react";

interface DiversificationGaugeProps {
  value?: any;
}

export default function DiversificationGauge({ value: apiData }: DiversificationGaugeProps) {
  const { score, assetClasses } = { ...diversification, ...(apiData || {}) };

  // Semi-circle arc
  const radius = 80;
  const halfCircumference = Math.PI * radius;
  const offset = halfCircumference - (score / 100) * halfCircumference;

  const scoreLabel =
    score >= 80
      ? "Excellent"
      : score >= 60
        ? "Good"
        : score >= 40
          ? "Fair"
          : "Poor";

  const scoreColor =
    score >= 80
      ? "#00d4aa"
      : score >= 60
        ? "#f59e0b"
        : "#f43f5e";

  return (
    <motion.div
      className="glass-card p-6 flex flex-col gap-5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide uppercase text-text-secondary">
          Diversification
        </h2>
        <Gauge size={18} className="text-text-muted" />
      </div>

      {/* Gauge */}
      <div className="flex justify-center">
        <div className="relative">
          <svg width="200" height="120" viewBox="0 0 200 120">
            {/* Track */}
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="12"
              strokeLinecap="round"
            />
            {/* Fill */}
            <motion.path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              stroke={scoreColor}
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={halfCircumference}
              initial={{ strokeDashoffset: halfCircumference }}
              animate={{ strokeDashoffset: offset }}
              transition={{ duration: 1.5, ease: "easeOut", delay: 0.3 }}
              style={{
                filter: `drop-shadow(0 0 8px ${scoreColor}50)`,
              }}
            />
          </svg>
          {/* Score text */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
            <motion.p
              className="text-3xl font-bold"
              style={{ color: scoreColor }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1 }}
            >
              {score}%
            </motion.p>
            <p className="text-xs text-text-muted mt-0.5">{scoreLabel}</p>
          </div>
        </div>
      </div>

      {/* Asset class chips */}
      <div className="flex flex-wrap gap-2 mt-auto">
        {assetClasses.map((ac: any, i: number) => (
          <motion.div
            key={ac.name}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.04] text-xs"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.6 + i * 0.08 }}
          >
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: ac.color }}
            />
            <span className="text-text-secondary">{ac.name}</span>
            <span className="font-semibold text-text-primary">{ac.pct ?? ac.value}%</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
