/**
 * Prepare Vite dist/ for static bucket hosting (GCS, S3, etc.).
 * - SPA fallback: copy index.html → 404.html
 * - Remove dev-only MSW worker from the upload bundle
 */
import { copyFileSync, existsSync, rmSync } from 'node:fs'
import { join } from 'node:path'

const dist = join(import.meta.dirname, '..', 'dist')
const index = join(dist, 'index.html')
const notFound = join(dist, '404.html')
const msw = join(dist, 'mockServiceWorker.js')

if (!existsSync(index)) {
  console.error('dist/index.html not found — run "npm run build" first.')
  process.exit(1)
}

copyFileSync(index, notFound)
console.log('Created dist/404.html (SPA fallback for bucket hosting)')

if (existsSync(msw)) {
  rmSync(msw)
  console.log('Removed dist/mockServiceWorker.js (dev-only)')
}

console.log('\nUpload the contents of dist/ to your bucket:')
console.log('  gcloud storage rsync -r dist/ gs://YOUR-BUCKET/')
