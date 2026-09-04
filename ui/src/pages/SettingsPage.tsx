import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ModelDefaultOverride, type ServiceConfig } from "../api";

type OverrideField = keyof ModelDefaultOverride;

const OVERRIDE_FIELDS: { key: OverrideField; label: string }[] = [
  { key: "guidance_scale", label: "Guidance" },
  { key: "inf_steps", label: "Steps" },
  { key: "width", label: "Width" },
  { key: "height", label: "Height" },
  { key: "num_images_per_prompt", label: "Images" },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
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

  const [draft, setDraft] = useState<ServiceConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config && !draft) {
      setDraft(structuredClone(config));
    }
  }, [config, draft]);

  const save = useMutation({
    mutationFn: (next: ServiceConfig) => api.putConfig(next),
    onSuccess: (next) => {
      queryClient.setQueryData(["config"], next);
      queryClient.invalidateQueries({ queryKey: ["llm-models"] });
      setDraft(structuredClone(next));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  if (!draft || !models) return <div className="hint">Loading…</div>;

  const setOverride = (
    modelName: string,
    field: OverrideField,
    raw: string,
  ) => {
    setDraft((previous) => {
      if (!previous) return previous;
      const next = structuredClone(previous);
      const overrides = { ...(next.model_defaults[modelName] ?? {}) };
      if (raw === "") {
        overrides[field] = null;
      } else {
        overrides[field] = Number(raw);
      }
      const hasValues = Object.values(overrides).some(
        (value) => value !== null && value !== undefined,
      );
      if (hasValues) {
        next.model_defaults[modelName] = overrides;
      } else {
        delete next.model_defaults[modelName];
      }
      return next;
    });
  };

  const isLlmModelEnabled = (id: string) =>
    draft.llm.enabled_models === null || draft.llm.enabled_models.includes(id);

  const toggleLlmModel = (id: string, checked: boolean) => {
    setDraft((previous) => {
      if (!previous) return previous;
      const allIds = llmModels?.map((m) => m.id) ?? [];
      const current = previous.llm.enabled_models ?? allIds;
      const next = checked
        ? [...new Set([...current, id])]
        : current.filter((entry) => entry !== id);
      return {
        ...previous,
        llm: { ...previous.llm, enabled_models: next },
      };
    });
  };

  const setAllLlmModels = (enabled: boolean) => {
    setDraft((previous) =>
      previous
        ? {
            ...previous,
            llm: {
              ...previous.llm,
              enabled_models: enabled ? null : [],
            },
          }
        : previous,
    );
  };

  const handleSave = (event: React.FormEvent) => {
    event.preventDefault();
    save.mutate(draft);
  };

  return (
    <form onSubmit={handleSave}>
      <h1>Settings</h1>
      {save.isError && (
        <div className="error-box">{(save.error as Error).message}</div>
      )}
      {saved && <div className="success-box">Configuration saved.</div>}

      <div className="panel">
        <h2>Service</h2>
        <div className="field field-row-3">
          <div>
            <label>Output root</label>
            <input
              value={draft.output_root}
              onChange={(event) =>
                setDraft({ ...draft, output_root: event.target.value })
              }
            />
            <div className="hint">Requires restart</div>
          </div>
          <div>
            <label>Max workers</label>
            <input
              type="number"
              min={1}
              max={8}
              value={draft.max_workers}
              onChange={(event) =>
                setDraft({ ...draft, max_workers: Number(event.target.value) })
              }
            />
            <div className="hint">Requires restart</div>
          </div>
          <div>
            <label>Default model</label>
            <select
              value={draft.default_model ?? ""}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  default_model: event.target.value || null,
                })
              }
            >
              <option value="">(none)</option>
              {models.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name}
                </option>
              ))}
            </select>
            <div className="hint">Preselected in the Generate form</div>
          </div>
        </div>
      </div>

      <div className="panel">
        <h2>BFS LoRA (flux2-klein-9b-bfs)</h2>
        <div className="field field-row-3">
          <div>
            <label>Source</label>
            <input
              value={draft.bfs_lora.source ?? ""}
              placeholder="/path/to/lora or HF repo id"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  bfs_lora: {
                    ...draft.bfs_lora,
                    source: event.target.value || null,
                  },
                })
              }
            />
          </div>
          <div>
            <label>Weight name</label>
            <input
              value={draft.bfs_lora.weight_name ?? ""}
              placeholder="checkpoint.safetensors"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  bfs_lora: {
                    ...draft.bfs_lora,
                    weight_name: event.target.value || null,
                  },
                })
              }
            />
          </div>
          <div>
            <label>Scale</label>
            <input
              type="number"
              step={0.05}
              value={draft.bfs_lora.scale}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  bfs_lora: {
                    ...draft.bfs_lora,
                    scale: Number(event.target.value),
                  },
                })
              }
            />
          </div>
        </div>
      </div>

      <div className="panel">
        <h2>Prompt Enhancer — LLM providers</h2>
        <div className="hint" style={{ marginBottom: 12 }}>
          Local providers (Ollama, LM Studio) are discovered live from their
          base URLs. Azure and Bedrock credentials come from environment
          variables (AZURE_OPENAI_API_KEY, AWS credentials/profile) — only
          endpoints and model names are stored here.
        </div>
        <div className="field field-row">
          <div>
            <label>Ollama base URL</label>
            <input
              value={draft.llm.ollama.base_url}
              placeholder="http://localhost:11434"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    ollama: { base_url: event.target.value },
                  },
                })
              }
            />
          </div>
          <div>
            <label>LM Studio base URL</label>
            <input
              value={draft.llm.lmstudio.base_url}
              placeholder="http://localhost:1234/v1"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    lmstudio: { base_url: event.target.value },
                  },
                })
              }
            />
          </div>
        </div>
        <div className="field field-row-3">
          <div>
            <label>Azure OpenAI endpoint</label>
            <input
              value={draft.llm.azure.endpoint ?? ""}
              placeholder="https://myresource.openai.azure.com"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    azure: {
                      ...draft.llm.azure,
                      endpoint: event.target.value || null,
                    },
                  },
                })
              }
            />
          </div>
          <div>
            <label>Azure API version</label>
            <input
              value={draft.llm.azure.api_version}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    azure: {
                      ...draft.llm.azure,
                      api_version: event.target.value,
                    },
                  },
                })
              }
            />
          </div>
          <div>
            <label>Azure deployments</label>
            <input
              value={draft.llm.azure.deployments.join(", ")}
              placeholder="gpt-4o, gpt-4o-mini"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    azure: {
                      ...draft.llm.azure,
                      deployments: event.target.value
                        .split(",")
                        .map((entry) => entry.trim())
                        .filter(Boolean),
                    },
                  },
                })
              }
            />
            <div className="hint">Comma-separated deployment names</div>
          </div>
        </div>
        <div className="field field-row">
          <div>
            <label>Bedrock region</label>
            <input
              value={draft.llm.bedrock.region ?? ""}
              placeholder="us-east-1"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    bedrock: {
                      ...draft.llm.bedrock,
                      region: event.target.value || null,
                    },
                  },
                })
              }
            />
          </div>
          <div>
            <label>Bedrock model IDs</label>
            <input
              value={draft.llm.bedrock.model_ids.join(", ")}
              placeholder="anthropic.claude-3-5-sonnet-20240620-v1:0"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    bedrock: {
                      ...draft.llm.bedrock,
                      model_ids: event.target.value
                        .split(",")
                        .map((entry) => entry.trim())
                        .filter(Boolean),
                    },
                  },
                })
              }
            />
            <div className="hint">Comma-separated model IDs</div>
          </div>
        </div>
        <div className="field field-row">
          <div>
            <label>Default max tokens</label>
            <input
              type="number"
              min={1}
              max={8192}
              value={draft.llm.default_max_tokens}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    default_max_tokens: Number(event.target.value),
                  },
                })
              }
            />
          </div>
          <div>
            <label>Default temperature</label>
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={draft.llm.default_temperature}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  llm: {
                    ...draft.llm,
                    default_temperature: Number(event.target.value),
                  },
                })
              }
            />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="llm-models-header">
          <h2>Prompt Enhancer — available models</h2>
          <div className="llm-models-actions">
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setAllLlmModels(true)}
            >
              Enable all
            </button>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setAllLlmModels(false)}
            >
              Disable all
            </button>
          </div>
        </div>
        <div className="hint" style={{ marginBottom: 12 }}>
          Only checked models appear in the Prompt Enhancer dropdown on the
          Generate page. Local models are discovered live; the list refreshes
          automatically.
        </div>
        {!llmModels || llmModels.length === 0 ? (
          <div className="hint">
            No LLM models discovered. Check provider settings above and make
            sure Ollama / LM Studio are running.
          </div>
        ) : (
          ["ollama", "lmstudio", "azure", "bedrock"].map((provider) => {
            const entries = llmModels.filter((m) => m.provider === provider);
            if (entries.length === 0) return null;
            return (
              <div key={provider} className="llm-provider-group">
                <div className="llm-provider-label">{provider}</div>
                <div className="llm-model-list">
                  {entries.map((m) => (
                    <label key={m.id} className="llm-model-item">
                      <input
                        type="checkbox"
                        checked={isLlmModelEnabled(m.id)}
                        onChange={(event) =>
                          toggleLlmModel(m.id, event.target.checked)
                        }
                      />
                      <span title={m.id}>{m.model}</span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="panel">
        <h2>Per-model defaults</h2>
        <div className="hint" style={{ marginBottom: 12 }}>
          Blank fields inherit the model&apos;s built-in defaults (shown as
          placeholders). Overrides apply to requests that omit the parameter.
        </div>
        <table className="overrides-table">
          <thead>
            <tr>
              <th>Model</th>
              {OVERRIDE_FIELDS.map((field) => (
                <th key={field.key}>{field.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map((model) => {
              const overrides = draft.model_defaults[model.name] ?? {};
              return (
                <tr key={model.name}>
                  <td className="model-name">{model.name}</td>
                  {OVERRIDE_FIELDS.map((field) => (
                    <td key={field.key}>
                      <input
                        type="number"
                        step={field.key === "guidance_scale" ? 0.1 : 1}
                        placeholder={String(model.defaults[field.key])}
                        value={overrides[field.key] ?? ""}
                        onChange={(event) =>
                          setOverride(model.name, field.key, event.target.value)
                        }
                      />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <button type="submit" disabled={save.isPending}>
        {save.isPending ? "Saving…" : "Save configuration"}
      </button>
    </form>
  );
}
