import React from 'react';
import { Wallet } from '../types';
import { updateWalletReview } from '../api/client';

interface WalletTableProps {
  wallets: Wallet[];
  sort: string;
  order: string;
  onSort: (column: string) => void;
  onDataChange: () => void;
}

const CLIENT_TYPES = ['U', 'E', 'S', 'AP', 'B'];

const COLUMNS: { key: string; label: string; sortable: boolean }[] = [
  { key: 'address', label: 'Address', sortable: true },
  { key: 'data_source', label: 'Data Source', sortable: true },
  { key: 'client_type', label: 'Client Type', sortable: true },
  { key: 'client_tier', label: 'Client Tier', sortable: true },
  { key: 'review_status', label: 'Review', sortable: true },
  { key: 'freq_cycle', label: 'Freq Cycle', sortable: true },
  { key: 'freq_tier', label: 'Freq Tier', sortable: true },
  { key: 'purity', label: 'Purity', sortable: true },
  { key: 'risk_level', label: 'Risk', sortable: true },
  { key: 'confidence', label: 'Confidence', sortable: true },
  { key: 'funded_by', label: 'Funded By', sortable: false },
  { key: 'total_amount', label: 'Total Amount', sortable: true },
  { key: 'tx_in_period', label: 'TX in Period', sortable: true },
  { key: 'wallet_created', label: 'Wallet Created', sortable: true },
  { key: 'collection_date', label: 'Collection Date', sortable: true },
  { key: 'update_time', label: 'Update Time', sortable: true },
  { key: 'reviewer', label: 'Reviewer', sortable: false },
];

function truncateAddress(addr: string | null): string {
  if (!addr) return '\u2014';
  const a = addr.trim();
  if (a.length <= 13) return a;
  return `${a.slice(0, 7)}...${a.slice(-5)}`;
}

function riskClass(level: string | null): string {
  if (level === 'high') return 'risk-high';
  if (level === 'medium') return 'risk-medium';
  return 'risk-low';
}

function confidenceClass(level: string | null): string {
  if (level === 'high') return 'conf-high';
  if (level === 'medium') return 'conf-medium';
  return 'conf-low';
}

function formatAmount(amount: number | null, tokenCount: number | null): React.ReactNode {
  if (amount === null || amount === undefined || amount === 0) {
    return (
      <div className="amount-cell">
        <span className="amount-value">$0 (0 Tokens)</span>
      </div>
    );
  }
  const formatted =
    amount >= 1000
      ? `$${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
      : `$${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  const tokens = tokenCount || 0;
  return (
    <div className="amount-cell">
      <span className="amount-value">{formatted}</span>
      <span className="token-info">({tokens} Tokens)</span>
    </div>
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014';
  try {
    const d = new Date(dateStr);
    return d.toISOString().slice(0, 10);
  } catch {
    return dateStr;
  }
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '\u2014';
  try {
    const d = new Date(dateStr);
    const date = d.toISOString().slice(0, 10);
    const time = d.toISOString().slice(11, 16);
    return `${date} | ${time}`;
  } catch {
    return dateStr;
  }
}

const WalletTable: React.FC<WalletTableProps> = ({ wallets, sort, order, onSort, onDataChange }) => {
  const handleTypeChange = async (address: string, newType: string) => {
    try {
      await updateWalletReview(address, { client_type: newType, review_status: 'Reviewed' });
      onDataChange();
    } catch (err) {
      console.error('Failed to update wallet:', err);
    }
  };

  const renderSortArrow = (key: string) => {
    if (sort !== key) return null;
    return <span className="sort-arrow">{order === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  return (
    <div className="table-container">
      <table className="wallet-table">
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={col.sortable ? () => onSort(col.key) : undefined}
                style={{ cursor: col.sortable ? 'pointer' : 'default' }}
              >
                {col.label}
                {col.sortable && renderSortArrow(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {wallets.map((w) => (
            <tr key={w.address}>
              <td>
                <span className="address-cell" title={w.address}>
                  {truncateAddress(w.address)}
                </span>
              </td>

              <td>
                <span className={`badge badge-${w.data_source || 'R'}`}>{w.data_source || 'R'}</span>
              </td>

              <td>
                <select
                  className="type-select"
                  value={w.client_type || 'U'}
                  onChange={(e) => handleTypeChange(w.address, e.target.value)}
                >
                  {CLIENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </td>

              <td className="tier-cell">{w.client_tier || '\u2014'}</td>

              <td>
                <span
                  className={`review-badge ${w.review_status === 'AI Review'
                      ? 'review-ai'
                      : w.review_status === 'Reviewed'
                        ? 'review-done'
                        : 'review-manual'
                    }`}
                >
                  {w.review_status === 'AI Review'
                    ? 'A'
                    : w.review_status === 'Manual Review'
                      ? 'M'
                      : w.review_status === 'Reviewed'
                        ? 'R'
                        : '\u2014'}
                </span>
              </td>

              <td className="freq-cell">{w.freq_cycle || '\u2014'}</td>
              <td className="freq-cell">{w.freq_tier || '\u2014'}</td>

              <td>
                <span className={`purity-${w.purity || 'C'}`}>{w.purity || '\u2014'}</span>
              </td>

              {/* Risk */}
              <td>
                <span className={`badge ${riskClass(w.risk_level)}`} title={`Score: ${Math.round(w.risk_score ?? 0)}`}>
                  {(w.risk_level || 'low').toUpperCase()} ({Math.round(w.risk_score ?? 0)})
                </span>
              </td>

              {/* Confidence */}
              <td>
                <span className={`badge ${confidenceClass(w.confidence)}`}>
                  {(w.confidence || 'low').toUpperCase()}
                </span>
              </td>

              <td>
                {w.funded_by ? (
                  <span className="funded-by-cell" title={w.funded_by}>
                    {truncateAddress(w.funded_by)}
                  </span>
                ) : (
                  '\u2014'
                )}
              </td>

              <td>{formatAmount(w.total_amount, w.token_count)}</td>
              <td style={{ textAlign: 'right' }}>{w.tx_in_period?.toLocaleString() || 0}</td>
              <td className="date-cell">{formatDate(w.wallet_created)}</td>
              <td className="date-cell">{formatDate(w.collection_date)}</td>
              <td className="date-cell">{formatDateTime(w.update_time)}</td>

              <td>
                <span
                  className={
                    w.review_status === 'AI Review'
                      ? 'review-ai'
                      : w.review_status === 'Reviewed'
                        ? 'review-done'
                        : 'review-manual'
                  }
                >
                  {w.review_status || 'Manual Review'}
                </span>
              </td>
            </tr>
          ))}

          {wallets.length === 0 && (
            <tr>
              <td colSpan={COLUMNS.length} style={{ textAlign: 'center', padding: '40px', color: '#8b949e' }}>
                No wallets found. Add addresses to analyze.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default WalletTable;