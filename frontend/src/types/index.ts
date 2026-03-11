
export interface Wallet {
  address: string;
  client_type: string | null;
  client_tier: string | null;
  freq_cycle: string | null;
  freq_tier: string | null;
  purity: string | null;
  review_status: string | null;
  data_source: string | null;
  eth_balance: number | null;
  total_amount: number | null;
  token_count: number | null;
  tx_in_period: number | null;
  is_contract: boolean | null;
  funded_by: string | null;
  wallet_created: string | null;
  collection_date: string | null;
  update_time: string | null;
  first_seen: string | null;
  last_seen: string | null;
  label: string | null;
  notes: string | null;
  on_watchlist: boolean | null;

  // Super Analysis v2
  risk_score: number | null;
  risk_level: "low" | "medium" | "high" | null;
  confidence: "low" | "medium" | "high" | null;
  contamination_score: number | null;

  tx_30d: number | null;
  tx_90d: number | null;
  volume_30d_usd: number | null;
  volume_90d_usd: number | null;
  active_days_30d: number | null;
}

export interface WalletListResponse {
  wallets: Wallet[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface Stats {
  total_wallets: number;
  by_client_type: Record<string, number>;
  by_client_tier: Record<string, number>;
  by_freq_cycle: Record<string, number>;
  by_freq_tier: Record<string, number>;
  by_purity: Record<string, number>;
  by_review: Record<string, number>;
  by_data_source: Record<string, number>;
}

export interface Filters {
  client_type?: string;
  client_tier?: string;
  freq_cycle?: string;
  freq_tier?: string;
  purity?: string;
  review_status?: string;
  data_source?: string;
  search?: string;
}
