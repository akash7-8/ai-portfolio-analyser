// ============================================================
// Mock Data for AI Portfolio Analyzer Dashboard
// ============================================================

export const portfolioMetrics = {
  score: 82,
  totalValue: 1_247_832.45,
  dailyChange: 2.34,
  dailyChangeAmount: 28_541.12,
  sharpeRatio: 1.87,
  volatility: 12.4,
  beta: 0.92,
  alpha: 3.2,
  maxDrawdown: -8.7,
  ytdReturn: 18.6,
};

export const diversification = {
  score: 74,
  assetClasses: [
    { name: "US Equities", pct: 42, color: "#3b82f6" },
    { name: "Int'l Equities", pct: 18, color: "#8b5cf6" },
    { name: "Bonds", pct: 20, color: "#00d4aa" },
    { name: "Real Estate", pct: 8, color: "#f59e0b" },
    { name: "Crypto", pct: 7, color: "#f43f5e" },
    { name: "Commodities", pct: 5, color: "#6366f1" },
  ],
};

export const sectorExposure = [
  { name: "Technology", value: 28, color: "#3b82f6" },
  { name: "Healthcare", value: 18, color: "#00d4aa" },
  { name: "Financials", value: 15, color: "#8b5cf6" },
  { name: "Energy", value: 10, color: "#f59e0b" },
  { name: "Consumer", value: 12, color: "#f43f5e" },
  { name: "Industrials", value: 9, color: "#6366f1" },
  { name: "Real Estate", value: 8, color: "#ec4899" },
];

// Monte Carlo simulation paths (simplified: 5 percentile bands over 12 months)
function generateMonteCarlo() {
  const months = 24;
  const startValue = 1_247_832;
  const data = [];

  for (let i = 0; i <= months; i++) {
    const t = i / months;
    const drift = startValue * (1 + 0.08 * t); // 8% annual drift
    data.push({
      month: i,
      label: `M${i}`,
      p10: Math.round(drift * (0.82 + 0.03 * Math.sin(i * 0.5))),
      p25: Math.round(drift * (0.91 + 0.02 * Math.sin(i * 0.7))),
      p50: Math.round(drift * (1.0 + 0.01 * Math.sin(i * 0.3))),
      p75: Math.round(drift * (1.09 + 0.02 * Math.sin(i * 0.4))),
      p90: Math.round(drift * (1.18 + 0.03 * Math.sin(i * 0.6))),
    });
  }
  return data;
}
export const monteCarloData = generateMonteCarlo();

export const rebalanceDefaults = [
  { name: "Stocks", current: 60, target: 55, color: "#3b82f6" },
  { name: "Bonds", current: 20, target: 25, color: "#00d4aa" },
  { name: "Real Estate", current: 8, target: 10, color: "#f59e0b" },
  { name: "Crypto", current: 7, target: 5, color: "#f43f5e" },
  { name: "Commodities", current: 5, target: 5, color: "#8b5cf6" },
];

export const aiInsights = [
  {
    type: "warning" as const,
    title: "High Tech Concentration",
    text: "Your portfolio has 28% exposure to the technology sector, which is above the recommended 20% threshold. Consider reducing FAANG positions by 5-8% to mitigate sector-specific risk.",
  },
  {
    type: "positive" as const,
    title: "Strong Risk-Adjusted Returns",
    text: "Your Sharpe ratio of 1.87 indicates excellent risk-adjusted performance. This is in the top 15% of similar portfolios analyzed by our AI engine.",
  },
  {
    type: "info" as const,
    title: "Rebalancing Opportunity",
    text: "Bond allocation has drifted 5% below target due to recent equity appreciation. Our Monte Carlo analysis suggests rebalancing would reduce max drawdown by ~2.1% while maintaining expected returns.",
  },
  {
    type: "positive" as const,
    title: "Diversification Improving",
    text: "Adding international equities last quarter improved your diversification score from 68 to 74. Consider adding emerging market exposure for further improvement.",
  },
  {
    type: "warning" as const,
    title: "Crypto Volatility Alert",
    text: "Cryptocurrency holdings contributed 34% of portfolio volatility despite being only 7% of value. The AI recommends a 2% reduction to optimize risk/return profile.",
  },
];
