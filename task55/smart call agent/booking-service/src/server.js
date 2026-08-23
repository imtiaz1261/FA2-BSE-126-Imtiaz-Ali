const express = require('express');
const config = require('./config/env');
const routes = require('./api/routes');

const app = express();
app.use(express.json());

app.get('/healthz', (req, res) => res.status(200).send('ok'));
app.use('/', routes);

app.listen(config.PORT, () => {
  console.log(`booking-service listening on :${config.PORT}`);
});

module.exports = app;
