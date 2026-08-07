PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sets (
    set_id INTEGER PRIMARY KEY CHECK (set_id > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    abbreviation TEXT NOT NULL CHECK (length(trim(abbreviation)) > 0),
    products_modified_at TEXT,
    pricing_modified_at TEXT
);

CREATE TABLE IF NOT EXISTS cards (
    product_id INTEGER PRIMARY KEY CHECK (product_id > 0),
    set_id INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    collector_number TEXT NOT NULL CHECK (length(trim(collector_number)) > 0),
    rarity TEXT NOT NULL CHECK (length(trim(rarity)) > 0),

    FOREIGN KEY (set_id) REFERENCES sets(set_id)
);

CREATE INDEX IF NOT EXISTS idx_cards_set_id ON cards(set_id);

CREATE TABLE IF NOT EXISTS prices (
    product_id INTEGER NOT NULL,
    finish TEXT NOT NULL CHECK (length(trim(finish)) > 0),
    market_price_cents  INTEGER NOT NULL CHECK (market_price_cents >= 0),

    PRIMARY KEY (product_id, finish),
    FOREIGN KEY (product_id) REFERENCES cards(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS card_images (
    image_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    image_url TEXT NOT NULL CHECK (length(trim(image_url)) > 0),

    FOREIGN KEY (product_id) REFERENCES cards(product_id) ON DELETE CASCADE,
    UNIQUE (product_id, image_url)
);

CREATE TABLE IF NOT EXISTS fingerprints (
    image_id INTEGER NOT NULL,
    algorithm TEXT NOT NULL CHECK (length(trim(algorithm)) > 0),
    region TEXT NOT NULL CHECK (length(trim(region)) > 0),
    fingerprint_blob BLOB NOT NULL CHECK (length(fingerprint_blob) > 0),

    PRIMARY KEY (image_id, algorithm, region),
    FOREIGN KEY (image_id) REFERENCES card_images(image_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_runs (
    sync_run_id INTEGER PRIMARY KEY,
    set_id INTEGER,
    sync_type TEXT NOT NULL CHECK (length(trim(sync_type)) > 0),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    error_message TEXT,

    FOREIGN KEY (set_id) REFERENCES sets(set_id) ON DELETE SET NULL
);
