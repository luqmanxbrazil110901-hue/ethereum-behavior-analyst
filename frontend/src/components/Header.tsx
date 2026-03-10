import React from 'react';

interface HeaderProps {
  lang: string;
  onLangChange: (lang: string) => void;
  onExport: () => void;
}

const Header: React.FC<HeaderProps> = ({ lang, onLangChange, onExport }) => {
  return (
    <div className="header">
      <div className="header-left">
        <div className="header-logo">
          <span role="img" aria-label="diamond">&#x1F48E;</span>
        </div>
        <span className="header-title">Ethereum Behavior Analyst</span>
      </div>
      <div className="header-right">
        <button className="theme-toggle" title="Toggle theme">
          &#x1F319;
        </button>
        {['EN', '\u4E2D\u6587', 'VI'].map((l) => (
          <button
            key={l}
            className={`lang-btn ${lang === l ? 'active' : ''}`}
            onClick={() => onLangChange(l)}
          >
            {l}
          </button>
        ))}
        <button className="export-btn" onClick={onExport}>
          &#x2B07; Download CSV
        </button>
      </div>
    </div>
  );
};

export default Header;
