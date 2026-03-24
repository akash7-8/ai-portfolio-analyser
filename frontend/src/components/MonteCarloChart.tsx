"use client";

import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { monteCarloData } from "@/lib/mockData";
import { LineChart } from "lucide-react";

interface MCTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

function MCTooltip({ active, payload, label }: MCTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-bg-secondary/95 backdrop-blur-md border border-white/10 rounded-xl px-4 py-3 shadow-2xl min-w-[180px]">
      <p className="text-xs text-text-muted mb-2 font-medium">Month {label?.replace("M", "")}</p>
      {payload.map((p) => (
        <div
          key={p.name}
          className="flex items-center justify-between gap-4 text-xs mb-1"
        >
          <span className="text-text-secondary">{p.name}</span>
          <span className="font-semibold" style={{ color: p.color }}>
            ${(p.value / 1000).toFixed(0)}K
          </span>
        </div>
      ))}
    </div>
  );
}

function formatYAxis(value: number) {
  return `$${(value / 1_000_000).toFixed(1)}M`;
}

interface MonteCarloChartProps {
  data?: any;
}

export default function MonteCarloChart({ data: apiData }: MonteCarloChartProps) {
  const chartData = apiData?.length ? apiData : monteCarloData;
  return (
    <motion.div
      className="glass-card p-6 flex flex-col gap-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-wide uppercase text-text-secondary">
            Monte Carlo Simulation
          </h2>
          <p className="text-xs text-text-muted mt-1">
            10,000 paths · 24-month projection
          </p>
        </div>
        <LineChart size={18} className="text-text-muted" />
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs">
        {[
          { label: "P90 (Bull)", color: "#00d4aa" },
          { label: "P50 (Base)", color: "#3b82f6" },
          { label: "P10 (Bear)", color: "#f43f5e" },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: l.color }}
            />
            <span className="text-text-muted">{l.label}</span>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id="gradP90" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00d4aa" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#00d4aa" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradP75" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00d4aa" stopOpacity={0.08} />
                <stop offset="100%" stopColor="#00d4aa" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradP50" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradP25" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.06} />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradP10" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.06} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
              tickLine={false}
              interval={3}
            />
            <YAxis
              tickFormatter={formatYAxis}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip content={<MCTooltip />} />
            <Area
              type="monotone"
              dataKey="p90"
              name="P90"
              stroke="#00d4aa"
              strokeWidth={1.5}
              fill="url(#gradP90)"
              dot={false}
              animationDuration={1500}
            />
            <Area
              type="monotone"
              dataKey="p75"
              name="P75"
              stroke="#00d4aa"
              strokeWidth={1}
              strokeOpacity={0.4}
              fill="url(#gradP75)"
              dot={false}
              animationDuration={1500}
            />
            <Area
              type="monotone"
              dataKey="p50"
              name="P50"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#gradP50)"
              dot={false}
              animationDuration={1500}
            />
            <Area
              type="monotone"
              dataKey="p25"
              name="P25"
              stroke="#f59e0b"
              strokeWidth={1}
              strokeOpacity={0.4}
              fill="url(#gradP25)"
              dot={false}
              animationDuration={1500}
            />
            <Area
              type="monotone"
              dataKey="p10"
              name="P10"
              stroke="#f43f5e"
              strokeWidth={1.5}
              fill="url(#gradP10)"
              dot={false}
              animationDuration={1500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
