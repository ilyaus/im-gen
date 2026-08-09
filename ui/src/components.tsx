import { useState } from "react";
import type { GenerationResult, JobStatus } from "./api";
import Lightbox, { type LightboxImage } from "./Lightbox";
import {
  DownloadIcon,
  FailedIcon,
  QueuedIcon,
  RunningIcon,
  SuccessIcon,
} from "./icons";

export function StatusBadge({
  status,
  iconOnly,
}: {
  status: JobStatus;
  iconOnly?: boolean;
}) {
  const icon =
    status === "running" ? (
      <RunningIcon size={14} />
    ) : status === "succeeded" ? (
      <SuccessIcon size={14} />
    ) : status === "failed" ? (
      <FailedIcon size={14} />
    ) : (
      <QueuedIcon size={14} />
    );

  if (iconOnly) {
    return (
      <span className={`status-icon ${status}`} title={status}>
        {icon}
      </span>
    );
  }

  return <span className={`badge ${status}`}>{status}</span>;
}

export function ResultImages({ result }: { result: GenerationResult }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const images: LightboxImage[] = result.artifacts
    .filter((artifact) => artifact.download_url)
    .map((artifact) => ({
      url: artifact.download_url!,
      filename: artifact.filename,
      seed: artifact.seed,
    }));

  return (
    <>
      <div className="image-grid">
        {result.artifacts.map((artifact, index) => (
          <figure key={artifact.filename}>
            <div className="thumb-wrap">
              <button
                type="button"
                className="thumb-btn"
                onClick={() => setOpenIndex(index)}
                title="View full size"
              >
                <img
                  src={artifact.download_url ?? ""}
                  alt={artifact.filename}
                  loading="lazy"
                />
              </button>
              {artifact.download_url && (
                <a
                  className="icon-btn thumb-action"
                  href={artifact.download_url}
                  download={artifact.filename}
                  title="Download image"
                  onClick={(event) => event.stopPropagation()}
                >
                  <DownloadIcon size={15} />
                </a>
              )}
            </div>
            <figcaption>
              {artifact.filename}
              {artifact.seed !== null && ` · seed ${artifact.seed}`}
            </figcaption>
          </figure>
        ))}
      </div>
      {openIndex !== null && images[openIndex] && (
        <Lightbox
          images={images}
          index={openIndex}
          onIndexChange={setOpenIndex}
          onClose={() => setOpenIndex(null)}
        />
      )}
    </>
  );
}
