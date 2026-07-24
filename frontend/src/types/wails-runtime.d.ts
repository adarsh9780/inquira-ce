declare module '*wailsjs/runtime/runtime.js' {
  export function EventsOn(
    eventName: string,
    callback: (...data: unknown[]) => void,
  ): () => void
}

declare module '*wailsjs/runtime/runtime' {
  export function EventsOn(
    eventName: string,
    callback: (...data: unknown[]) => void,
  ): () => void
}
