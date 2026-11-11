export interface PolicyNameState {
  dirty: boolean;
  loaded: boolean;
  current: string;
}

/** Suggested names apply only to a new policy the user has not typed into and has not loaded. */
export function policyNameAfterLocaleChange(state: PolicyNameState, suggested: string): string {
  if (state.dirty || state.loaded) return state.current;
  return suggested;
}
