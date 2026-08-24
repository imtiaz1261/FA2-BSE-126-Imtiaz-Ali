const express = require('express');
const config = require('./config/env');
const routes = require('./api/routes');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false })); // Twilio's SMS webhook posts form-encoded

app.get('/healthz', (req, res) => res.status(200).send('ok'));
app.use('/', routes);

app.listen(config.PORT, () => {
  console.log(`status-service listening on :${config.PORT}`);
});

module.exports = app;
