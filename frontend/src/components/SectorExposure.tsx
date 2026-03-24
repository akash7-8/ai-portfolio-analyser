"use client";

import { motion } from "framer-motion";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { sectorExposure } from "@/lib/mockData";
import { PieChart as PieIcon } from "lucide-react";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    payload: { color: string };
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-bg-secondary/95 backdrop-blur-md border border-white/10 rounded-xl px-4 py-3 shadow-2xl">
      <p className="text-sm font-semibold text-text-primary flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: d.payload.color }}
        />
        {d.name}
      </p>
      <p className="text-lg font-bold mt-1" style={{ color: d.payload.color }}>
        {d.value}%
      </p>
    </div>
  );
}

interface LabelProps {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  name: string;
  value: number;
}

function renderLabel({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  name,
  value,
}: LabelProps) {
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 28;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="#94a3b8"
      textAnchor={x > cx ? "start" : "end"}
      dominantBaseline="central"
      fontSize={11}
      fontWeight={500}
    >
      {name} ({value}%)
    </text>
  );
}

interface SectorExposureProps {
  data?: any;
}

export default function SectorExposure({ data: apiData }: SectorExposureProps) {
  const chartData = apiData?.length ? apiData : sectorExposure;
  return (
    <motion.div
      className="glass-card p-6 flex flex-col gap-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide uppercase text-text-secondary">
          Sector Exposure
        </h2>
        <PieIcon size={18} className="text-text-muted" />
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={95}
              paddingAngle={3}
              dataKey="value"
              label={renderLabel}
              animationBegin={300}
              animationDuration={1200}
              animationEasing="ease-out"
            >
              {chartData.map((entry: any, index: number) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  stroke="transparent"
                  style={{
                    filter: `drop-shadow(0 0 6px ${entry.color}40)`,
                  }}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {chartData.map((s: any) => (
          <div key={s.name} className="flex items-center gap-1.5 text-xs">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-text-muted">{s.name}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
