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
