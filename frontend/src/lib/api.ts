// ============================================================
// API Layer — Backend communication (http://127.0.0.1:8000)
// ============================================================

const BASE_URL = "http://127.0.0.1:8000";

export async function analyzePortfolio(data: any) {
  const res = await fetch(`${BASE_URL}/analyze_portfolio`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => "");
    let errorData = null;
    try { errorData = JSON.parse(errorText); } catch {}
    
    console.error(`Backend Error /analyze_portfolio [${res.status}]:`, errorText);
    throw new Error(
      errorData?.detail || errorData?.message || `Analyze API failed: HTTP ${res.status}`
    );
  }
  return res.json();
}

export async function rebalancePortfolio(data: any) {
  const res = await fetch(`${BASE_URL}/rebalance_simulation`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => "");
    let errorData = null;
    try { errorData = JSON.parse(errorText); } catch {}

    console.error(`Backend Error /rebalance_simulation [${res.status}]:`, errorText);
    throw new Error(
      errorData?.detail || errorData?.message || `Rebalance API failed: HTTP ${res.status}`
    );
  }
  return res.json();
}
