"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { aiInsights } from "@/lib/mockData";
import {
  Brain,
  AlertTriangle,
  CheckCircle2,
  Info,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const iconMap = {
  warning: AlertTriangle,
  positive: CheckCircle2,
  info: Info,
} as const;

const colorMap = {
  warning: { text: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)", border: "rgba(245, 158, 11, 0.2)" },
  positive: { text: "#00d4aa", bg: "rgba(0, 212, 170, 0.1)", border: "rgba(0, 212, 170, 0.2)" },
  info: { text: "#3b82f6", bg: "rgba(59, 130, 246, 0.1)", border: "rgba(59, 130, 246, 0.2)" },
} as const;

function useTypingEffect(text: string, speed: number = 18) {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayedText("");
    setIsComplete(false);
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayedText(text.slice(0, i + 1));
        i++;
      } else {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayedText, isComplete };
}

function InsightCard({
  insight,
  index,
  isExpanded,
  onToggle,
}: {
  insight: { type: string; title: string; text: string };
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const iconMap: Record<string, { icon: any; colors: { bg: string; text: string } }> = {
    warning: {
      icon: AlertTriangle,
      colors: { bg: "rgba(245, 158, 11, 0.1)", text: "#f59e0b" },
    },
    negative: {
      icon: AlertTriangle,
      colors: { bg: "rgba(244, 63, 94, 0.1)", text: "#f43f5e" },
    },
    positive: {
      icon: CheckCircle2,
      colors: { bg: "rgba(0, 212, 170, 0.1)", text: "#00d4aa" },
    },
    info: {
      icon: Info,
      colors: { bg: "rgba(59, 130, 246, 0.1)", text: "#3b82f6" },
    },
  };

  const mapResult = iconMap[insight.type?.toLowerCase()] || iconMap.info;
  const { icon: Icon, colors } = mapResult;

  // Derive border color by changing the alpha of the background color
  const borderColor = colors.bg.replace(/(\d+(\.\d+)?)\)$/, (match, p1) => {
    const alpha = parseFloat(p1);
    return `${alpha * 2})`;
  });

  const { displayedText, isComplete } = useTypingEffect(
    isExpanded ? insight.text : "",
    12
  );

  return (
    <motion.div
      className="rounded-xl border cursor-pointer"
      style={{
        backgroundColor: isExpanded ? colors.bg : "rgba(255,255,255,0.02)",
        borderColor: isExpanded ? borderColor : "rgba(255,255,255,0.04)",
      }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 + index * 0.1 }}
      onClick={onToggle}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: colors.bg }}
        >
          <Icon size={14} style={{ color: colors.text }} />
        </div>
        <p className="text-sm font-medium text-text-primary flex-1">
          {insight.title}
        </p>
        {isExpanded ? (
          <ChevronUp size={14} className="text-text-muted" />
        ) : (
          <ChevronDown size={14} className="text-text-muted" />
        )}
      </div>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <p className="px-4 pb-3 text-xs text-text-secondary leading-relaxed">
              {displayedText}
              {!isComplete && (
                <span className="typing-cursor text-accent-teal">|</span>
              )}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

interface AIExplanationPanelProps {
  data?: any;
}

export default function AIExplanationPanel({ data: apiData }: AIExplanationPanelProps) {
  const insights = apiData?.length ? apiData : aiInsights;
  const [expandedIndex, setExpandedIndex] = useState(0);

  return (
    <motion.div
      className="glass-card p-6 flex flex-col gap-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-accent-teal-dim flex items-center justify-center">
            <Brain size={16} className="text-accent-teal" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-wide uppercase text-text-secondary">
              AI Insights
            </h2>
            <p className="text-[11px] text-text-muted flex items-center gap-1">
              <Sparkles size={10} />
              Powered by AI Portfolio Analyser Engine
            </p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full bg-accent-teal-dim text-accent-teal font-medium">
          {insights.length} findings
        </span>
      </div>

      {/* Insights list */}
      <div className="flex flex-col gap-2 overflow-y-auto max-h-[380px] pr-1">
        {insights.map((insight: any, i: number) => (
          <InsightCard
            key={i}
            insight={insight}
            index={i}
            isExpanded={expandedIndex === i}
            onToggle={() =>
              setExpandedIndex((prev) => (prev === i ? -1 : i))
            }
          />
        ))}
      </div>
    </motion.div>
  );
}
