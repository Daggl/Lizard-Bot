import React, {useState, useEffect} from 'react'
import { Button, Textarea, TextInput, Group, FileInput, Select, Image, Grid, Card, Text, Stack, Title } from '@mantine/core'

export default function Settings({guildId, backendOrigin, initialConfig, onSaved}){
  const cfg = initialConfig || {}
  const [welcome, setWelcome] = useState(cfg.welcome_message || '')
  const [announcementChannel, setAnnouncementChannel] = useState(cfg.announcement_channel_id || '')
  const [roleId, setRoleId] = useState(cfg.role_id || '')
  const [font, setFont] = useState(cfg.font || '')
  const [imagePath, setImagePath] = useState(cfg.image || '')
  const internalToken = import.meta.env.VITE_INTERNAL_TOKEN || ''
  const [channels, setChannels] = useState([])
  const [roles, setRoles] = useState([])

  useEffect(()=>{
    if(!guildId) return
    ;(async ()=>{
      try{
        // Prefer internal bot endpoint
        const ch = await fetch(`${backendOrigin}/api/guilds/${guildId}/channels`, { headers: { 'X-INTERNAL-TOKEN': internalToken } })
        if(ch.ok){
          const jc = await ch.json()
          setChannels(jc.map(c=>({ value: String(c.id), label: c.name || c.id })))
        }
      }catch(e){
        // ignore
      }

      try{
        const r = await fetch(`${backendOrigin}/api/guilds/${guildId}/roles`, { headers: { 'X-INTERNAL-TOKEN': internalToken } })
        if(r.ok){
          const jr = await r.json()
          setRoles(jr.map(r=>({ value: String(r.id), label: r.name || r.id })))
        }
      }catch(e){
        // ignore
      }
    })()
  },[guildId])

  useEffect(()=>{
    ;(async ()=>{
      try{
        const r = await fetch(`${backendOrigin}/api/fonts`)
        if(r.ok){
          const j = await r.json()
          // map to Select data
          const data = (j.fonts || []).map(f=>({ value: f, label: f }))
          if(data.length) setFont(data[0].value)
        }
      }catch(e){/*ignore*/}
    })()
  },[])

  const [previewUrl, setPreviewUrl] = useState(null)

  async function handleSave(){
    const body = {
      ...cfg,
      welcome_message: welcome,
      announcement_channel_id: announcementChannel,
      role_id: roleId,
      font: font,
      image: imagePath,
    }
    const res = await fetch(`${backendOrigin}/api/guilds/${guildId}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-INTERNAL-TOKEN': internalToken },
      body: JSON.stringify(body),
    })
    if(res.ok){
      alert('Saved')
      onSaved && onSaved(body)
    } else {
      alert('Save failed')
    }
  }

  async function handleUpload(file){
    if(!file) return
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${backendOrigin}/api/guilds/${guildId}/upload`, {
      method: 'POST',
      headers: { 'X-INTERNAL-TOKEN': internalToken },
      body: fd,
    })
    if(res.ok){
      const j = await res.json()
      // backend returns path relative to repo root. Use filename for preview endpoint
      const filename = file.name
      setImagePath(filename)
      alert('Upload successful')
    } else {
      alert('Upload failed')
    }
  }

  async function requestPreview(){
    const body = {
      welcome_message: welcome,
      announcement_channel_id: announcementChannel,
      role_id: roleId,
      font: font,
      image: imagePath,
    }
    const res = await fetch(`${backendOrigin}/api/guilds/${guildId}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-INTERNAL-TOKEN': internalToken },
      body: JSON.stringify(body),
    })
    if(res.ok){
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
    } else {
      alert('Preview generation failed')
    }
  }

  async function savePreview(){
    const body = {
      welcome_message: welcome,
      announcement_channel_id: announcementChannel,
      role_id: roleId,
      font: font,
      image: imagePath,
    }
    const res = await fetch(`${backendOrigin}/api/guilds/${guildId}/preview/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-INTERNAL-TOKEN': internalToken },
      body: JSON.stringify(body),
    })
    if(res.ok){
      const j = await res.json()
      setImagePath(j.path)
      alert('Preview saved to uploads')
    } else {
      alert('Save preview failed')
    }
  }

  return (
    <div style={{marginTop:20}}>
      <Grid>
        <Grid.Col span={7}>
          <Card shadow="sm" p="md">
            <Stack>
              <Title order={4}>Settings</Title>
              <TextInput label="Guild ID" value={guildId} readOnly />
              <Textarea label="Welcome Message" minRows={4} value={welcome} onChange={(e)=>setWelcome(e.target.value)} />
              <Select label="Announcement Channel" value={announcementChannel} onChange={setAnnouncementChannel} data={channels} searchable nothingFound="No channels" />
              <Select label="Role" value={roleId} onChange={setRoleId} data={roles} searchable nothingFound="No roles" />
              <Select label="Font" value={font} onChange={setFont} data={[{value:'Inter',label:'Inter'},{value:'Roboto',label:'Roboto'},{value:'Arial',label:'Arial'}]} />

              <div>
                <FileInput accept="image/*" label="Upload PNG/JPG" onChange={handleUpload} />
                {imagePath && (
                  <div style={{marginTop:10}}>
                    <div>Preview:</div>
                    <Image src={`${backendOrigin}/api/guilds/${guildId}/uploads/${imagePath}`} alt="uploaded" width={360} />
                  </div>
                )}
              </div>

                    <Group position="right">
                      <Button onClick={handleSave}>Save Settings</Button>
                      <Button variant="outline" onClick={requestPreview}>Generate Preview</Button>
                      <Button variant="light" onClick={savePreview}>Save Preview to Uploads</Button>
                    </Group>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={5}>
          <Card shadow="sm" p="md">
            <Title order={4}>Live Preview</Title>
            <div style={{marginTop:12}}>
              <div style={{border:'1px solid #e9ecef', borderRadius:8, padding:16, minHeight:220, display:'flex', alignItems:'center', justifyContent:'center', background:'#fff'}}>
                <div style={{textAlign:'center'}}>
                  {imagePath && (
                    <div style={{marginBottom:12}}>
                      <img src={`${backendOrigin}/api/guilds/${guildId}/uploads/${imagePath}`} alt="preview" style={{maxWidth:320, maxHeight:240, borderRadius:8}} />
                    </div>
                  )}
                  <div style={{fontFamily:font || 'Inter, Roboto, Arial, sans-serif'}}>
                    <Text size="lg" weight={600}>{welcome || 'Welcome to the server!'}</Text>
                    <Text size="sm" color="dimmed" style={{marginTop:8}}>Announcement channel: {announcementChannel || '—'}</Text>
                    <Text size="sm" color="dimmed">Role: {roleId || '—'}</Text>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </Grid.Col>
      </Grid>
    </div>
  )
}
