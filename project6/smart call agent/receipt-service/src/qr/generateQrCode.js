const QRCode = require('qrcode');

/**
 * Generates a QR code PNG buffer encoding the tracking number, for
 * embedding directly into the PDF receipt. Kept as its own small module
 * so the encoding scheme (currently: the raw tracking number string) can
 * evolve independently of PDF layout — e.g. later encoding a short check-in
 * URL instead of the bare number, without touching the PDF builder.
 */
async function generateTrackingQrCode(trackingNumber) {
  return QRCode.toBuffer(trackingNumber, {
    type: 'png',
    errorCorrectionLevel: 'M',
    margin: 1,
    width: 240,
  });
}

module.exports = { generateTrackingQrCode };
