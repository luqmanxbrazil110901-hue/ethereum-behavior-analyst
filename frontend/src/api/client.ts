import axios from 'axios';
import { WalletListResponse, Stats, Filters, Wallet } from '../types';

const API_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_URL,
});

export async function fetchWallets(
  filters: Filters,
  page: number = 1,
  limit: number = 100,
  sort: string = 'update_time',
  order: string = 'desc'
): Promise<WalletListResponse> {
  const params: Record<string, any> = { page, limit, sort, order };
  if (filters.client_type) params.client_type = filters.client_type;
  if (filters.client_tier) params.client_tier = filters.client_tier;
  if (filters.freq_cycle) params.freq_cycle = filters.freq_cycle;
  if (filters.freq_tier) params.freq_tier = filters.freq_tier;
  if (filters.purity) params.purity = filters.purity;
  if (filters.review_status) params.review_status = filters.review_status;
  if (filters.data_source) params.data_source = filters.data_source;
  if (filters.search) params.search = filters.search;

  const resp = await api.get<WalletListResponse>('/api/wallets', { params });
  return resp.data;
}

export async function fetchStats(): Promise<Stats> {
  const resp = await api.get<Stats>('/api/stats');
  return resp.data;
}

export async function analyzeWallet(address: string): Promise<Wallet> {
  const resp = await api.post<Wallet>('/api/wallets/analyze', { address });
  return resp.data;
}

export async function updateWalletReview(
  address: string,
  data: { review_status?: string; client_type?: string; notes?: string }
): Promise<Wallet> {
  const resp = await api.put<Wallet>(`/api/wallets/${address}/review`, data);
  return resp.data;
}

export function getExportUrl(filters: Filters): string {
  const params = new URLSearchParams();
  params.append('format', 'csv');
  if (filters.client_type) params.append('client_type', filters.client_type);
  if (filters.client_tier) params.append('client_tier', filters.client_tier);
  if (filters.freq_cycle) params.append('freq_cycle', filters.freq_cycle);
  if (filters.freq_tier) params.append('freq_tier', filters.freq_tier);
  if (filters.purity) params.append('purity', filters.purity);
  if (filters.review_status) params.append('review_status', filters.review_status);
  if (filters.data_source) params.append('data_source', filters.data_source);
  return `${API_URL}/api/wallets/export?${params.toString()}`;
}
