export function parseSseBuffer(buffer) {
  const events = []
  const chunks = buffer.split('\n\n')
  const remainder = chunks.pop() || ''

  for (const chunk of chunks) {
    if (!chunk.trim()) continue
    const lines = chunk.split('\n')
    let event = 'message'
    const dataLines = []

    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }

    const dataText = dataLines.join('\n')
    let data = dataText
    if (dataText) {
      try {
        data = JSON.parse(dataText)
      } catch {
        data = dataText
      }
    }

    events.push({ event, data })
  }

  return { events, remainder }
}
