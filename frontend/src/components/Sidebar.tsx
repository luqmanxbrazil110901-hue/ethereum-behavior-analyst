import React from 'react';
import { Stats, Filters } from '../types';

interface SidebarProps {
  stats: Stats | null;
  filters: Filters;
  onFilterChange: (key: keyof Filters, value: string | undefined) => void;
  onReset: () => void;
}

interface FilterSection {
  title: string;
  filterKey: keyof Filters;
  items: { code: string; label: string }[];
  statsKey: keyof Stats;
}

const SECTIONS: FilterSection[] = [
  {
    title: 'DATA SOURCE',
    filterKey: 'data_source',
    items: [
      { code: 'R', label: 'R Real-time' },
      { code: 'H', label: 'H Historical' },
    ],
    statsKey: 'by_data_source',
  },
  {
    title: 'CLIENT TYPE',
    filterKey: 'client_type',
    items: [
      { code: 'U', label: 'U Real User' },
      { code: 'E', label: 'E Exchange' },
      { code: 'S', label: 'S Script' },
      { code: 'AP', label: 'AP Malicious' },
      { code: 'B', label: 'B Bridge' },
    ],
    statsKey: 'by_client_type',
  },
  {
    title: 'CLIENT TIER',
    filterKey: 'client_tier',
    items: [
      { code: 'L1', label: 'L1 <10k' },
      { code: 'L2', label: 'L2 10k-99.9k' },
      { code: 'L3', label: 'L3 100k-999.9k' },
      { code: 'L4', label: 'L4 1M-9.99M' },
      { code: 'L5', label: 'L5 10M+' },
    ],
    statsKey: 'by_client_tier',
  },
  {
    title: 'REVIEW',
    filterKey: 'review_status',
    items: [
      { code: 'AI Review', label: 'A Auto' },
      { code: 'Manual Review', label: 'M Manual' },
    ],
    statsKey: 'by_review',
  },
  {
    title: 'FREQ CYCLE',
    filterKey: 'freq_cycle',
    items: [
      { code: 'D', label: 'D Day' },
      { code: 'W', label: 'W Week' },
      { code: 'M', label: 'M Month' },
      { code: 'Y', label: 'Y Year' },
    ],
    statsKey: 'by_freq_cycle',
  },
  {
    title: 'FREQ TIER',
    filterKey: 'freq_tier',
    items: [
      { code: 'F1', label: 'F1 0 TX' },
      { code: 'F2', label: 'F2 1-3 TX' },
      { code: 'F3', label: 'F3 4-10 TX' },
      { code: 'F4', label: 'F4 11-19 TX' },
      { code: 'F5', label: 'F5 20+ TX' },
    ],
    statsKey: 'by_freq_tier',
  },
  {
    title: 'ADDRESS PURITY',
    filterKey: 'purity',
    items: [
      { code: 'C', label: 'C Clean' },
      { code: 'P', label: 'P Toxic' },
    ],
    statsKey: 'by_purity',
  },
];

const Sidebar: React.FC<SidebarProps> = ({ stats, filters, onFilterChange, onReset }) => {
  const getCount = (section: FilterSection, code: string): number => {
    if (!stats) return 0;
    const data = stats[section.statsKey] as Record<string, number>;
    if (!data) return 0;

    // For review, the stats use short codes A/M/R but filter uses full names
    if (section.filterKey === 'review_status') {
      const shortMap: Record<string, string> = {
        'AI Review': 'A',
        'Manual Review': 'M',
        'Reviewed': 'R',
      };
      return data[shortMap[code]] || 0;
    }

    return data[code] || 0;
  };

  return (
    <div className="sidebar">
      {SECTIONS.map((section) => (
        <div className="sidebar-section" key={section.title}>
          <div className="sidebar-section-title">{section.title}</div>
          {section.items.map((item) => {
            const isActive = filters[section.filterKey] === item.code;
            const count = getCount(section, item.code);
            return (
              <div
                key={item.code}
                className={`sidebar-item ${isActive ? 'active' : ''}`}
                onClick={() => onFilterChange(section.filterKey, item.code)}
              >
                <span className="sidebar-item-label">{item.label}</span>
                <span className="sidebar-item-count">{count.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      ))}

      <div className="sidebar-actions">
        <button className="sidebar-btn" onClick={onReset}>
          Reset All
        </button>
        <button className="sidebar-btn">
          Actions
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
