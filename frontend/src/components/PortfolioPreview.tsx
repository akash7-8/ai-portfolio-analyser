"use client";

import { motion } from "framer-motion";
import type { PortfolioAllocation } from "@/lib/portfolioUtils";
import { BarChart3 } from "lucide-react";

interface PortfolioPreviewProps {
  allocations: PortfolioAllocation[];
}

const barColors = [
  "#3b82f6",
  "#00d4aa",
  "#8b5cf6",
  "#f59e0b",
  "#f43f5e",
  "#6366f1",
  "#ec4899",
  "#14b8a6",
  "#e879f9",
  "#fb923c",
];

export default function PortfolioPreview({
  allocations,
}: PortfolioPreviewProps) {
  if (allocations.length === 0) return null;

  const totalQty = allocations.reduce((sum, a) => sum + a.quantity, 0);

  return (
    <motion.div
      className="glass-card p-5"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-accent-teal" />
          <h3 className="text-sm font-semibold text-text-primary">
            Portfolio Preview
          </h3>
        </div>
        <span className="text-xs text-text-muted">
          {allocations.length} asset{allocations.length !== 1 ? "s" : ""} ·{" "}
          {totalQty} total shares
        </span>
      </div>

      {/* Allocation bar */}
      <div className="flex h-3 rounded-full overflow-hidden mb-4">
        {allocations.map((a, i) => (
          <motion.div
            key={a.ticker}
            initial={{ width: 0 }}
            animate={{ width: `${a.allocation}%` }}
            transition={{ duration: 0.6, delay: i * 0.05 }}
            className="h-full first:rounded-l-full last:rounded-r-full"
            style={{ backgroundColor: barColors[i % barColors.length] }}
            title={`${a.ticker}: ${a.allocation}%`}
          />
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="text-left text-xs text-text-muted font-medium py-2 pr-4">
                Ticker
              </th>
              <th className="text-right text-xs text-text-muted font-medium py-2 px-4">
                Quantity
              </th>
              <th className="text-right text-xs text-text-muted font-medium py-2 pl-4">
                Allocation
              </th>
            </tr>
          </thead>
          <tbody>
            {allocations.map((a, i) => (
              <motion.tr
                key={a.ticker}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 + i * 0.03 }}
                className="border-b border-white/[0.03] last:border-none"
              >
                <td className="py-2.5 pr-4">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{
                        backgroundColor: barColors[i % barColors.length],
                      }}
                    />
                    <span className="font-mono font-semibold text-text-primary">
                      {a.ticker}
                    </span>
                  </div>
                </td>
                <td className="py-2.5 px-4 text-right text-text-secondary">
                  {a.quantity.toLocaleString()}
                </td>
                <td className="py-2.5 pl-4 text-right font-medium">
                  <span
                    style={{
                      color: barColors[i % barColors.length],
                    }}
                  >
                    {a.allocation}%
                  </span>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
