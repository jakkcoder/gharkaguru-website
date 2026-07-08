import '@testing-library/jest-dom/vitest'

// Ensure deterministic IDs in tests
if (!globalThis.crypto?.randomUUID) {
  // @ts-expect-error test polyfill
  globalThis.crypto = {
    randomUUID: () => '00000000-0000-0000-0000-000000000000',
  }
}

