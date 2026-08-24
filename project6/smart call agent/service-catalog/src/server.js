const express = require('express');
const config = require('./config/env');
const routes = require('./api/routes');
const { seedIfEmpty } = require('./catalog/catalogStore');

const app = express();
app.use(express.json());

app.get('/healthz', (req, res) => res.status(200).send('ok'));
app.use('/', routes);

async function start() {
  const seedResult = await seedIfEmpty();
  if (seedResult.seeded) {
    console.log(`Seeded ${seedResult.count} services into an empty catalog.`);
  }

  app.listen(config.PORT, () => {
    console.log(`service-catalog listening on :${config.PORT}`);
  });
}

start().catch((err) => {
  console.error('Failed to start service-catalog', err);
  process.exit(1);
});

module.exports = app;
