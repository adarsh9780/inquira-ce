/// <reference types="vite/client" />

declare const __APP_VERSION__: string

interface Window {
  go?: {
    main?: {
      App?: Record<string, (...arguments_: unknown[]) => Promise<unknown>>
    }
  }
  runtime?: {
    EventsOnMultiple?: (
      name: string,
      callback: (payload: unknown) => void,
      maxCallbacks: number,
    ) => (() => void) | void
  }
}
