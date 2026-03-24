"use client";

import { useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, AlertCircle } from "lucide-react";
import type { PortfolioAsset } from "@/lib/portfolioUtils";

interface ManualInputProps {
  assets: PortfolioAsset[];
  onChange: (assets: PortfolioAsset[]) => void;
  errors: Record<number, string>;
}

export default function ManualInput({
  assets,
  onChange,
  errors,
}: ManualInputProps) {
  const addRow = useCallback(() => {
    onChange([...assets, { ticker: "", quantity: 0 }]);
  }, [assets, onChange]);

  const removeRow = useCallback(
    (index: number) => {
      onChange(assets.filter((_, i) => i !== index));
    },
    [assets, onChange]
  );

  const updateField = useCallback(
    (index: number, field: keyof PortfolioAsset, value: string | number) => {
      const updated = assets.map((a, i) =>
        i === index ? { ...a, [field]: value } : a
      );
      onChange(updated);
    },
    [assets, onChange]
  );

  return (
    <div className="flex flex-col gap-3">
      {/* Header labels */}
      <div className="grid grid-cols-[1fr_120px_36px] gap-3 px-1">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wide">
          Ticker
        </span>
        <span className="text-xs text-text-muted font-medium uppercase tracking-wide">
          Quantity
        </span>
        <span />
      </div>

      {/* Rows */}
      <div className="flex flex-col gap-2">
        <AnimatePresence initial={false}>
          {assets.map((asset, i) => (
            <motion.div
              key={i}
              layout
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 15, height: 0 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col gap-1"
            >
              <div className="grid grid-cols-[1fr_120px_36px] gap-3">
                <input
                  type="text"
                  placeholder="e.g. AAPL"
                  value={asset.ticker}
                  onChange={(e) =>
                    updateField(i, "ticker", e.target.value.toUpperCase())
                  }
                  maxLength={15}
                  className={`w-full px-3 py-2.5 rounded-xl text-sm bg-white/[0.04] border outline-none transition-all font-mono placeholder:text-text-muted/50 focus:ring-1 ${
                    errors[i]
                      ? "border-negative/40 focus:ring-negative/30"
                      : "border-white/[0.08] focus:border-accent-teal/50 focus:ring-accent-teal/20"
                  }`}
                />
                <input
                  type="number"
                  placeholder="0"
                  min={1}
                  value={asset.quantity || ""}
                  onChange={(e) =>
                    updateField(i, "quantity", parseInt(e.target.value) || 0)
                  }
                  className={`w-full px-3 py-2.5 rounded-xl text-sm bg-white/[0.04] border outline-none transition-all placeholder:text-text-muted/50 focus:ring-1 ${
                    errors[i]
                      ? "border-negative/40 focus:ring-negative/30"
                      : "border-white/[0.08] focus:border-accent-teal/50 focus:ring-accent-teal/20"
                  }`}
                />
                <button
                  onClick={() => removeRow(i)}
                  disabled={assets.length <= 1}
                  className="w-9 h-10 rounded-xl flex items-center justify-center text-text-muted hover:text-negative hover:bg-negative/[0.06] transition-all disabled:opacity-20 disabled:cursor-not-allowed"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              {/* Row-level error */}
              <AnimatePresence>
                {errors[i] && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex items-center gap-1.5 text-[11px] text-negative px-1"
                  >
                    <AlertCircle size={10} />
                    <span>{errors[i]}</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Add row button */}
      <button
        onClick={addRow}
        className="flex items-center gap-2 text-xs text-text-muted hover:text-accent-teal transition-colors self-start px-1 py-1"
      >
        <Plus size={14} />
        Add Asset
      </button>
    </div>
  );
}
