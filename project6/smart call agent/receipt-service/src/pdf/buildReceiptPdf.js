const PDFDocument = require('pdfkit');
const config = require('../config/env');
const { generateTrackingQrCode } = require('../qr/generateQrCode');

/**
 * Builds the receipt PDF as a Buffer, ready for upload to object storage.
 *
 * `receiptData` shape:
 *   {
 *     applicantName, cnic,
 *     serviceName, requiredDocuments: string[],
 *     locationName, locationAddress,
 *     date, timeBlock,
 *     trackingNumber,
 *   }
 *
 * Layout, top to bottom: department letterhead, a clear "APPOINTMENT
 * RECEIPT" title, applicant + appointment details in a label/value grid,
 * the tracking number in large bold type (the single most important
 * element on the page, sized to be legible at a glance when presented at
 * the counter), a QR code encoding it for fast scanning, and the required
 * documents checklist at the bottom.
 */
async function buildReceiptPdf(receiptData) {
  const {
    applicantName,
    cnic,
    serviceName,
    requiredDocuments,
    locationName,
    locationAddress,
    date,
    timeBlock,
    trackingNumber,
  } = receiptData;

  const qrBuffer = await generateTrackingQrCode(trackingNumber);

  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ size: 'A4', margin: 50 });
    const chunks = [];
    doc.on('data', (chunk) => chunks.push(chunk));
    doc.on('end', () => resolve(Buffer.concat(chunks)));
    doc.on('error', reject);

    // --- Letterhead ---
    doc
      .fontSize(9)
      .fillColor('#555555')
      .text('GOVERNMENT OF PAKISTAN', { align: 'center' })
      .fontSize(16)
      .fillColor('#111111')
      .font('Helvetica-Bold')
      .text(config.ORG_NAME, { align: 'center' })
      .moveDown(0.2)
      .fontSize(9)
      .font('Helvetica')
      .fillColor('#555555')
      .text(locationAddress, { align: 'center' });

    doc.moveDown(1);
    doc.moveTo(50, doc.y).lineTo(545, doc.y).strokeColor('#cccccc').stroke();
    doc.moveDown(1);

    // --- Title ---
    doc
      .fontSize(18)
      .font('Helvetica-Bold')
      .fillColor('#111111')
      .text('APPOINTMENT RECEIPT', { align: 'center' });
    doc.moveDown(1.2);

    // --- Applicant + appointment details (label/value pairs) ---
    const detailRows = [
      ['Applicant Name', applicantName],
      ['CNIC', cnic || 'Not provided'],
      ['Purpose of Visit', serviceName],
      ['Service Center', locationName],
      ['Address', locationAddress],
      ['Appointment Date', date],
      ['Appointment Time', timeBlock],
    ];

    const labelX = 60;
    const valueX = 220;
    doc.fontSize(11);
    for (const [label, value] of detailRows) {
      const rowY = doc.y;
      doc.font('Helvetica-Bold').fillColor('#333333').text(label, labelX, rowY, { width: 150 });
      doc.font('Helvetica').fillColor('#111111').text(String(value), valueX, rowY, { width: 320 });
      doc.moveDown(0.6);
    }

    doc.moveDown(1);
    doc.moveTo(50, doc.y).lineTo(545, doc.y).strokeColor('#cccccc').stroke();
    doc.moveDown(1);

    // --- Tracking number, large and unmissable ---
    doc
      .fontSize(11)
      .font('Helvetica')
      .fillColor('#555555')
      .text('TRACKING / BOOKING NUMBER', { align: 'center' });
    doc.moveDown(0.3);
    doc
      .fontSize(28)
      .font('Helvetica-Bold')
      .fillColor('#0a3d91')
      .text(trackingNumber, { align: 'center', characterSpacing: 1 });
    doc.moveDown(1);

    // --- QR code, centered ---
    const qrSize = 110;
    const qrX = (doc.page.width - qrSize) / 2;
    doc.image(qrBuffer, qrX, doc.y, { width: qrSize, height: qrSize });
    doc.y += qrSize + 10;
    doc
      .fontSize(9)
      .font('Helvetica')
      .fillColor('#555555')
      .text('Scan at the counter for fast check-in', { align: 'center' });

    doc.moveDown(1.5);
    doc.moveTo(50, doc.y).lineTo(545, doc.y).strokeColor('#cccccc').stroke();
    doc.moveDown(1);

    // --- Required documents checklist ---
    doc
      .fontSize(13)
      .font('Helvetica-Bold')
      .fillColor('#111111')
      .text('Please bring the following documents:');
    doc.moveDown(0.5);
    doc.fontSize(11).font('Helvetica').fillColor('#111111');
    for (const item of requiredDocuments) {
      doc.text(`\u2610  ${item}`, { indent: 10 }); // unchecked-box glyph
      doc.moveDown(0.3);
    }

    doc.moveDown(1.5);
    doc
      .fontSize(8)
      .fillColor('#888888')
      .text(
        'This receipt is your appointment confirmation. Please arrive 10 minutes early with all listed documents. ' +
          'For any changes, contact the citizen services helpline and quote your tracking number.',
        { align: 'center' }
      );

    doc.end();
  });
}

module.exports = { buildReceiptPdf };
