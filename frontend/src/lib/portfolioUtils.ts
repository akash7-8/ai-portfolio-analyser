// ============================================================
// Portfolio Utilities — CSV parsing, demo data, API helpers
// ============================================================

export interface PortfolioAsset {
  ticker: string;
  quantity: number;
}

export interface PortfolioAllocation extends PortfolioAsset {
  allocation: number; // percentage
}

// ─── Demo Portfolio ───
export const demoPortfolio: PortfolioAsset[] = [
  { ticker: "AAPL", quantity: 50 },
  { ticker: "MSFT", quantity: 35 },
  { ticker: "GOOGL", quantity: 20 },
  { ticker: "AMZN", quantity: 15 },
  { ticker: "JNJ", quantity: 40 },
  { ticker: "JPM", quantity: 30 },
  { ticker: "XOM", quantity: 25 },
  { ticker: "PG", quantity: 45 },
  { ticker: "NVDA", quantity: 10 },
  { ticker: "BND", quantity: 100 },
];

// ─── CSV Parsing ───
export interface CSVParseResult {
  success: boolean;
  data: PortfolioAsset[];
  error?: string;
}

export function parsePortfolioCSV(csvText: string): CSVParseResult {
  try {
    const lines = csvText
      .trim()
      .split(/\r?\n/)
      .filter((line) => line.trim() !== "");

    if (lines.length < 2) {
      return { success: false, data: [], error: "CSV must have a header row and at least one data row." };
    }

    // Parse header
    const header = lines[0].toLowerCase().split(",").map((h) => h.trim());
    const tickerIdx = header.findIndex((h) =>
      ["ticker", "symbol", "stock", "asset"].includes(h)
    );
    const qtyIdx = header.findIndex((h) =>
      ["quantity", "qty", "shares", "amount", "units"].includes(h)
    );

    if (tickerIdx === -1 || qtyIdx === -1) {
      return {
        success: false,
        data: [],
        error: "CSV must contain 'Ticker' and 'Quantity' columns.",
      };
    }

    const assets: PortfolioAsset[] = [];
    const errors: string[] = [];

    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(",").map((c) => c.trim());
      const ticker = cols[tickerIdx]?.toUpperCase();
      const quantity = parseFloat(cols[qtyIdx]);

      if (!ticker || ticker.length === 0) {
        errors.push(`Row ${i + 1}: Missing ticker.`);
        continue;
      }
      if (!/^[A-Z0-9.\-]{1,15}$/.test(ticker)) {
        errors.push(`Row ${i + 1}: Invalid ticker "${ticker}".`);
        continue;
      }
      if (isNaN(quantity) || quantity <= 0) {
        errors.push(`Row ${i + 1}: Invalid quantity for ${ticker}.`);
        continue;
      }

      assets.push({ ticker, quantity });
    }

    if (assets.length === 0) {
      return {
        success: false,
        data: [],
        error: errors.length > 0 ? errors.join(" ") : "No valid assets found in CSV.",
      };
    }

    return { success: true, data: assets };
  } catch {
    return { success: false, data: [], error: "Failed to parse CSV file." };
  }
}

// ─── Allocation Calculation ───
export function calculateAllocations(
  assets: PortfolioAsset[]
): PortfolioAllocation[] {
  const totalQty = assets.reduce((sum, a) => sum + a.quantity, 0);
  if (totalQty === 0) return assets.map((a) => ({ ...a, allocation: 0 }));

  return assets.map((a) => ({
    ...a,
    allocation: parseFloat(((a.quantity / totalQty) * 100).toFixed(1)),
  }));
}

// ─── Weight Conversion (for backend API) ───
export function convertToWeights(data: any[]) {
  const total = data.reduce((sum: number, item: any) => sum + item.quantity, 0);

  return data.map((item: any) => ({
    ticker: item.ticker,
    weight: item.quantity / total,
  }));
}

// ─── API (re-exported from api.ts) ───
export { analyzePortfolio, rebalancePortfolio } from "./api";

// ─── Sample CSV Content ───
export const sampleCSVContent = `Ticker,Quantity
AAPL,50
MSFT,35
GOOGL,20
AMZN,15
JNJ,40
JPM,30
XOM,25
PG,45
NVDA,10
BND,100`;
