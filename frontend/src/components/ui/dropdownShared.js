export const dropdownSurfaceClass = 'layer-modal-dropdown fixed overflow-auto rounded-md py-1 shadow-md focus:outline-none'

export const dropdownSearchRowClass = 'sticky top-0 z-10 px-2 pb-1 pt-1'

export const dropdownSearchInputClass = 'w-full rounded-md border px-2 py-1 text-[12px] focus:outline-none'

export const dropdownGroupLabelClass = 'px-3 py-1 text-[11px] font-semibold uppercase tracking-wide'

export const dropdownEmptyClass = 'px-3 py-2 text-[12px]'

export const dropdownOptionClass = 'relative cursor-default select-none py-2 text-[13px]'

export function dropdownSurfaceStyle({ surface = 'var(--color-surface)', border = 'var(--color-border)' } = {}) {
  return {
    backgroundColor: surface,
    border: `1px solid ${border}`,
  }
}

export const dropdownSearchRowStyle = {
  backgroundColor: 'var(--color-surface)',
  borderBottom: '1px solid var(--color-border)',
}

export const dropdownSearchInputStyle = {
  backgroundColor: 'var(--color-base)',
  borderColor: 'var(--color-border)',
  color: 'var(--color-text-main)',
}

export const dropdownMutedTextStyle = {
  color: 'var(--color-text-muted)',
}

export function dropdownOptionStyle(active, { activeMix = 'var(--color-text-main) 6%' } = {}) {
  return {
    backgroundColor: active ? `color-mix(in srgb, ${activeMix}, transparent)` : 'transparent',
    color: 'var(--color-text-main)',
  }
}
