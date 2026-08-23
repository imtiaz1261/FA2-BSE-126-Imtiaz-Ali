const express = require('express');
const twilio = require('twilio');
const config = require('../config/env');

const router = express.Router();
const VoiceResponse = twilio.twiml.VoiceResponse;
const client = twilio(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN);

const AVG_HANDLE_TIME_SECONDS = 180; // rolling average, tune from historical data
const ASSUMED_ACTIVE_AGENTS = 4; // number of staff softphones logged into the queue

async function getQueueDepth() {
  try {
    const queue = await client.queue(config.HUMAN_QUEUE_NAME).fetch();
    return queue.currentSize;
  } catch (err) {
    console.error('Failed to fetch queue depth', err);
    return 0;
  }
}

async function estimateWaitSeconds() {
  const depth = await getQueueDepth();
  // Simple Erlang-ish approximation: depth / concurrent agents * avg handle time.
  // Replace with a proper Erlang-C model once real handle-time data exists.
  return Math.ceil(depth / ASSUMED_ACTIVE_AGENTS) * AVG_HANDLE_TIME_SECONDS;
}

// waitUrl for <Enqueue>: Twilio polls this repeatedly while the caller holds,
// so it re-announces an updated estimated wait and plays hold music.
router.post('/hold-music', async (req, res) => {
  const waitSecs = await estimateWaitSeconds();
  const twiml = new VoiceResponse();

  twiml.say(
    { voice: 'Polly.Joanna' },
    `You are still in the queue. Estimated wait is about ${Math.ceil(
      waitSecs / 60
    )} minutes.`
  );
  twiml.play('https://your-cdn.example.com/audio/hold-music-loop.mp3');

  res.type('text/xml').send(twiml.toString());
});

module.exports = { router, getQueueDepth, estimateWaitSeconds };
