export function shouldInitializeRuntime(isAuthenticated, runtimeInitialized) {
  return Boolean(isAuthenticated) && !Boolean(runtimeInitialized)
}
