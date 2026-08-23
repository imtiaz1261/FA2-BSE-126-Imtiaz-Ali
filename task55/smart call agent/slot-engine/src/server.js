const express = require('express');
const config = require('./config/env');
const routes = require('./api/routes');
const { startHoldSweeper } = require('./jobs/expireHolds');

const app = express();
app.use(express.json());

app.get('/healthz', (req, res) => res.status(200).send('ok'));
app.use('/', routes);

startHoldSweeper();

app.listen(config.PORT, () => {
  console.log(`slot-engine listening on :${config.PORT}`);
});

module.exports = app;
