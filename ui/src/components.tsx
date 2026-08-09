import type { GenerationResult, JobStatus } from "./api";

export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`badge ${status}`}>{status}</span>;
}

export function ResultImages({ result }: { result: GenerationResult }) {
  return (
    <div className="image-grid">
      {result.artifacts.map((artifact) => (
        <figure key={artifact.filename}>
          <a
            href={artifact.download_url ?? "#"}
            target="_blank"
            rel="noreferrer"
          >
            <img src={artifact.download_url ?? ""} alt={artifact.filename} />
          </a>
          <figcaption>
            {artifact.filename}
            {artifact.seed !== null && ` · seed ${artifact.seed}`}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
