import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  api,
  type GenerationRequest,
  type ModelDefaults,
  type ModelInfo,
  type ServiceConfig,
} from "../api";
import { ResultImages, StatusBadge } from "../components";

function randomSeed(): number {
  return Math.floor(Math.random() * 1_000_000_000_000);
}

function effectiveDefaults(
  model: ModelInfo,
  config: ServiceConfig | undefined,
): ModelDefaults {
  const override = config?.model_defaults?.[model.name] ?? {};
  return {
    guidance_scale: override.guidance_scale ?? model.defaults.guidance_scale,
    inf_steps: override.inf_steps ?? model.defaults.inf_steps,
    height: override.height ?? model.defaults.height,
    width: override.width ?? model.defaults.width,
    num_images_per_prompt:
      override.num_images_per_prompt ?? model.defaults.num_images_per_prompt,
  };
}

function JobCard({ jobId }: { jobId: string }) {
  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "succeeded" || status === "failed" ? false : 1500;
    },
  });

  if (!job) return null;
  const running = job.status === "queued" || job.status === "running";
  return (
    <div className="panel">
      <div className="job-header">
        <div className="left">
          {running && <span className="spinner" />}
          <StatusBadge status={job.status} />
          <span className="model">{jobId.slice(0, 8)}</span>
        </div>
        {job.result && (
          <span className="hint">
            {job.result.duration_seconds.toFixed(1)}s · seed {job.result.seed}
          </span>
        )}
      </div>
      {job.error && <div className="error-box">{job.error}</div>}
      {job.result?.llm_model && (
        <div className="enhanced-prompt-box">
          <span className="enhanced-prompt-label">
            Enhanced by {job.result.llm_model}
          </span>
          {job.result.prompt}
        </div>
      )}
      {job.result && <ResultImages result={job.result} />}
    </div>
  );
}

