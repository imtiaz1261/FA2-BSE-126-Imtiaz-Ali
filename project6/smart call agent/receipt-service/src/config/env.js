require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 9000,

  DATABASE_URL: required('DATABASE_URL'),

  // Object storage (S3-compatible — works against AWS S3 or a
  // self-hosted MinIO/etc. endpoint for on-prem deployments).
  S3_BUCKET: required('S3_BUCKET'),
  S3_REGION: process.env.S3_REGION || 'us-east-1',
  S3_ENDPOINT: process.env.S3_ENDPOINT || undefined, // set for MinIO/non-AWS
  S3_ACCESS_KEY_ID: required('S3_ACCESS_KEY_ID'),
  S3_SECRET_ACCESS_KEY: required('S3_SECRET_ACCESS_KEY'),

  SIGNED_URL_TTL_SECONDS: parseInt(process.env.SIGNED_URL_TTL_SECONDS || '86400', 10), // 24h

  // Upstream services this module reads from.
  BOOKING_SERVICE_BASE_URL: required('BOOKING_SERVICE_BASE_URL'),
  SERVICE_CATALOG_BASE_URL: required('SERVICE_CATALOG_BASE_URL'),
  TRACKING_SERVICE_BASE_URL: required('TRACKING_SERVICE_BASE_URL'),
  NOTIFICATION_SERVICE_BASE_URL: required('NOTIFICATION_SERVICE_BASE_URL'),

  ORG_NAME: process.env.ORG_NAME || 'Citizen Services Department',
};
