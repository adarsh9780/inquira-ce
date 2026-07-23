export type ThemeId = 'foundry' | 'bluehour'

export interface ProviderSummary {
  id: string
  label: string
  openai_compatible: boolean
  api_key_present: boolean
  base_url?: string
}

export interface ModelSummary {
  id: string
  name: string
  provider: string
  supports_tools?: boolean
  supports_structured_output?: boolean
  context_window?: number
}

export interface Preferences {
  ui_theme: ThemeId
  app_font: string
  code_font: string
  llm_provider?: string
  selected_model?: string
  slow_request_warning_seconds: number
  allow_llm_data_samples: boolean
}

export interface WorkspaceModelConfiguration {
  provider?: string
  main_model?: string
  lite_model?: string
  coding_model?: string
  allow_llm_data_samples: boolean
  configuration_reviewed: boolean
}
