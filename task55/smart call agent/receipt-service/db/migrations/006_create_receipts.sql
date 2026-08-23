-- One row per tracking number once a receipt has been generated at least
-- once. The PDF itself lives in object storage (s3_key); this row just
-- tracks where it is so repeat downloads/resends don't regenerate the PDF
-- unnecessarily — only a fresh signed URL is needed each time.
CREATE TABLE IF NOT EXISTS receipts (
    tracking_number   VARCHAR(32) PRIMARY KEY REFERENCES appointments(tracking_number),
    s3_key            VARCHAR(255) NOT NULL,
    generated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    regenerated_count INTEGER NOT NULL DEFAULT 0,
    last_sent_at      TIMESTAMPTZ
);
