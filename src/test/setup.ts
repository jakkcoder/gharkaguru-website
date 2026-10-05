import '@testing-library/jest-dom/vitest'

if (typeof localStorage === 'undefined' || typeof localStorage.clear !== 'function') {
  const store = new Map<string, string>()
  const memoryStorage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, String(value))
    },
    removeItem: (key: string) => {
      store.delete(key)
    },
    clear: () => {
      store.clear()
    },
    key: (index: number) => [...store.keys()][index] ?? null,
    get length() {
      return store.size
    },
  }
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: memoryStorage })
}

// Ensure deterministic IDs in tests
if (!globalThis.crypto?.randomUUID) {
  // @ts-expect-error test polyfill
  globalThis.crypto = {
    randomUUID: () => '00000000-0000-0000-0000-000000000000',
  }
}

