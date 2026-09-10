import { useRef, useState } from "react";
import { ImageUp } from "lucide-react";

const ACCEPT = "image/png,image/jpeg,image/webp,image/bmp,image/tiff,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff";

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function DropZone({ onFile, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);

  function take(fileList: FileList | null) {
    const file = fileList?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload an image. Drop a file or press Enter to browse."
      className={`cursor-pointer rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-colors duration-200 ${
        active ? "border-accent bg-muted" : "border-white/15 bg-muted/60 hover:border-primary"
      } ${disabled ? "pointer-events-none opacity-50" : ""}`}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setActive(true);
      }}
      onDragLeave={() => setActive(false)}
      onDrop={(event) => {
        event.preventDefault();
        setActive(false);
        take(event.dataTransfer.files);
      }}
    >
      <ImageUp className="mx-auto h-10 w-10 text-accent" aria-hidden="true" />
      <p className="mt-4 font-heading text-lg">Drop a screenshot or photo</p>
      <p className="mt-2 text-sm text-white/70">PNG, JPEG, WebP, BMP, or TIFF. Original files are never overwritten.</p>
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept={ACCEPT}
        disabled={disabled}
        onChange={(event) => take(event.target.files)}
      />
    </div>
  );
}
