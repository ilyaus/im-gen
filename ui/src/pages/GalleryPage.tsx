import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { StatusBadge } from "../components";

const PAGE_SIZE = 24;

export default function GalleryPage() {
  const navigate = useNavigate();
  const [modelFilter, setModelFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);

  const { data: models } = useQuery({
    queryKey: ["models"],
    queryFn: api.listModels,
  });
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs", modelFilter, statusFilter, page],
    queryFn: () =>
      api.listJobs({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        model: modelFilter || undefined,
        status: statusFilter || undefined,
      }),
    refetchInterval: 5000,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <h1>Gallery</h1>
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
      <div className="gallery-grid">
        {data?.jobs.map((job) => (
          <div
            key={job.job_id}
            className="job-card"
            onClick={() => navigate(`/gallery/${job.job_id}`)}
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
            <div className="meta">
              <StatusBadge status={job.status} />
              <div className="prompt" title={job.prompt}>
                {job.prompt}
              </div>
              <div className="model">
                {job.model} · {new Date(job.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        ))}
      </div>
      {data && data.total > PAGE_SIZE && (
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
