/// <reference types="vite/client" />

declare const __APP_VERSION__: string

declare module 'plotly.js-dist-min' {
  const Plotly: {
    newPlot: (...arguments_: any[]) => Promise<unknown>
    purge: (...arguments_: any[]) => void
    toImage: (...arguments_: any[]) => Promise<string>
    Plots: { resize: (...arguments_: any[]) => void }
  }
  export default Plotly
}

declare module 'markdown-it'
declare module 'prismjs'
declare module 'prismjs/components/prism-python'
declare module 'prismjs/components/prism-sql'

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
