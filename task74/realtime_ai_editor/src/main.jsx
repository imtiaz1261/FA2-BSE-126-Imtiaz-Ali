import React from 'react'
import { createRoot } from 'react-dom/client'
import { EditorProvider } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Collaboration from '@tiptap/extension-collaboration'
import CollaborationCaret from '@tiptap/extension-collaboration-caret'
import Placeholder from '@tiptap/extension-placeholder'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import './styles.css'

const userId = crypto.randomUUID()
const colors = ['#7c3aed','#2563eb','#059669','#ea580c','#db2777']
const color = colors[Math.floor(Math.random()*colors.length)]
const userName = 'User ' + userId.slice(0,4)

const doc = new Y.Doc()
const provider = new WebsocketProvider(
  `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`,
  'demo-document',
  doc
)
provider.awareness.setLocalStateField('user', { name: userName, color })

function App() {
  const [editor, setEditor] = React.useState(null)
  const [commandOpen, setCommandOpen] = React.useState(false)
  const [suggestion, setSuggestion] = React.useState('')
  const [versions, setVersions] = React.useState([])
  const [busy, setBusy] = React.useState(false)
  const [lastSource, setLastSource] = React.useState('human')

  const loadVersions = React.useCallback(async () => {
    const r = await fetch('/api/versions/demo-document')
    setVersions(await r.json())
  }, [])

  React.useEffect(() => { loadVersions() }, [loadVersions])

  React.useEffect(() => {
    if (!editor) return
    const onUpdate = ({ transaction }) => {
      if (transaction.docChanged) {
        const source = transaction.getMeta('ai-source') ? 'ai' : 'human'
        setLastSource(source)
        fetch('/api/versions/demo-document', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            user: userName,
            source,
            text: editor.getText().slice(0, 5000)
          })
        }).then(loadVersions).catch(()=>{})
      }
    }
    editor.on('update', onUpdate)
    return () => editor.off('update', onUpdate)
  }, [editor, loadVersions])

  async function ai(action) {
    if (!editor) return
    setBusy(true)
    setCommandOpen(false)
    try {
      const r = await fetch('/api/ai', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          action,
          text: editor.getText().slice(0, 8000),
          selection: editor.state.doc.textBetween(editor.state.selection.from, editor.state.selection.to, '\\n')
        })
      })
      const data = await r.json()
      const output = data.text || ''
      if (action === 'autocomplete') {
        setSuggestion(output)
      } else {
        editor.chain().focus().insertContent(`\\n\\n${output}`).run()
      }
    } finally { setBusy(false) }
  }

  function acceptSuggestion() {
    if (!editor || !suggestion) return
    editor.chain().focus().insertContent(suggestion).run()
    setSuggestion('')
  }

  const extensions = [
    StarterKit.configure({ history: false }),
    Placeholder.configure({ placeholder: "Start writing… Type /ai for AI actions." }),
    Collaboration.configure({ document: doc }),
    CollaborationCaret.configure({
      provider,
      user: { name: userName, color }
    })
  ]

  return (
    <div className="app">
      <header>
        <div>
          <div className="brand">paper<span>•</span>ai</div>
          <div className="subtitle">Realtime collaborative workspace</div>
        </div>
        <div className="top-actions">
          <span className="presence">● {provider.awareness.getStates().size} online</span>
          <button onClick={() => ai('autocomplete')} disabled={busy}>AI autocomplete</button>
          <button className="dark" onClick={() => setCommandOpen(v=>!v)}>/ai</button>
        </div>
      </header>

      <main>
        <section className="editor-wrap">
          <div className="doc-meta">
            <span>Untitled document</span>
            <span className={lastSource==='ai' ? 'ai-tag':'human-tag'}>
              {lastSource === 'ai' ? 'AI edit' : 'Human edit'}
            </span>
          </div>
          <EditorProvider
            slotBefore={<Toolbar />}
            extensions={extensions}
            content="<h1>Welcome to your collaborative document</h1><p>Open this page in another browser tab and start typing. Everyone sees changes in real time.</p><h2>Try the AI</h2><p>Type <strong>/ai</strong> or use the AI autocomplete button.</p>"
            onCreate={({editor}) => setEditor(editor)}
          />
          {suggestion && (
            <div className="suggestion">
              <span>{suggestion}</span>
              <kbd>Tab</kbd>
              <button onClick={acceptSuggestion}>Accept</button>
            </div>
          )}
          {commandOpen && (
            <div className="command-menu">
              <div className="command-title">AI assistant</div>
              {[
                ['rewrite','Rewrite selection'],
                ['summarize','Summarize document'],
                ['continue','Continue writing'],
                ['autocomplete','Suggest next text']
              ].map(([id,label]) =>
                <button key={id} onClick={()=>ai(id)}>{label}<span>⌘</span></button>
              )}
            </div>
          )}
          <div className="footer">Connected via Yjs CRDT · Last change: {lastSource}</div>
        </section>

        <aside>
          <div className="side-title">Version history</div>
          {versions.length === 0 && <p className="muted">Edits will appear here.</p>}
          {versions.slice().reverse().map((v,i)=>(
            <div className="version" key={v.id || i}>
              <div className="dot"></div>
              <div>
                <strong>{v.source === 'ai' ? 'AI assistant' : v.user}</strong>
                <div className="small">{new Date(v.time).toLocaleTimeString()}</div>
                <p>{v.text?.slice(0,90)}{v.text?.length>90?'…':''}</p>
              </div>
            </div>
          ))}
        </aside>
      </main>
    </div>
  )
}

function Toolbar() {
  return <div className="toolbar">
    <button onClick={()=>document.execCommand('bold')}>B</button>
    <button onClick={()=>document.execCommand('italic')}>I</button>
    <button onClick={()=>document.execCommand('insertUnorderedList')}>• List</button>
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
