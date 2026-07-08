import { useCallback, useState } from 'react'
import Cropper from 'react-easy-crop'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import type { CropAreaPixels } from './cropImage'
import { cropToDataUrl } from './cropImage'
import { useToast } from '../../components/ui/toast/useToast'

export function PhotoCropModal({
  open,
  onOpenChange,
  imageSrc,
  onCropped,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  imageSrc: string
  onCropped: (dataUrl: string) => void
}) {
  const toast = useToast()
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<CropAreaPixels | null>(null)

  const onCropComplete = useCallback((_area: unknown, areaPixels: CropAreaPixels) => {
    setCroppedAreaPixels(areaPixels)
  }, [])

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Crop photo"
      description="Crop to 1:1 (required)."
    >
      <div className="space-y-4">
        <div className="relative h-[320px] w-full overflow-hidden rounded-xl bg-black">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={1}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
          />
        </div>

        <div>
          <label className="text-sm font-medium">Zoom</label>
          <input
            className="mt-2 w-full"
            type="range"
            min={1}
            max={3}
            step={0.05}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          />
        </div>

        <div className="flex gap-2">
          <Button
            type="button"
            onClick={async () => {
              try {
                if (!croppedAreaPixels) {
                  toast.error('Crop not ready')
                  return
                }
                const out = await cropToDataUrl(imageSrc, croppedAreaPixels)
                onCropped(out)
                onOpenChange(false)
              } catch {
                toast.error('Failed to crop image')
              }
            }}
          >
            Confirm crop
          </Button>
          <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  )
}

