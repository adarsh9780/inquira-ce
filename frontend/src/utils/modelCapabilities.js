export function modelSupportsImages(modelId) {
  const normalized = String(modelId || '').trim().toLowerCase()
  if (!normalized) return false
  return [
    'gpt-4o',
    'gpt-4.1',
    'gemini',
    'claude-3',
    'claude-sonnet-4',
    'llava',
    'vision',
    'pixtral',
    'qwen-vl',
    'moondream',
    'minicpm-v',
  ].some((marker) => normalized.includes(marker))
}

export const SUPPORTED_CHAT_IMAGE_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
  'image/gif',
])
