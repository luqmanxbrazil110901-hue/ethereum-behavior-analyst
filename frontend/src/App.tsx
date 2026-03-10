import React, { useState, useEffect, useCallback } from 'react';
import { Filters, Stats, WalletListResponse } from './types';
import { fetchWallets, fetchStats, getExportUrl } from './api/client';
import Sidebar from './components/Sidebar';
import WalletTable from './components/WalletTable';
import Header from './components/Header';
import Pagination from './components/Pagination';
import './App.css';

function App() {
  const [filters, setFilters] = useState<Filters>({});
  const [stats, setStats] = useState<Stats | null>(null);
  const [data, setData] = useState<WalletListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState('update_time');
  const [order, setOrder] = useState('desc');
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [lang, setLang] = useState('EN');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [walletData, statsData] = await Promise.all([
        fetchWallets(filters, page, 100, sort, order),
        fetchStats(),
      ]);
      setData(walletData);
      setStats(statsData);
      setLastUpdate(new Date().toLocaleString('sv-SE').replace(' ', ' '));
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }, [filters, page, sort, order]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleFilterChange = (key: keyof Filters, value: string | undefined) => {
    setFilters(prev => {
      const next = { ...prev };
      if (value === undefined || prev[key] === value) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return next;
    });
    setPage(1);
  };

  const handleSort = (column: string) => {
    if (sort === column) {
      setOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSort(column);
      setOrder('desc');
    }
  };

  const resetFilters = () => {
    setFilters({});
    setPage(1);
  };

  const handleExport = () => {
    window.open(getExportUrl(filters), '_blank');
  };

  return (
    <div className="app">
      <Header
        lang={lang}
        onLangChange={setLang}
        onExport={handleExport}
      />
      <div className="main-content">
        <Sidebar
          stats={stats}
          filters={filters}
          onFilterChange={handleFilterChange}
          onReset={resetFilters}
        />
        <div className="content-area">
          <div className="content-header">
            <div className="row-counts">
              <span>Total Rows: <strong>{stats?.total_wallets?.toLocaleString() || 0}</strong></span>
              <span className="filtered-count">Filtered: <strong>{data?.total?.toLocaleString() || 0}</strong></span>
            </div>
            <div className="update-status">
              {loading ? (
                <span className="updating">Updating... <span className="spinner"></span> {lastUpdate}</span>
              ) : (
                <span>Updated: {lastUpdate}</span>
              )}
            </div>
          </div>
          <WalletTable
            wallets={data?.wallets || []}
            sort={sort}
            order={order}
            onSort={handleSort}
            onDataChange={loadData}
          />
          <Pagination
            page={page}
            totalPages={data?.total_pages || 1}
            onPageChange={setPage}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