export default function GeneratePage() {
  const { data: models } = useQuery({
    queryKey: ["models"],
    queryFn: api.listModels,
  });
  const { data: config } = useQuery({
    queryKey: ["config"],
    queryFn: api.getConfig,
  });
  const { data: llmModels } = useQuery({
    queryKey: ["llm-models"],
    queryFn: api.listLlmModels,
    refetchInterval: 30000,
  });

  const [modelName, setModelName] = useState<string>("");
  const [prompt, setPrompt] = useState("");
  const [negPrompt, setNegPrompt] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [llmMaxTokens, setLlmMaxTokens] = useState(512);
  const [llmTemperature, setLlmTemperature] = useState(0.7);
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [steps, setSteps] = useState(4);
  const [guidance, setGuidance] = useState(1.0);
  const [seed, setSeed] = useState<number>(randomSeed());
  const [randomSeedEnabled, setRandomSeedEnabled] = useState(true);
  const [numImages, setNumImages] = useState(1);
  const [images, setImages] = useState("");
  const [sweepEnabled, setSweepEnabled] = useState(false);
  const [sweepCount, setSweepCount] = useState(4);
  const [sweepInc, setSweepInc] = useState(1);
  const [jobIds, setJobIds] = useState<string[]>([]);

  const model = useMemo(
    () => models?.find((entry) => entry.name === modelName),
    [models, modelName],
  );

  useEffect(() => {
    if (!models || models.length === 0 || modelName) return;
    const initial =
      (config?.default_model &&
        models.find((entry) => entry.name === config.default_model)?.name) ||
      models[0].name;
    setModelName(initial);
  }, [models, config, modelName]);

  useEffect(() => {
    if (!model) return;
    const defaults = effectiveDefaults(model, config);
    setWidth(defaults.width);
    setHeight(defaults.height);
    setSteps(defaults.inf_steps);
    setGuidance(defaults.guidance_scale);
    setNumImages(defaults.num_images_per_prompt);
  }, [model, config]);

  useEffect(() => {
    if (!config?.llm) return;
    setLlmMaxTokens(config.llm.default_max_tokens);
    setLlmTemperature(config.llm.default_temperature);
  }, [config]);

  useEffect(() => {
    if (
      llmModel &&
      llmModels &&
      !llmModels.some((m) => m.id === llmModel && m.enabled)
    ) {
      setLlmModel("");
    }
  }, [llmModels, llmModel]);

  const submit = useMutation({
    mutationFn: (request: GenerationRequest) => api.submitJob(request),
    onSuccess: (response) => {
      setJobIds((previous) => [response.job_id, ...previous]);
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!model) return;
    const imagePaths = images
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
    submit.mutate({
      model: model.name,
      prompt,
      neg_prompt:
        model.capabilities.supports_negative_prompt && negPrompt
          ? negPrompt
          : null,
      width,
      height,
      inf_steps: steps,
      guidance_scale: guidance,
      ...(randomSeedEnabled ? {} : { seed }),
      num_images_per_prompt: sweepEnabled ? 1 : numImages,
      images: imagePaths.length > 0 ? imagePaths : null,
      test_gen: sweepEnabled
        ? { count: sweepCount, seed_inc: sweepInc }
        : null,
      enhance: llmModel
        ? {
            model: llmModel,
            system_prompt: systemPrompt || null,
            max_tokens: llmMaxTokens,
            temperature: llmTemperature,
          }
        : null,
    });
  };

  return (
    <div className="grid-2">
      <form className="panel" onSubmit={handleSubmit}>
        <h1>Generate</h1>
        {submit.isError && (
          <div className="error-box">{(submit.error as Error).message}</div>
        )}
        <div className="field">
          <label>Model</label>
          <select
            value={modelName}
            onChange={(event) => setModelName(event.target.value)}
          >
            {models?.map((entry) => (
              <option key={entry.name} value={entry.name}>
                {entry.name}
              </option>
            ))}
          </select>
          {model && <div className="hint">{model.description}</div>}
        </div>
        <div className="enhancer-section">
          <div className="enhancer-header">Prompt Enhancer</div>
          <div className="field">
            <label>LLM model</label>
            <select
              value={llmModel}
              onChange={(event) => setLlmModel(event.target.value)}
            >
              <option value="">None — send prompt directly</option>
              {["ollama", "lmstudio", "azure", "bedrock"].map((provider) => {
                const entries =
                  llmModels?.filter(
                    (m) => m.provider === provider && m.enabled,
                  ) ?? [];
                if (entries.length === 0) return null;
                return (
                  <optgroup key={provider} label={provider}>
                    {entries.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.model}
                      </option>
                    ))}
                  </optgroup>
                );
              })}
            </select>
            <div className="hint">
              {llmModel
                ? "The LLM rewrites your prompt before image generation."
                : "Prompt is sent to the image model as-is."}
            </div>
          </div>
          {llmModel && (
            <>
              <div className="field">
                <label>System prompt</label>
                <textarea
                  value={systemPrompt}
                  onChange={(event) => setSystemPrompt(event.target.value)}
                  placeholder="You are an expert image prompt engineer. Rewrite the user's idea as a single vivid, detailed image generation prompt. Reply with the prompt only."
                />
              </div>
              <div className="field field-row">
                <div>
                  <label>Max tokens</label>
                  <input
                    type="number"
                    min={1}
                    max={8192}
                    value={llmMaxTokens}
                    onChange={(event) =>
                      setLlmMaxTokens(Number(event.target.value))
                    }
                  />
                </div>
                <div>
                  <label>Temperature</label>
                  <input
                    type="number"
                    min={0}
                    max={2}
                    step={0.1}
                    value={llmTemperature}
                    onChange={(event) =>
                      setLlmTemperature(Number(event.target.value))
                    }
                  />
                </div>
              </div>
            </>
          )}
        </div>
        <div className="field">
          <label>Prompt</label>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Walking cat with tall black hat."
            required
          />
        </div>
        {model?.capabilities.supports_negative_prompt && (
          <div className="field">
            <label>Negative prompt</label>
            <input
              value={negPrompt}
              onChange={(event) => setNegPrompt(event.target.value)}
              placeholder="(optional)"
            />
          </div>
        )}
        {model?.capabilities.supports_image_input && (
          <div className="field">
            <label>
              Input images{" "}
              {model.capabilities.requires_image_input ? "(required)" : ""}
            </label>
            <input
              value={images}
              onChange={(event) => setImages(event.target.value)}
              placeholder="/path/to/image1.png, /path/to/image2.png"
              required={model.capabilities.requires_image_input}
            />
            <div className="hint">
              Comma-separated local paths on the server
            </div>
          </div>
        )}
        <div className="field field-row">
          <div>
            <label>Width</label>
            <input
              type="number"
              min={64}
              max={2048}
              step={64}
              value={width}
              onChange={(event) => setWidth(Number(event.target.value))}
            />
          </div>
          <div>
            <label>Height</label>
            <input
              type="number"
              min={64}
              max={2048}
              step={64}
              value={height}
              onChange={(event) => setHeight(Number(event.target.value))}
            />
          </div>
        </div>
        <div className="field field-row">
          <div>
            <label>Steps</label>
            <input
              type="number"
              min={1}
              max={100}
              value={steps}
              onChange={(event) => setSteps(Number(event.target.value))}
            />
          </div>
          <div>
            <label>Guidance</label>
            <input
              type="number"
              min={0}
              max={20}
              step={0.1}
              value={guidance}
              onChange={(event) => setGuidance(Number(event.target.value))}
            />
          </div>
        </div>
        <div className="field">
          <label>Seed</label>
          <div className="checkbox-row" style={{ marginBottom: 8 }}>
            <input
              id="random-seed"
              type="checkbox"
              checked={randomSeedEnabled}
              onChange={(event) => setRandomSeedEnabled(event.target.checked)}
            />
            <label htmlFor="random-seed">Random (picked by the server)</label>
          </div>
          {!randomSeedEnabled && (
            <div className="seed-row">
              <input
                type="number"
                value={seed}
                onChange={(event) => setSeed(Number(event.target.value))}
              />
              <button
                type="button"
                className="secondary"
                onClick={() => setSeed(randomSeed())}
              >
                🎲
              </button>
            </div>
          )}
        </div>
        {model?.capabilities.supports_multi_image && !sweepEnabled && (
          <div className="field">
            <label>Images per prompt</label>
            <input
              type="number"
              min={1}
              max={model.capabilities.max_images}
              value={numImages}
              onChange={(event) => setNumImages(Number(event.target.value))}
            />
          </div>
        )}
        <div className="checkbox-row">
          <input
            id="sweep"
            type="checkbox"
            checked={sweepEnabled}
            onChange={(event) => setSweepEnabled(event.target.checked)}
          />
          <label htmlFor="sweep">Seed sweep (test_gen)</label>
        </div>
        {sweepEnabled && (
          <div className="field field-row">
            <div>
              <label>Count</label>
              <input
                type="number"
                min={1}
                value={sweepCount}
                onChange={(event) => setSweepCount(Number(event.target.value))}
              />
            </div>
            <div>
              <label>Seed increment</label>
              <input
                type="number"
                value={sweepInc}
                onChange={(event) => setSweepInc(Number(event.target.value))}
              />
            </div>
          </div>
        )}
        <button type="submit" disabled={submit.isPending || !model}>
          {submit.isPending ? "Submitting…" : "Generate"}
        </button>
      </form>
      <div>
        {jobIds.length === 0 && (
          <div className="panel">
            <span className="hint">
              Submitted jobs will appear here with live status and results.
            </span>
          </div>
        )}
        {jobIds.map((jobId) => (
          <JobCard key={jobId} jobId={jobId} />
        ))}
      </div>
    </div>
  );
}
