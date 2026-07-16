export function useVoiceInput() {
  function supportsSpeechRecognition() {
    if (typeof window === 'undefined') return false
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
  }

  return {
    supportsSpeechRecognition,
  }
}
