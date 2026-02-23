import React, {useEffect, useState} from 'react'
import { Container, Textarea, Button, Group, Title, TextInput } from '@mantine/core'
import Settings from './Settings'

export default function App(){
  const [guilds, setGuilds] = useState(null)
  const isOauth = window.location.pathname === '/oauth-success'
  const [guildId, setGuildId] = useState('')
  const backendOrigin = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
  const [config, setConfig] = useState('{}')

  async function load(){
    if(!guildId) return
    const res = await fetch(`${backendOrigin}/api/guilds/${guildId}/config`, { credentials: 'include' })
    const data = await res.json()
    setConfig(JSON.stringify(data, null, 2))
    setParsedConfig(data)
  }

  const [parsedConfig, setParsedConfig] = useState(null)
  const [showSettings, setShowSettings] = useState(false)

  async function save(){
    if(!guildId) return
    try{
      const body = JSON.parse(config)
      const res = await fetch(`${backendOrigin}/api/guilds/${guildId}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-INTERNAL-TOKEN': '' },
        body: JSON.stringify(body)
      })
      if(res.ok) alert('Saved')
      else alert('Save failed')
    }catch(e){
      alert('Invalid JSON')
    }
  }

  useEffect(()=>{
    if(isOauth){
      ;(async ()=>{
        try{
          const r = await fetch(`${backendOrigin}/auth/me`, { credentials: 'include' })
          if(r.ok){
            const j = await r.json()
            setGuilds(j.guilds)
          } else {
            setGuilds([])
          }
        }catch(e){
          setGuilds([])
        }
      })()
    }
  },[])

  if(isOauth){
    return (
      <Container size="sm" style={{paddingTop:40}}>
        <Title order={2}>OAuth Success</Title>
        <div style={{marginTop:20}}>
          {guilds === null && <div>Loading guilds…</div>}
          {Array.isArray(guilds) && guilds.length === 0 && <div>No guilds or not authorized.</div>}
          {Array.isArray(guilds) && guilds.length > 0 && (
            <ul>
              {guilds.map(g=> <li key={g.id}>{g.name} ({g.id})</li>)}
            </ul>
          )}
          <div style={{marginTop:20}}>
            <a href="/">Back</a>
          </div>
        </div>
      </Container>
    )
  }

  return (
    <Container size="sm" style={{paddingTop:40}}>
      <Title order={2}>Bot Dashboard (MVP)</Title>
      <Group grow style={{marginTop:20}}>
        <TextInput placeholder="Guild ID" value={guildId} onChange={(e)=>setGuildId(e.target.value)} />
        <Button onClick={load}>Load</Button>
      </Group>

      <Textarea minRows={8} style={{marginTop:20, fontFamily:'monospace'}} value={config} onChange={(e)=>setConfig(e.target.value)} />
      <Group position="left" style={{marginTop:10}}>
        <Button onClick={()=>{ if(parsedConfig) setShowSettings(s=>!s) }} disabled={!parsedConfig}>{showSettings ? 'Hide Settings' : 'Edit Settings'}</Button>
      </Group>
      {showSettings && parsedConfig && (
        <Settings guildId={guildId} backendOrigin={backendOrigin} initialConfig={parsedConfig} onSaved={(b)=>{ setParsedConfig(b); setConfig(JSON.stringify(b, null, 2)) }} />
      )}
      <Group position="right" style={{marginTop:10}}>
        <Button onClick={save}>Save Config</Button>
      </Group>

      <Group position="left" style={{marginTop:20}}>
        <Button component="a" href={`${backendOrigin}/auth/login?state=${encodeURIComponent('local')}`}>Login with Discord</Button>
      </Group>
    </Container>
  )
}
