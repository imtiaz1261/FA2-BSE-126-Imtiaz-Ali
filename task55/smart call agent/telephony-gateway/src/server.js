const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const config = require('./config/env');

const incomingCallRouter = require('./webhooks/incomingCall');
const fallbackRouter = require('./webhooks/fallback');
const { router: queueRouter } = require('./queue/callQueue');
const { attachMediaStreamBridge } = require('./mediaStream/bridge');

const app = express();
app.use(express.urlencoded({ extended: false })); // Twilio webhooks post form-encoded
app.use(express.json());

app.get('/healthz', (req, res) => res.status(200).send('ok'));

// Twilio webhook: fired the instant a call hits the service number
app.use('/voice', incomingCallRouter);

// Fallback/handoff endpoints (timeout, trigger phrase, agent error)
app.use('/voice/fallback', fallbackRouter);

// Queue wait-time announcement + hold music loop
app.use('/voice/queue', queueRouter);

const server = http.createServer(app);

// Real-time bidirectional audio: Twilio Media Streams <-> Voice Agent
const wss = new WebSocketServer({ server, path: '/media-stream' });
attachMediaStreamBridge(wss);

server.listen(config.PORT, () => {
  console.log(`telephony-gateway listening on :${config.PORT}`);
});

module.exports = server;
