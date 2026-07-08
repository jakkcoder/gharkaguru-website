import fs from 'node:fs/promises'
import path from 'node:path'
import sharp from 'sharp'

const ROOT = path.resolve(process.cwd())
const DIR = path.join(ROOT, 'public', 'assets', 'stock')

function profileFor(name) {
  if (name.startsWith('hero-')) return { maxWidth: 1400, quality: 62 }
  if (name.startsWith('promo-')) return { maxWidth: 1100, quality: 62 }
  if (name.startsWith('cat-')) return { maxWidth: 700, quality: 60 }
  if (name.startsWith('tutor-')) return { maxWidth: 360, quality: 60 }
  if (name.startsWith('gallery-')) return { maxWidth: 1000, quality: 62 }
  return { maxWidth: 900, quality: 62 }
}

function fmtBytes(n) {
  const units = ['B', 'KB', 'MB', 'GB']
  let u = 0
  let x = n
  while (x >= 1024 && u < units.length - 1) {
    x /= 1024
    u++
  }
  return `${x.toFixed(u === 0 ? 0 : 1)} ${units[u]}`
}

async function main() {
  const entries = await fs.readdir(DIR, { withFileTypes: true })
  const files = entries
    .filter((e) => e.isFile() && e.name.toLowerCase().endsWith('.jpg'))
    .map((e) => e.name)
    .sort()

  if (!files.length) {
    console.log(`No .jpg files found in ${DIR}`)
    return
  }

  let totalBefore = 0
  let totalAfter = 0

  for (const name of files) {
    const input = path.join(DIR, name)
    const tmp = path.join(DIR, `${name}.tmp`)

    const beforeStat = await fs.stat(input)
    totalBefore += beforeStat.size

    const { maxWidth, quality } = profileFor(name)

    const img = sharp(input, { failOn: 'none' })
    const meta = await img.metadata()
    const width = meta.width ?? maxWidth
    const resizeWidth = Math.min(width, maxWidth)

    await img
      .rotate() // respect EXIF orientation
      .resize({ width: resizeWidth, withoutEnlargement: true })
      .jpeg({
        quality,
        progressive: true,
        mozjpeg: true,
      })
      .toFile(tmp)

    const afterStat = await fs.stat(tmp)
    totalAfter += afterStat.size

    // Replace original
    await fs.rename(tmp, input)

    const saved = beforeStat.size - afterStat.size
    const pct = beforeStat.size ? ((saved / beforeStat.size) * 100).toFixed(1) : '0.0'
    console.log(
      `${name}: ${fmtBytes(beforeStat.size)} → ${fmtBytes(afterStat.size)} (saved ${fmtBytes(saved)} / ${pct}%)`,
    )
  }

  const savedTotal = totalBefore - totalAfter
  const pctTotal = totalBefore ? ((savedTotal / totalBefore) * 100).toFixed(1) : '0.0'
  console.log(`\nTOTAL: ${fmtBytes(totalBefore)} → ${fmtBytes(totalAfter)} (saved ${fmtBytes(savedTotal)} / ${pctTotal}%)`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})

