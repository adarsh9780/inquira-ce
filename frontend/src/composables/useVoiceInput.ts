type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: unknown
  webkitSpeechRecognition?: unknown
}

export function useVoiceInput() {
  function supportsSpeechRecognition(): boolean {
    if (typeof window === 'undefined') return false
    const speechWindow = window as SpeechRecognitionWindow
    return Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition)
  }

  return {
    supportsSpeechRecognition,
  }
}
