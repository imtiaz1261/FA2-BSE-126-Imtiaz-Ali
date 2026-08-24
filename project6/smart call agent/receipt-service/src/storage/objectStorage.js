const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const config = require('../config/env');

const s3 = new S3Client({
  region: config.S3_REGION,
  endpoint: config.S3_ENDPOINT, // undefined -> real AWS S3; set for MinIO/on-prem
  forcePathStyle: !!config.S3_ENDPOINT, // required for most non-AWS S3-compatible stores
  credentials: {
    accessKeyId: config.S3_ACCESS_KEY_ID,
    secretAccessKey: config.S3_SECRET_ACCESS_KEY,
  },
});

function receiptKey(trackingNumber) {
  return `receipts/${trackingNumber}.pdf`;
}

/** Uploads (or overwrites) the receipt PDF for a tracking number. */
async function uploadReceiptPdf(trackingNumber, pdfBuffer) {
  const key = receiptKey(trackingNumber);
  await s3.send(
    new PutObjectCommand({
      Bucket: config.S3_BUCKET,
      Key: key,
      Body: pdfBuffer,
      ContentType: 'application/pdf',
      // No ACL: 'public-read' -- receipts are only ever reachable via a
      // signed, time-limited URL, never a public/guessable link.
    })
  );
  return key;
}

/**
 * Generates a fresh signed download URL for an already-uploaded receipt.
 * Called on every download/resend request rather than caching a long-lived
 * URL, so access windows stay short (SIGNED_URL_TTL_SECONDS, default 24h)
 * regardless of how long ago the PDF itself was generated.
 */
async function getSignedDownloadUrl(s3Key) {
  const command = new GetObjectCommand({ Bucket: config.S3_BUCKET, Key: s3Key });
  const url = await getSignedUrl(s3, command, { expiresIn: config.SIGNED_URL_TTL_SECONDS });
  const expiresAt = new Date(Date.now() + config.SIGNED_URL_TTL_SECONDS * 1000);
  return { url, expiresAt };
}

module.exports = { uploadReceiptPdf, getSignedDownloadUrl, receiptKey };
