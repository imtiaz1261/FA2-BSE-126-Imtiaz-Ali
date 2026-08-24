require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const apiRoutes = require('./routes');

const app = express();
const PORT = Number(process.env.PORT || 8080);

app.use(cors());
app.use(express.json());

app.get('/healthz', (req, res) => {
  res.status(200).json({ ok: true, service: 'admin-api' });
});

app.use('/api', apiRoutes);

const distPath = path.join(__dirname, '../../admin-console/dist');
const indexPath = path.join(distPath, 'index.html');

app.use(express.static(distPath));
app.get('*', (req, res) => {
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ error: 'not_found' });
  }
  return res.sendFile(indexPath);
});

app.listen(PORT, () => {
  console.log(`Admin API running on http://localhost:${PORT}`);
});

module.exports = app;
