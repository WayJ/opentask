import { useEventListener } from '@vueuse/core';
import { isModK } from '@/utils/hotkeys';
import { useCommandPalette } from './use-command-palette';

/** S1: Meta/Ctrl+K toggles palette (allowed in inputs); Esc closes. Single-letter / ⌘B → S3. */
export function useAppHotkeys() {
  const palette = useCommandPalette();

  useEventListener(window, 'keydown', (event: KeyboardEvent) => {
    if (isModK(event)) {
      event.preventDefault();
      palette.toggle();
      return;
    }

    if (event.key === 'Escape' && palette.isOpen.value) {
      event.preventDefault();
      palette.close();
    }
  });
}
