# Digital Receipt Generation — Module 8

Branded, printable PDF receipts with an embedded QR code, stored in object
storage behind signed, time-limited download URLs.

## 1. PDF generation (`src/pdf/buildReceiptPdf.js`)

Uses PDFKit (programmatic PDF construction, no headless browser needed —
consistent with this being a Node service throughout, the same role
`reportlab` plays in a Python stack). `buildReceiptPdf(receiptData)`
returns a `Buffer`, built by piping PDFKit's stream output into memory.

Layout, top to bottom:
1. Department letterhead (`ORG_NAME`, location address)
2. "APPOINTMENT RECEIPT" title
3. Label/value grid: applicant name, CNIC, purpose of visit, service
   center name + address, appointment date, appointment time
4. Tracking number in large (28pt bold) type — the single most important
   element on the page, sized to be read at a glance when presented at
   the counter
5. QR code (see below), centered, with a "scan for fast check-in" caption
6. Required-documents checklist, one line per item with an unchecked-box
   glyph
7. Footer note (arrive 10 minutes early, contact helpline with tracking
   number for changes)

## 2. QR code embedding (`src/qr/generateQrCode.js`)

```js
QRCode.toBuffer(trackingNumber, { type: 'png', errorCorrectionLevel: 'M', width: 240 })
```

Generated as a PNG buffer and embedded directly into the PDF via
`doc.image(qrBuffer, x, y, { width, height })` — no temp files, no extra
network round trip. Kept as its own module so the encoding scheme (today:
the raw tracking number string) can evolve later — e.g. to a short check-in
URL — without touching the PDF layout code.

## 3. Storage + signed download URL (`src/storage/objectStorage.js`)

- Upload: `PutObjectCommand` to an S3-compatible bucket (`S3_ENDPOINT`
  unset -> real AWS S3; set it for MinIO/on-prem), key
  `receipts/<trackingNumber>.pdf`. No `public-read` ACL — the object is
  never reachable except via a signed URL.
- Download: `getSignedUrl(s3, GetObjectCommand, { expiresIn: SIGNED_URL_TTL_SECONDS })`,
  default 24h. A fresh signed URL is generated on every request (generate,
  re-fetch, or resend) rather than caching one — access windows stay short
  no matter how long ago the PDF itself was produced.

## 4. Orchestration (`src/receipts/generateReceipt.js`)

`generateReceipt({ trackingNumber })`:
1. If a `receipts` row already exists and `forceRegenerate` isn't set,
   skip straight to minting a new signed URL for the existing PDF — no
   need to rebuild it.
2. Otherwise: fetch the appointment from booking-service (Module 6), the
   service name + required documents from service-catalog (Module 4), and
   the location name/address from the local `locationDirectory`.
3. Build the PDF, upload it, upsert the `receipts` row (`tracking_number`
   PK, `s3_key`, `regenerated_count`).
4. Return `{ downloadUrl, expiresAt }`.

This is called automatically right after booking confirmation (Module 6's
post-commit flow, alongside the SMS trigger) and is idempotent to call
again any time.

## 5. Self-service resend (`src/receipts/resendReceipt.js`)

```
POST /receipts/resend   { tracking_number, phone }
```

Looks up the appointment by `tracking_number`, then verifies the supplied
`phone` matches the phone on file (last 10 digits compared, so
formatting/country-code differences don't cause false rejections) before
sending anything. On mismatch, returns a deliberately generic
`403 verification_failed` — it never reveals whether the tracking number
existed but the phone was wrong, to avoid leaking which half of the pair
was incorrect. On match, regenerates a fresh signed URL and triggers the
Notification Service (Module 10) to actually send it.

`GET /receipts/:trackingNumber` (no phone required) is intentionally
lighter-weight — it only returns a signed URL to someone who already has
the tracking number in hand, never sends anything to a phone/email on its
own, so no additional verification is layered on top.

## 6. API

```
POST /receipts/generate   { tracking_number, force_regenerate? }  -> { downloadUrl, expiresAt, regenerated }
GET  /receipts/:trackingNumber                                    -> { downloadUrl, expiresAt, regenerated }
POST /receipts/resend     { tracking_number, phone }               -> { sent, downloadUrl, expiresAt }
```

## 7. Data model

```sql
receipts (
  tracking_number PK REFERENCES appointments(tracking_number),
  s3_key, generated_at, regenerated_count, last_sent_at
)
```

Full DDL in `db/migrations/006_create_receipts.sql`.

## 8. On credentials

`.env.example` ships with placeholders only for `DATABASE_URL`,
`S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY` — no real secrets committed.
Fill in real values only in a local, untracked `.env`.

## 9. Local development

```bash
npm install
cp .env.example .env
psql "$DATABASE_URL" -f db/migrations/006_create_receipts.sql
npm run dev
```

Requires `appointments` (Module 6) already migrated in the same database,
since `receipts.tracking_number` references it.

## Next module

Module 9 (Application Status Tracking) will read `appointments.status` and
this module's `receipts` table to power a status-check endpoint/portal, and
Module 10 (Notifications) is what actually delivers the SMS/email
containing the `downloadUrl` this module produces.
