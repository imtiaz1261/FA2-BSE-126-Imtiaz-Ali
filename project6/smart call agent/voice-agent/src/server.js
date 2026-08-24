const http = require('http');
const { WebSocketServer } = require('ws');
const url = require('url');
const config = require('./config/env');
const { CallSession } = require('./session/callSession');

const server = http.createServer((req, res) => {
  if (req.url === '/healthz') {
    res.writeHead(200);
    res.end('ok');
    return;
  }
  res.writeHead(404);
  res.end();
});

// telephony-gateway connects here per call:
//   ws://voice-agent:4000/session?callSid=CAxxxx
const wss = new WebSocketServer({ server, path: '/session' });

wss.on('connection', (ws, req) => {
  const { query } = url.parse(req.url, true);
  const callSid = query.callSid;
  if (!callSid) {
    ws.close(1008, 'callSid required');
    return;
  }

  const session = new CallSession({
    callSid,
    send: (messageObject) => {
      if (ws.readyState === ws.OPEN) ws.send(JSON.stringify(messageObject));
    },
  });

  ws.on('message', (raw) => {
    const msg = JSON.parse(raw);
    if (msg.type === 'audio_in') {
      session.pushAudio(msg.audioBase64);
    }
  });

  ws.on('close', () => session.close());
  ws.on('error', (err) => console.error(`session ws error (${callSid})`, err));
});

server.listen(config.PORT, () => {
  console.log(`voice-agent listening on :${config.PORT}`);
});

module.exports = server;
