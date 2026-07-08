export type CropAreaPixels = { x: number; y: number; width: number; height: number }

function createImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.addEventListener('load', () => resolve(img))
    img.addEventListener('error', (e) => reject(e))
    img.src = url
  })
}

export async function cropToDataUrl(imageSrc: string, crop: CropAreaPixels): Promise<string> {
  const image = await createImage(imageSrc)
  const canvas = document.createElement('canvas')
  canvas.width = crop.width
  canvas.height = crop.height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas not supported')

  ctx.drawImage(
    image,
    crop.x,
    crop.y,
    crop.width,
    crop.height,
    0,
    0,
    crop.width,
    crop.height,
  )

  return canvas.toDataURL('image/jpeg', 0.92)
}

