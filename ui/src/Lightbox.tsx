import { useCallback, useEffect, useState } from "react";
import {
  CheckIcon,
  CloseIcon,
  CopyIcon,
  DownloadIcon,
  FitIcon,
  ZoomIcon,
} from "./icons";

export interface LightboxImage {
  url: string;
  filename: string;
  seed?: number | null;
  context?: string;
}

interface LightboxProps {
  images: LightboxImage[];
  index: number;
  onIndexChange: (index: number) => void;
  onClose: () => void;
}

export default function Lightbox({
  images,
  index,
  onIndexChange,
  onClose,
}: LightboxProps) {
  const [actualSize, setActualSize] = useState(false);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [copied, setCopied] = useState(false);

  const total = images.length;
  const image = total > 0 ? images[Math.min(index, total - 1)] : null;

  const showPrev = useCallback(() => {
    setActualSize(false);
    onIndexChange((index - 1 + total) % total);
  }, [index, total, onIndexChange]);

  const showNext = useCallback(() => {
    setActualSize(false);
    onIndexChange((index + 1) % total);
  }, [index, total, onIndexChange]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      else if (event.key === "ArrowLeft") showPrev();
      else if (event.key === "ArrowRight") showNext();
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose, showPrev, showNext]);

  useEffect(() => {
    setNatural(null);
    setCopied(false);
  }, [image?.url]);

  const copyPath = useCallback(async () => {
    if (!image) return;
    const fullUrl = `${window.location.origin}${image.url}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = fullUrl;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        // give up silently
      }
      document.body.removeChild(textarea);
    }
  }, [image]);

  if (!image) return null;

  return (
    <div className="lightbox-backdrop" onClick={onClose}>
      <div className="lightbox-toolbar" onClick={(e) => e.stopPropagation()}>
        <span className="lightbox-counter">
          {index + 1} / {total}
        </span>
        <span className="lightbox-title" title={image.filename}>
          {image.filename}
          {image.seed !== null && image.seed !== undefined && (
            <span className="lightbox-seed"> · seed {image.seed}</span>
          )}
          {natural && (
            <span className="lightbox-seed">
              {" "}
              · {natural.w} × {natural.h}
            </span>
          )}
          {image.context && (
            <span className="lightbox-context">{image.context}</span>
          )}
        </span>
        <button
          type="button"
          className="icon-btn lightbox-copy"
          onClick={copyPath}
          title={
            copied ? "Copied!" : "Copy full image path to clipboard"
          }
        >
          {copied ? <CheckIcon size={15} /> : <CopyIcon size={15} />}
        </button>
        <div className="lightbox-actions">
          <button
            type="button"
            className="lightbox-btn"
            onClick={() => setActualSize((value) => !value)}
            title={actualSize ? "Scale to fit" : "View at actual size"}
          >
            {actualSize ? <FitIcon size={18} /> : <ZoomIcon size={18} />}
            <span>{actualSize ? "Fit" : "1:1"}</span>
          </button>
          <a
            className="lightbox-btn"
            href={image.url}
            download={image.filename}
            title="Download image"
          >
            <DownloadIcon size={18} />
            <span>Download</span>
          </a>
          <button
            type="button"
            className="lightbox-btn"
            onClick={onClose}
            title="Close (Esc)"
          >
            <CloseIcon size={18} />
          </button>
        </div>
      </div>
      <div className="lightbox-stage" onClick={onClose}>
        <img
          src={image.url}
          alt={image.filename}
          className={actualSize ? "actual" : "fit"}
          onClick={(e) => e.stopPropagation()}
          onLoad={(e) =>
            setNatural({
              w: e.currentTarget.naturalWidth,
              h: e.currentTarget.naturalHeight,
            })
          }
        />
      </div>
      {total > 1 && (
        <>
          <button
            type="button"
            className="lightbox-nav prev"
            onClick={(e) => {
              e.stopPropagation();
              showPrev();
            }}
            title="Previous (←)"
          >
            ‹
          </button>
          <button
            type="button"
            className="lightbox-nav next"
            onClick={(e) => {
              e.stopPropagation();
              showNext();
            }}
            title="Next (→)"
          >
            ›
          </button>
        </>
      )}
    </div>
  );
}
