"use client";

import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import CSVUploader from "@/components/CSVUploader";
import ManualInput from "@/components/ManualInput";
import PortfolioPreview from "@/components/PortfolioPreview";
import {
  type PortfolioAsset,
  calculateAllocations,
  demoPortfolio,
  convertToWeights,
} from "@/lib/portfolioUtils";
import { analyzePortfolio } from "@/lib/api";
import {
  Upload,
  Keyboard,
  Sparkles,
  Loader2,
  AlertCircle,
  Play,
  Shield,
  Lock,
  Brain,
} from "lucide-react";

type InputMode = "csv" | "manual";

export default function LandingPage() {
  const router = useRouter();
  const [mode, setMode] = useState<InputMode>("csv");
  const [assets, setAssets] = useState<PortfolioAsset[]>([
    { ticker: "", quantity: 0 },
    { ticker: "", quantity: 0 },
    { ticker: "", quantity: 0 },
  ]);
  const [csvAssets, setCsvAssets] = useState<PortfolioAsset[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [manualErrors, setManualErrors] = useState<Record<number, string>>({});

  // Current working assets
  const currentAssets = mode === "csv" ? csvAssets : assets;

  // Allocations
  const validAssets = useMemo(
    () =>
      currentAssets.filter(
        (a) => a.ticker.trim() !== "" && a.quantity > 0
      ),
    [currentAssets]
  );
  const allocations = useMemo(
    () => calculateAllocations(validAssets),
    [validAssets]
  );

  // Validate manual input
  const validateManualAssets = useCallback((): boolean => {
    const errs: Record<number, string> = {};
    let valid = true;

    assets.forEach((a, i) => {
      if (!a.ticker.trim() && a.quantity <= 0) {
        // Empty row — skip if there are other filled rows
        return;
      }
      if (!a.ticker.trim()) {
        errs[i] = "Ticker is required.";
        valid = false;
      } else if (!/^[A-Z0-9.\-]{1,15}$/.test(a.ticker.trim())) {
        errs[i] = "Invalid ticker (1–15 chars/numbers).";
        valid = false;
      }
      if (a.quantity <= 0) {
        errs[i] = errs[i]
          ? errs[i] + " Quantity must be > 0."
          : "Quantity must be > 0.";
        valid = false;
      }
    });

    // Check at least 1 valid
    const filledCount = assets.filter(
      (a) => a.ticker.trim() !== "" || a.quantity > 0
    ).length;
    if (filledCount === 0) {
      errs[0] = "Add at least one asset.";
      valid = false;
    }

    setManualErrors(errs);
    return valid;
  }, [assets]);

  // Handle analyze
  const handleAnalyze = useCallback(async () => {
    setApiError(null);

    if (mode === "manual") {
      if (!validateManualAssets()) return;
    } else if (csvAssets.length === 0) {
      setApiError("Please upload a CSV file first.");
      return;
    }

    setIsLoading(true);

    try {
      const payload = validAssets.map((a) => ({
        ticker: a.ticker,
        quantity: a.quantity,
      }));
      const result = await analyzePortfolio({ assets: payload });

      // Store API response and redirect to dashboard
      localStorage.setItem("portfolioData", JSON.stringify(result));
      router.push("/dashboard");
    } catch (err) {
      setApiError(
        err instanceof Error ? err.message : "Analysis failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }, [mode, csvAssets, validAssets, validateManualAssets, router]);

  // Handle demo
  const handleDemo = useCallback(async () => {
    setIsLoading(true);
    try {
      const payload = demoPortfolio.map((a) => ({
        ticker: a.ticker,
        quantity: a.quantity,
      }));
      const result = await analyzePortfolio({ assets: payload });
      localStorage.setItem("portfolioData", JSON.stringify(result));
      router.push("/dashboard");
    } catch {
      // Fallback: store raw demo data and redirect anyway
      localStorage.setItem("portfolioData", JSON.stringify(demoPortfolio));
      router.push("/dashboard");
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  return (
    <div className="min-h-screen relative z-10 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
        {/* ─── Hero ─── */}
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-teal-dim border border-accent-teal/20 text-xs text-accent-teal font-medium mb-6">
            <Brain size={12} />
            AI-Powered Portfolio Analysis
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 leading-tight">
            AI Portfolio{" "}
            <span className="bg-gradient-to-r from-accent-teal to-accent-blue bg-clip-text text-transparent">
              Analyser
            </span>
          </h1>
          <p className="text-text-secondary text-base md:text-lg max-w-xl mx-auto leading-relaxed">
            Upload your portfolio and get AI-powered insights on
            diversification, risk, and long-term growth.
          </p>
        </motion.div>

        {/* ─── Input Card ─── */}
        <motion.div
          className="glass-card p-6 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          {/* Tab switcher */}
          <div className="flex p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] mb-6">
            <button
              onClick={() => setMode("csv")}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                mode === "csv"
                  ? "bg-accent-teal/10 text-accent-teal border border-accent-teal/20"
                  : "text-text-muted hover:text-text-secondary border border-transparent"
              }`}
            >
              <Upload size={14} />
              CSV Upload
            </button>
            <button
              onClick={() => setMode("manual")}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                mode === "manual"
                  ? "bg-accent-teal/10 text-accent-teal border border-accent-teal/20"
                  : "text-text-muted hover:text-text-secondary border border-transparent"
              }`}
            >
              <Keyboard size={14} />
              Manual Input
            </button>
          </div>

          {/* Content */}
          <AnimatePresence mode="wait">
            {mode === "csv" ? (
              <motion.div
                key="csv"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
              >
                <CSVUploader onParsed={setCsvAssets} />
              </motion.div>
            ) : (
              <motion.div
                key="manual"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <ManualInput
                  assets={assets}
                  onChange={(a) => {
                    setAssets(a);
                    setManualErrors({});
                  }}
                  errors={manualErrors}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* ─── Preview ─── */}
        <AnimatePresence>
          {allocations.length > 0 && (
            <motion.div
              className="mb-6"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <PortfolioPreview allocations={allocations} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── API Error ─── */}
        <AnimatePresence>
          {apiError && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="flex items-center gap-2 text-sm text-negative px-4 py-3 rounded-xl bg-negative/[0.06] border border-negative/20 mb-6"
            >
              <AlertCircle size={16} className="flex-shrink-0" />
              <span>{apiError}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Action Buttons ─── */}
        <motion.div
          className="flex flex-col sm:flex-row gap-3 mb-8"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <button
            onClick={handleAnalyze}
            disabled={isLoading}
            className="flex-1 flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-accent-teal to-accent-blue text-white font-semibold text-sm transition-all hover:shadow-lg hover:shadow-accent-teal/20 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles size={16} />
                Analyze Portfolio
              </>
            )}
          </button>

          <button
            onClick={handleDemo}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-white/[0.04] border border-white/[0.1] text-text-secondary font-medium text-sm transition-all hover:bg-white/[0.08] hover:text-text-primary hover:border-white/[0.15] disabled:opacity-50"
          >
            <Play size={14} />
            Try Demo Portfolio
          </button>
        </motion.div>
      </main>

      {/* ─── Disclaimer Footer ─── */}
      <footer className="max-w-3xl mx-auto w-full px-6 pb-8">
        <motion.div
          className="flex flex-col items-center gap-3 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <div className="flex items-center gap-1.5">
              <Shield size={12} className="text-accent-teal" />
              <span>Secure Analysis</span>
            </div>
            <span className="w-1 h-1 rounded-full bg-text-muted/40" />
            <div className="flex items-center gap-1.5">
              <Lock size={12} className="text-accent-teal" />
              <span>No Data Stored</span>
            </div>
          </div>
          <p className="text-[11px] text-text-muted/70 max-w-md">
            We do not store your financial data. All analysis is done
            securely.
          </p>
          <p className="text-[10px] text-text-muted/40 mt-1">
            © 2026 AI Portfolio Analyser
          </p>
        </motion.div>
      </footer>
    </div>
  );
}
