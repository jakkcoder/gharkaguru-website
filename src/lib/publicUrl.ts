/** Public asset path with Vite base (e.g. /gharkaguru-website/ on GCS, / on custom domain). */
export function publicUrl(path: string) {
  const normalized = path.startsWith('/') ? path.slice(1) : path
  return `${import.meta.env.BASE_URL}${normalized}`
}

export function routerBasename() {
  return import.meta.env.BASE_URL.replace(/\/$/, '')
}
