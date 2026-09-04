export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface ModelDefaults {
  guidance_scale: number;
  inf_steps: number;
  height: number;
  width: number;
  num_images_per_prompt: number;
}

export interface ModelCapabilities {
  supports_negative_prompt: boolean;
  supports_image_input: boolean;
  requires_image_input: boolean;
  supports_multi_image: boolean;
  max_images: number;
}

export interface ModelInfo {
  name: string;
  module: string;
  description: string;
  defaults: ModelDefaults;
  capabilities: ModelCapabilities;
}

export interface GeneratedArtifact {
  filename: string;
  path: string;
  media_type: string;
  size_bytes: number;
  download_url: string | null;
  seed: number | null;
}

export interface GenerationResult {
  model: string;
  prompt: string;
  output_dir: string;
  artifacts: GeneratedArtifact[];
  height: number;
  width: number;
  num_images_per_prompt: number;
  neg_prompt: string | null;
  guidance_scale: number | null;
  inf_steps: number;
  seed: number;
  device: string | null;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  source_prompt: string | null;
  llm_model: string | null;
}

export interface LlmModelInfo {
  id: string;
  provider: string;
  model: string;
  enabled: boolean;
}

export interface PromptEnhancement {
  model: string;
  system_prompt?: string | null;
  max_tokens?: number | null;
  temperature?: number | null;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: GenerationResult | null;
}

export interface ArtifactSummary {
  filename: string;
  download_url: string | null;
  seed: number | null;
}

export interface JobSummary {
  job_id: string;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  model: string;
  prompt: string;
  error: string | null;
  artifact_count: number;
  thumbnail_url: string | null;
  artifacts: ArtifactSummary[];
}

export interface JobListResponse {
  jobs: JobSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ModelDefaultOverride {
  guidance_scale?: number | null;
  inf_steps?: number | null;
  height?: number | null;
  width?: number | null;
  num_images_per_prompt?: number | null;
}

export interface BfsLoraConfig {
  source: string | null;
  weight_name: string | null;
  scale: number;
}

export interface LlmConfig {
  ollama: { base_url: string };
  lmstudio: { base_url: string };
  azure: { endpoint: string | null; api_version: string; deployments: string[] };
  bedrock: { region: string | null; model_ids: string[] };
  default_max_tokens: number;
  default_temperature: number;
  enabled_models: string[] | null;
}

export interface ServiceConfig {
  output_root: string;
  max_workers: number;
  default_model: string | null;
  bfs_lora: BfsLoraConfig;
  model_defaults: Record<string, ModelDefaultOverride>;
  llm: LlmConfig;
}

export interface GenerationRequest {
  model: string;
  prompt: string;
  height?: number | null;
  width?: number | null;
  num_images_per_prompt?: number | null;
  neg_prompt?: string | null;
  images?: string[] | null;
  guidance_scale?: number | null;
  inf_steps?: number | null;
  seed?: number;
  output_prefix?: string | null;
  test_gen?: { count: number; seed_inc: number } | null;
  enhance?: PromptEnhancement | null;
}

export interface JobSubmissionResponse {
  job_id: string;
  status: JobStatus;
  status_url: string;
  result_url: string;
}

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      // keep statusText
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  listModels: () => fetch("/models").then((r) => handle<ModelInfo[]>(r)),
  listLlmModels: () =>
    fetch("/llm/models").then((r) => handle<LlmModelInfo[]>(r)),
  getConfig: () => fetch("/config").then((r) => handle<ServiceConfig>(r)),
  putConfig: (config: ServiceConfig) =>
    fetch("/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }).then((r) => handle<ServiceConfig>(r)),
  submitJob: (request: GenerationRequest) =>
    fetch("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }).then((r) => handle<JobSubmissionResponse>(r)),
  getJob: (jobId: string) =>
    fetch(`/jobs/${jobId}`).then((r) => handle<JobStatusResponse>(r)),
  listJobs: (params: {
    limit?: number;
    offset?: number;
    model?: string;
    status?: string;
  }) => {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    if (params.model) query.set("model", params.model);
    if (params.status) query.set("status", params.status);
    return fetch(`/jobs?${query}`).then((r) => handle<JobListResponse>(r));
  },
  deleteJob: (jobId: string) =>
    fetch(`/jobs/${jobId}`, { method: "DELETE" }).then((r) => handle<void>(r)),
};
