type PlotlyModule = typeof import('plotly.js-dist-min').default

let plotlyPromise: Promise<PlotlyModule> | null = null

export function loadPlotly(): Promise<PlotlyModule> {
  if (!plotlyPromise) {
    plotlyPromise = import('plotly.js-dist-min').then((module) => module.default)
  }
  return plotlyPromise
}
