require('dotenv').config()
const http = require('http')
const express = require('express')
const cors = require('cors')
const path = require('path')
const fs = require('fs')
const OpenAI = require('openai')
const { setupWSConnection } = require('y-websocket/bin/utils')

const app = express()
app.use(cors())
app.use(express.json({limit:'1mb'}))

const dataDir = path.join(__dirname, 'data')
fs.mkdirSync(dataDir, {recursive:true})
const versionFile = path.join(dataDir, 'versions.json')
if (!fs.existsSync(versionFile)) fs.writeFileSync(versionFile, '[]')

function versions() {
  try { return JSON.parse(fs.readFileSync(versionFile,'utf8')) } catch { return [] }
}

app.get('/api/versions/:doc', (req,res) => {
  res.json(versions().filter(v => v.doc === req.params.doc).slice(-100))
})

app.post('/api/versions/:doc', (req,res) => {
  const all = versions()
  all.push({
    id: crypto.randomUUID(),
    doc:req.params.doc,
    time:Date.now(),
    user:req.body.user || 'Unknown',
    source:req.body.source === 'ai' ? 'ai' : 'human',
    text:req.body.text || ''
  })
  fs.writeFileSync(versionFile, JSON.stringify(all.slice(-1000),null,2))
  res.json({ok:true})
})

app.post('/api/ai', async (req,res) => {
  const {action,text,selection} = req.body
  const promptMap = {
    rewrite: `Rewrite the selected text clearly and naturally. Preserve meaning. Selected text:\\n${selection || text}`,
    summarize: `Summarize the document in concise prose.\\n${text}`,
    continue: `Continue writing the document in the same tone. Return only the continuation.\\n${text}`,
    autocomplete: `Predict a useful next sentence or short phrase for this document. Return only the suggestion, no quotes.\\n${text}`
  }
  if (!promptMap[action]) return res.status(400).json({error:'Unknown action'})

  if (!process.env.GROQ_API_KEY) {
    const demo = {
      rewrite:'Here is a clearer, more polished version of the selected text.',
      summarize:'This document explains a collaborative editor with real-time editing and an integrated AI assistant.',
      continue:'The next step is to refine the workflow and make collaboration feel effortless.',
      autocomplete:' while keeping the writing clear, focused, and easy to collaborate on.'
    }
    return res.json({text:demo[action]})
  }

  try {
    const client = new OpenAI({
      apiKey: process.env.GROQ_API_KEY,
      baseURL: 'https://api.groq.com/openai/v1'
    })
    const response = await client.chat.completions.create({
      model:process.env.GROQ_MODEL || 'openai/gpt-oss-20b',
      messages:[
        {role:'system',content:'You are an inline writing assistant. Be concise. Never add meta-commentary.'},
        {role:'user',content:promptMap[action]}
      ],
      temperature:0.4
    })
    res.json({text:response.choices[0].message.content.trim()})
  } catch(e) {
    res.status(500).json({error:e.message})
  }
})

const server = http.createServer(app)
const wss = new (require('ws').WebSocketServer)({noServer:true})
server.on('upgrade', (request,socket,head) => {
  if (!request.url.startsWith('/ws')) return socket.destroy()
  wss.handleUpgrade(request,socket,head,ws => {
    wss.emit('connection',ws,request)
  })
})
wss.on('connection',(conn,req) => setupWSConnection(conn,req,{gc:true}))

const clientDir = path.join(__dirname,'..','dist')
if (fs.existsSync(clientDir)) {
  app.use(express.static(clientDir))
  app.get('*',(req,res)=>res.sendFile(path.join(clientDir,'index.html')))
}

const port = process.env.PORT || 1234
server.listen(port,()=>console.log(`Server running on http://localhost:${port}`))
