import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ResultImages, StatusBadge } from "../components";

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const { data: job, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "succeeded" || status === "failed" ? false : 1500;
    },
  });

  const deleteJob = useMutation({
    mutationFn: () => api.deleteJob(jobId!),
    onSuccess: () => navigate("/gallery"),
  });

  if (error) {
    return <div className="error-box">{(error as Error).message}</div>;
  }
  if (!job) return <div className="hint">Loading…</div>;

  const result = job.result;
  const running = job.status === "queued" || job.status === "running";

  return (
    <div>
      <div className="job-header">
        <div className="left">
          {running && <span className="spinner" />}
          <StatusBadge status={job.status} />
          <h1 style={{ margin: 0 }}>{job.job_id.slice(0, 8)}</h1>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="secondary" onClick={() => navigate("/gallery")}>
            Back
          </button>
          <button
            className="danger"
            disabled={running || deleteJob.isPending}
            onClick={() => {
              if (window.confirm("Delete this job and its images?")) {
                deleteJob.mutate();
              }
            }}
          >
            Delete
          </button>
        </div>
      </div>
      {deleteJob.isError && (
        <div className="error-box">{(deleteJob.error as Error).message}</div>
      )}
      {job.error && <div className="error-box">{job.error}</div>}
      {result && (
        <div className="panel">
          <ResultImages result={result} />
        </div>
      )}
      <div className="panel">
        <h2>Parameters</h2>
        <table className="params-table">
          <tbody>
            <tr>
              <td>Model</td>
              <td>{result?.model ?? "—"}</td>
            </tr>
            <tr>
              <td>Prompt</td>
              <td>{result?.prompt ?? "—"}</td>
            </tr>
            {result?.neg_prompt && (
              <tr>
                <td>Negative prompt</td>
                <td>{result.neg_prompt}</td>
              </tr>
            )}
            <tr>
              <td>Size</td>
              <td>
                {result ? `${result.width} × ${result.height}` : "—"}
              </td>
            </tr>
            <tr>
              <td>Steps / Guidance</td>
              <td>
                {result
                  ? `${result.inf_steps} / ${result.guidance_scale ?? "—"}`
                  : "—"}
              </td>
            </tr>
            <tr>
              <td>Seed</td>
              <td>{result?.seed ?? "—"}</td>
            </tr>
            <tr>
              <td>Device</td>
              <td>{result?.device ?? "—"}</td>
            </tr>
            <tr>
              <td>Created</td>
              <td>{new Date(job.created_at).toLocaleString()}</td>
            </tr>
            <tr>
              <td>Duration</td>
              <td>
                {result ? `${result.duration_seconds.toFixed(1)}s` : "—"}
              </td>
            </tr>
            <tr>
              <td>Output directory</td>
              <td>{result?.output_dir ?? "—"}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
