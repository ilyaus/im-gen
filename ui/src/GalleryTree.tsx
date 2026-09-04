import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { JobSummary } from "./api";
import { api } from "./api";
import { StatusBadge } from "./components";
import Lightbox, { type LightboxImage } from "./Lightbox";
import {
  CheckIcon,
  ChevronIcon,
  CollapseIcon,
  CopyIcon,
  DeleteIcon,
  DownloadIcon,
  ExpandIcon,
  FolderIcon,
} from "./icons";

type Grouping = "model" | "date";

interface JobGroup {
  key: string;
  label: string;
  jobs: JobSummary[];
}

interface TreeImage extends LightboxImage {
  key: string;
  jobId: string;
  prompt: string;
  model: string;
  createdAt: string;
}

function groupJobs(jobs: JobSummary[], grouping: Grouping): JobGroup[] {
  const groups = new Map<string, JobGroup>();
  for (const job of jobs) {
    let key: string;
    let label: string;
    if (grouping === "model") {
      key = job.model;
      label = job.model;
    } else {
      const created = new Date(job.created_at);
      key = created.toISOString().slice(0, 10);
      label = created.toLocaleDateString(undefined, {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    }
    let group = groups.get(key);
    if (!group) {
      group = { key, label, jobs: [] };
      groups.set(key, group);
    }
    group.jobs.push(job);
  }
  return [...groups.values()];
}

export default function GalleryTree({ jobs }: { jobs: JobSummary[] }) {
  const [grouping, setGrouping] = useState<Grouping>("model");
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(),
  );
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const autoExpanded = useRef(false);
  const queryClient = useQueryClient();

  const deleteJob = useMutation({
    mutationFn: (jobId: string) => api.deleteJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const groups = useMemo(() => groupJobs(jobs, grouping), [jobs, grouping]);

  const flatImages = useMemo(() => {
    const images: TreeImage[] = [];
    for (const group of groups) {
      for (const job of group.jobs) {
        for (const artifact of job.artifacts) {
          if (!artifact.download_url) continue;
          images.push({
            key: `${job.job_id}/${artifact.filename}`,
            url: artifact.download_url,
            filename: artifact.filename,
            seed: artifact.seed,
            context: `${job.model} · ${new Date(job.created_at).toLocaleString()}`,
            jobId: job.job_id,
            prompt: job.prompt,
            model: job.model,
            createdAt: job.created_at,
          });
        }
      }
    }
    return images;
  }, [groups]);

  const indexByKey = useMemo(() => {
    const map = new Map<string, number>();
    flatImages.forEach((image, index) => map.set(image.key, index));
    return map;
  }, [flatImages]);

  // Expand the first job that has images once, so leaves are visible on load.
  useEffect(() => {
    if (autoExpanded.current) return;
    for (const group of groups) {
      for (const job of group.jobs) {
        if (job.artifacts.length > 0) {
          autoExpanded.current = true;
          setExpandedJobs(new Set([job.job_id]));
          return;
        }
      }
    }
  }, [groups]);

  const selectedIndex =
    selectedKey !== null ? (indexByKey.get(selectedKey) ?? 0) : 0;
  const selected = flatImages.length > 0 ? flatImages[selectedIndex] : null;

  const selectedJobId = selected?.jobId;
  const { data: detailedJob } = useQuery({
    queryKey: ["job", selectedJobId],
    queryFn: () => api.getJob(selectedJobId!),
    enabled: Boolean(selectedJobId) && detailsOpen,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "succeeded" || status === "failed" ? false : 1500;
    },
  });

  const toggleGroup = (key: string) =>
    setCollapsedGroups((previous) => {
      const next = new Set(previous);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const toggleJob = (jobId: string) =>
    setExpandedJobs((previous) => {
      const next = new Set(previous);
      if (next.has(jobId)) next.delete(jobId);
      else next.add(jobId);
      return next;
    });

  const expandAll = () => {
    setCollapsedGroups(new Set());
    setExpandedJobs(
      new Set(groups.flatMap((group) => group.jobs.map((job) => job.job_id))),
    );
  };

  const collapseAll = () => {
    setCollapsedGroups(new Set(groups.map((group) => group.key)));
    setExpandedJobs(new Set());
  };

  const handleRowKeyDown =
    (action: () => void) => (event: React.KeyboardEvent) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        action();
      }
    };

  const copyPath = async () => {
    if (!selected) return;
    const fullUrl = `${window.location.origin}${selected.url}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = fullUrl;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <div className="tree-toolbar">
        <div className="segmented">
          <button
            type="button"
            className={grouping === "model" ? "active" : ""}
            onClick={() => setGrouping("model")}
          >
            By model
          </button>
          <button
            type="button"
            className={grouping === "date" ? "active" : ""}
            onClick={() => setGrouping("date")}
          >
            By date
          </button>
        </div>
        <div className="toolbar-spacer" />
        <button type="button" className="ghost-btn" onClick={expandAll}>
          <ExpandIcon size={14} /> Expand all
        </button>
        <button type="button" className="ghost-btn" onClick={collapseAll}>
          <CollapseIcon size={14} /> Collapse all
        </button>
      </div>
      <div className="browser">
        <div className="browser-tree">
          {groups.map((group) => {
            const groupOpen = !collapsedGroups.has(group.key);
            const imageCount = group.jobs.reduce(
              (count, job) => count + job.artifacts.length,
              0,
            );
            return (
              <section className="tree-group" key={group.key}>
                <button
                  type="button"
                  className="tree-row tree-row-group"
                  onClick={() => toggleGroup(group.key)}
                >
                  <ChevronIcon
                    className={`tree-chevron ${groupOpen ? "open" : ""}`}
                  />
                  <FolderIcon className="tree-folder" />
                  <span className="tree-label">{group.label}</span>
                  <span className="tree-count">
                    {group.jobs.length}{" "}
                    {group.jobs.length === 1 ? "job" : "jobs"} · {imageCount}{" "}
                    {imageCount === 1 ? "image" : "images"}
                  </span>
                </button>
                {groupOpen && (
                  <div className="tree-children">
                    {group.jobs.map((job) => {
                      const jobOpen = expandedJobs.has(job.job_id);
                      const running =
                        job.status === "queued" || job.status === "running";
                      return (
                        <div className="tree-job" key={job.job_id}>
                          <div
                            className="tree-row tree-row-job"
                            role="button"
                            tabIndex={0}
                            onClick={() => toggleJob(job.job_id)}
                            onKeyDown={handleRowKeyDown(() =>
                              toggleJob(job.job_id),
                            )}
                          >
                            <ChevronIcon
                              className={`tree-chevron ${jobOpen ? "open" : ""}`}
                            />
                            <StatusBadge status={job.status} iconOnly />
                            <span
                              className="tree-job-prompt"
                              title={job.prompt}
                            >
                              {job.prompt}
                            </span>
                            <span className="tree-job-meta">
                              {job.artifact_count}{" "}
                              {job.artifact_count === 1 ? "image" : "images"}
                            </span>
                            <button
                              type="button"
                              className="icon-btn tree-delete"
                              title="Delete job"
                              disabled={
                                running || deleteJob.isPending
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
                              <DeleteIcon size={16} />
                            </button>
                          </div>
                          {jobOpen && (
                            <div className="tree-leaf-list">
                              {job.artifacts.length === 0 && (
                                <div className="tree-leaf-empty hint">
                                  {job.status === "failed"
                                    ? `Job failed${job.error ? `: ${job.error}` : ""}`
                                    : "No images yet"}
                                </div>
                              )}
                              {job.artifacts.map(
                                (artifact) =>
                                  artifact.download_url && (
                                    <div
                                      key={artifact.filename}
                                      className={`tree-row tree-leaf-row${
                                        selectedKey ===
                                        `${job.job_id}/${artifact.filename}`
                                          ? " selected"
                                          : ""
                                      }`}
                                      role="button"
                                      tabIndex={0}
                                      title={artifact.filename}
                                      onClick={() =>
                                        setSelectedKey(
                                          `${job.job_id}/${artifact.filename}`,
                                        )
                                      }
                                      onKeyDown={handleRowKeyDown(() =>
                                        setSelectedKey(
                                          `${job.job_id}/${artifact.filename}`,
                                        ),
                                      )}
                                    >
                                      <img
                                        className="tree-mini-thumb"
                                        src={artifact.download_url}
                                        alt=""
                                        loading="lazy"
                                      />
                                      <span className="tree-leaf-filename">
                                        {artifact.filename}
                                      </span>
                                      <a
                                        className="icon-btn tree-leaf-download"
                                        href={artifact.download_url}
                                        download={artifact.filename}
                                        title="Download image"
                                        onClick={(event) =>
                                          event.stopPropagation()
                                        }
                                      >
                                        <DownloadIcon size={13} />
                                      </a>
                                    </div>
                                  ),
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            );
          })}
        </div>
        <aside className="browser-preview">
          {selected ? (
            <>
              <div className="preview-stage">
                <button
                  type="button"
                  className="preview-zoom"
                  onClick={() => setLightboxOpen(true)}
                  title="View fullscreen"
                >
                  <img src={selected.url} alt={selected.filename} />
                </button>
              </div>
              <div className="preview-meta">
                <div className="preview-filename-row">
                  <span className="preview-filename">{selected.filename}</span>
                  <button
                    type="button"
                    className="icon-btn preview-copy"
                    onClick={copyPath}
                    title={
                      copied
                        ? "Copied!"
                        : "Copy full image path to clipboard"
                    }
                  >
                    {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
                  </button>
                </div>
                <div className="hint">
                  {selected.model} ·{" "}
                  {new Date(selected.createdAt).toLocaleString()}
                  {selected.seed !== null && ` · seed ${selected.seed}`}
                </div>
                <p className="preview-prompt" title={selected.prompt}>
                  {selected.prompt}
                </p>
                <div className="preview-actions">
                  <a
                    className="btn-primary"
                    href={selected.url}
                    download={selected.filename}
                  >
                    <DownloadIcon size={15} /> Download
                  </a>
                </div>
              </div>
              <div className="preview-details">
                <button
                  type="button"
                  className="details-toggle"
                  onClick={() => setDetailsOpen((open) => !open)}
                >
                  <ChevronIcon
                    size={14}
                    className={detailsOpen ? "open" : ""}
                  />
                  Job details
                </button>
                {detailsOpen && (
                  <div className="preview-details-content">
                    {detailedJob ? (
                      detailedJob.result ? (
                        <table className="params-table">
                          <tbody>
                            <tr>
                              <td>Job ID</td>
                              <td>{detailedJob.job_id}</td>
                            </tr>
                            <tr>
                              <td>Status</td>
                              <td>{detailedJob.status}</td>
                            </tr>
                            <tr>
                              <td>Model</td>
                              <td>{detailedJob.result.model}</td>
                            </tr>
                            {detailedJob.result.source_prompt && (
                              <tr>
                                <td>Original prompt</td>
                                <td>{detailedJob.result.source_prompt}</td>
                              </tr>
                            )}
                            {detailedJob.result.llm_model && (
                              <tr>
                                <td>Enhanced by</td>
                                <td>{detailedJob.result.llm_model}</td>
                              </tr>
                            )}
                            <tr>
                              <td>Size</td>
                              <td>
                                {detailedJob.result.width} ×{" "}
                                {detailedJob.result.height}
                              </td>
                            </tr>
                            <tr>
                              <td>Steps / Guidance</td>
                              <td>
                                {detailedJob.result.inf_steps} /{" "}
                                {detailedJob.result.guidance_scale ?? "—"}
                              </td>
                            </tr>
                            <tr>
                              <td>Seed</td>
                              <td>{detailedJob.result.seed}</td>
                            </tr>
                            <tr>
                              <td>Device</td>
                              <td>{detailedJob.result.device ?? "—"}</td>
                            </tr>
                            <tr>
                              <td>Created</td>
                              <td>
                                {new Date(
                                  detailedJob.created_at,
                                ).toLocaleString()}
                              </td>
                            </tr>
                            <tr>
                              <td>Duration</td>
                              <td>
                                {detailedJob.result.duration_seconds.toFixed(1)}s
                              </td>
                            </tr>
                            <tr>
                              <td>Output directory</td>
                              <td>{detailedJob.result.output_dir}</td>
                            </tr>
                            {detailedJob.result.neg_prompt && (
                              <tr>
                                <td>Negative prompt</td>
                                <td>{detailedJob.result.neg_prompt}</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      ) : (
                        <div className="hint">
                          Parameters will appear when the job finishes.
                        </div>
                      )
                    ) : (
                      <div className="hint">Loading details…</div>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="preview-empty">
              <span className="hint">
                Select an image in the tree to preview it here.
              </span>
            </div>
          )}
        </aside>
      </div>
      {lightboxOpen && selected && (
        <Lightbox
          images={flatImages}
          index={selectedIndex}
          onIndexChange={(index) => setSelectedKey(flatImages[index].key)}
          onClose={() => setLightboxOpen(false)}
        />
      )}
    </>
  );
}
