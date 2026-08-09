import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { StatusBadge } from "../components";
import GalleryTree from "../GalleryTree";
import Lightbox, { type LightboxImage } from "../Lightbox";
import { DeleteIcon, DownloadIcon, GridIcon, TreeIcon } from "../icons";

const PAGE_SIZE = 24;
const TREE_LIMIT = 100;
const VIEW_STORAGE_KEY = "im-gen-gallery-view";

type ViewMode = "grid" | "tree";

function getStoredView(): ViewMode {
  return localStorage.getItem(VIEW_STORAGE_KEY) === "tree" ? "tree" : "grid";
}

export default function GalleryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [modelFilter, setModelFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const [view, setViewState] = useState<ViewMode>(getStoredView);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const deleteJob = useMutation({
    mutationFn: (jobId: string) => api.deleteJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const setView = (next: ViewMode) => {
    setViewState(next);
    localStorage.setItem(VIEW_STORAGE_KEY, next);
  };

  const { data: models } = useQuery({
    queryKey: ["models"],
    queryFn: api.listModels,
  });
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs", modelFilter, statusFilter, page, view],
    queryFn: () =>
      api.listJobs({
        limit: view === "tree" ? TREE_LIMIT : PAGE_SIZE,
        offset: view === "tree" ? 0 : page * PAGE_SIZE,
        model: modelFilter || undefined,
        status: statusFilter || undefined,
      }),
    refetchInterval: 5000,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const flatImages: LightboxImage[] = useMemo(() => {
    if (!data) return [];
    return data.jobs.flatMap((job) =>
      job.artifacts
        .filter((artifact) => artifact.download_url)
        .map((artifact) => ({
          url: artifact.download_url!,
          filename: artifact.filename,
          seed: artifact.seed,
          context: `${job.model} · ${new Date(job.created_at).toLocaleString()}`,
        })),
    );
  }, [data]);

  return (
    <div>
      <div className="page-header">
        <h1>Gallery</h1>
        <div className="segmented view-toggle">
          <button
            type="button"
            className={view === "grid" ? "active" : ""}
            onClick={() => setView("grid")}
            title="Grid view"
          >
            <GridIcon size={14} /> Grid
          </button>
          <button
            type="button"
            className={view === "tree" ? "active" : ""}
            onClick={() => setView("tree")}
            title="Tree view"
          >
            <TreeIcon size={14} /> Tree
          </button>
        </div>
      </div>
      <div className="filters">
        <div>
          <label>Model</label>
          <select
            value={modelFilter}
            onChange={(event) => {
              setModelFilter(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All models</option>
            {models?.map((model) => (
              <option key={model.name} value={model.name}>
                {model.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Status</label>
          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All statuses</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
          </select>
        </div>
      </div>
      {error && <div className="error-box">{(error as Error).message}</div>}
      {isLoading && <div className="hint">Loading…</div>}
      {data && data.jobs.length === 0 && (
        <div className="panel">
          <span className="hint">No jobs found.</span>
        </div>
      )}
      {data && data.jobs.length > 0 && view === "tree" && (
        <>
          <GalleryTree jobs={data.jobs} />
          {data.total > data.jobs.length && (
            <div className="hint" style={{ marginTop: 12 }}>
              Showing the latest {data.jobs.length} of {data.total} jobs. Use
              the filters to narrow down, or switch to grid view for pagination.
            </div>
          )}
        </>
      )}
      {view === "grid" && (
        <div className="gallery-grid">
          {data?.jobs.map((job) => {
            const firstImageIndex = flatImages.findIndex(
              (image) =>
                image.url ===
                (job.artifacts.find((artifact) => artifact.download_url)
                  ?.download_url ?? null),
            );
            const firstArtifact = job.artifacts.find(
              (artifact) => artifact.download_url,
            );
            return (
              <div key={job.job_id} className="job-card">
                <div
                  className="thumb-wrap card-thumb"
                  onClick={() => {
                    if (firstImageIndex >= 0) setLightboxIndex(firstImageIndex);
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (
                      (event.key === "Enter" || event.key === " ") &&
                      firstImageIndex >= 0
                    ) {
                      event.preventDefault();
                      setLightboxIndex(firstImageIndex);
                    }
                  }}
                  title={
                    firstImageIndex >= 0 ? "View full size" : job.prompt
                  }
                >
                  {job.thumbnail_url ? (
                    <img
                      className="thumb"
                      src={job.thumbnail_url}
                      alt={job.prompt}
                      loading="lazy"
                    />
                  ) : (
                    <div className="thumb-placeholder">
                      {job.status === "failed" ? "failed" : "no image yet"}
                    </div>
                  )}
                  <div className="card-actions">
                    {firstArtifact?.download_url && (
                      <a
                        className="icon-btn thumb-action"
                        href={firstArtifact.download_url}
                        download={firstArtifact.filename}
                        title="Download image"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <DownloadIcon size={14} />
                      </a>
                    )}
                    <button
                      type="button"
                      className="icon-btn thumb-action danger"
                      title="Delete job"
                      disabled={
                        job.status === "queued" ||
                        job.status === "running" ||
                        deleteJob.isPending
                      }
                      onClick={(event) => {
                        event.stopPropagation();
                        if (
                          window.confirm(
                            `Delete job ${job.job_id.slice(0, 8)} and its images?`,
                          )
                        ) {
                          deleteJob.mutate(job.job_id);
                        }
                      }}
                    >
                      <DeleteIcon size={14} />
                    </button>
                  </div>
                </div>
                <div
                  className="meta"
                  onClick={() => navigate(`/gallery/${job.job_id}`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(`/gallery/${job.job_id}`);
                    }
                  }}
                  title="Open job details"
                >
                  <StatusBadge status={job.status} />
                  <div className="prompt" title={job.prompt}>
                    {job.prompt}
                  </div>
                  <div className="model">
                    {job.model} · {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {lightboxIndex !== null && flatImages[lightboxIndex] && (
        <Lightbox
          images={flatImages}
          index={lightboxIndex}
          onIndexChange={setLightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
      {view === "grid" && data && data.total > PAGE_SIZE && (
        <div className="pagination">
          <button
            className="secondary"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <span>
            Page {page + 1} of {totalPages} ({data.total} jobs)
          </span>
          <button
            className="secondary"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
