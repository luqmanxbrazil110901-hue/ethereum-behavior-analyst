-- Ethereum Behavior Analyst - Database Schema

CREATE TABLE IF NOT EXISTS wallets (
    address             CHAR(42) PRIMARY KEY,

    -- Classification
    client_type         VARCHAR(10),
    client_tier         VARCHAR(5),
    freq_cycle          VARCHAR(5),
    freq_tier           VARCHAR(5),
    purity              VARCHAR(5),
    review_status       VARCHAR(20) DEFAULT 'Manual Review',

    -- Data Source
    data_source         VARCHAR(5) DEFAULT 'R',

    -- On-chain data
    eth_balance         NUMERIC DEFAULT 0,
    total_amount        NUMERIC DEFAULT 0,
    token_count         INTEGER DEFAULT 0,
    tx_in_period        INTEGER DEFAULT 0,
    is_contract         BOOLEAN DEFAULT FALSE,

    -- Relationships
    funded_by           CHAR(42),

    -- Timestamps
    wallet_created      DATE,
    collection_date     DATE DEFAULT CURRENT_DATE,
    update_time         TIMESTAMP DEFAULT NOW(),
    first_seen          TIMESTAMP,
    last_seen           TIMESTAMP,

    -- Metadata
    label               VARCHAR(100),
    notes               TEXT,
    on_watchlist        BOOLEAN DEFAULT FALSE,

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_w_type ON wallets(client_type);
CREATE INDEX IF NOT EXISTS idx_w_tier ON wallets(client_tier);
CREATE INDEX IF NOT EXISTS idx_w_freq ON wallets(freq_cycle);
CREATE INDEX IF NOT EXISTS idx_w_purity ON wallets(purity);
CREATE INDEX IF NOT EXISTS idx_w_review ON wallets(review_status);
CREATE INDEX IF NOT EXISTS idx_w_funded ON wallets(funded_by);
CREATE INDEX IF NOT EXISTS idx_w_watchlist ON wallets(on_watchlist) WHERE on_watchlist = TRUE;

CREATE TABLE IF NOT EXISTS transactions (
    tx_hash             CHAR(66) PRIMARY KEY,
    block_number        BIGINT NOT NULL,
    block_timestamp     TIMESTAMP NOT NULL,
    from_address        CHAR(42) NOT NULL,
    to_address          CHAR(42),
    value_wei           NUMERIC,
    gas_used            BIGINT,
    gas_price           NUMERIC,
    method_sig          CHAR(10),
    status              SMALLINT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_tx_to ON transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_tx_ts ON transactions(block_timestamp);

CREATE TABLE IF NOT EXISTS token_transfers (
    id                  SERIAL PRIMARY KEY,
    tx_hash             CHAR(66) NOT NULL,
    block_number        BIGINT NOT NULL,
    block_timestamp     TIMESTAMP NOT NULL,
    token_address       CHAR(42) NOT NULL,
    from_address        CHAR(42) NOT NULL,
    to_address          CHAR(42) NOT NULL,
    value               NUMERIC,
    token_type          VARCHAR(10),
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tt_from ON token_transfers(from_address);
CREATE INDEX IF NOT EXISTS idx_tt_to ON token_transfers(to_address);

CREATE TABLE IF NOT EXISTS known_labels (
    address             CHAR(42) PRIMARY KEY,
    label               VARCHAR(100) NOT NULL,
    category            VARCHAR(20) NOT NULL,
    is_toxic            BOOLEAN DEFAULT FALSE,
    source              VARCHAR(50),
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS classification_log (
    id                  SERIAL PRIMARY KEY,
    address             CHAR(42) NOT NULL,
    client_type         VARCHAR(10),
    client_tier         VARCHAR(5),
    freq_cycle          VARCHAR(5),
    freq_tier           VARCHAR(5),
    purity              VARCHAR(5),
    signals             JSONB,
    classified_at       TIMESTAMP DEFAULT NOW()
);
