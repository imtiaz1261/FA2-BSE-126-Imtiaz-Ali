require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 9500,

  DATABASE_URL: required('DATABASE_URL'),

  BOOKING_SERVICE_BASE_URL: required('BOOKING_SERVICE_BASE_URL'),
  NOTIFICATION_SERVICE_BASE_URL: required('NOTIFICATION_SERVICE_BASE_URL'),
  TRACKING_SERVICE_BASE_URL: required('TRACKING_SERVICE_BASE_URL'), // format+checksum validation before DB lookup

  // Twilio, for the inbound-SMS-keyword webhook and outbound status replies
  TWILIO_ACCOUNT_SID: required('TWILIO_ACCOUNT_SID'),
  TWILIO_AUTH_TOKEN: required('TWILIO_AUTH_TOKEN'),
};
