# im-gen

FastAPI-based image generation service with deferred job execution, persisted job history, a YAML configuration system, and a React web UI.

## Run the API

```bash
uv run uvicorn src.main:app --reload
```

If `ui/dist` exists (see below), the web UI is served at `http://127.0.0.1:8000/`.

## Web UI

The UI lives in `ui/` (Vite + React + TypeScript).

```bash
cd ui
npm install
npm run build     # outputs ui/dist, served by FastAPI at /
```

For UI development with hot reload (proxies API calls to `127.0.0.1:8000`):

```bash
cd ui
npm run dev       # http://localhost:5173
```

Pages:

- **Generate** - model picker with per-model defaults and capability-aware form, live job status, inline results
- **Gallery** - persisted job history with thumbnails, model/status filters, pagination, job detail and delete
- **Settings** - service configuration, BFS LoRA settings, and per-model default overrides

## Endpoints

- `GET /health` - service health check
- `GET /models` - list models with defaults and capabilities
- `GET /config` - current service configuration
- `PUT /config` - update and persist service configuration
- `POST /jobs` - submit a generation request
- `GET /jobs` - list jobs (`limit`, `offset`, `model`, `status` query params)
- `GET /jobs/{job_id}` - get job status
- `DELETE /jobs/{job_id}` - delete a finished job and its artifacts
- `GET /jobs/{job_id}/result` - fetch completed job metadata
- `GET /jobs/{job_id}/artifacts/{filename}` - download a generated image

## Configuration

Configuration is stored in `config.yaml` (path overridable via the `IM_GEN_CONFIG` environment variable) and editable via the Settings page or `PUT /config`:

```yaml
output_root: generated       # where job outputs are stored (restart required)
max_workers: 1               # generation worker threads (restart required)
default_model: flux2-klein-9b
bfs_lora:
  source: /home/ushomi/lora/bsf
  weight_name: bfs_head_v1_flux-klein_9b_step3750_rank64.safetensors
  scale: 1.0
model_defaults:              # per-model overrides for omitted request params
  flux2-klein-9b:
    inf_steps: 4
    width: 512
```

Environment variables (`OUTPUT_ROOT`, `IM_GEN_BFS_LORA`, `IM_GEN_BFS_LORA_WEIGHT_NAME`, `IM_GEN_BFS_LORA_SCALE`) are still honored as fallbacks when the corresponding value is not set in `config.yaml`.

Request parameters that are omitted resolve in this order: request value → `model_defaults` override from config → the model's built-in defaults (visible via `GET /models`).

## Job persistence

Each job writes a `job.json` record into its output directory. On startup the service rescans `output_root` and rehydrates job history, so the gallery survives restarts. Jobs that were queued or running during a restart are marked as failed.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "flux2-klein-9b",
    "prompt": "Walking cat with tall black hat.",
    "height": 1024,
    "width": 512,
    "num_images_per_prompt": 2,
    "inf_steps": 4,
    "seed": 42
  }'
```

The API responds immediately with a job ID. Poll `GET /jobs/{job_id}` until the status becomes `succeeded`, then call `GET /jobs/{job_id}/result` to retrieve artifact metadata and download URLs.

`num_images_per_prompt` defaults to the model's configured default. Multi-image generation is not supported by `tongyi-mai`, which requires `num_images_per_prompt=1`.

When `test_gen` is provided, the service runs a seed sweep: it generates `count` images with the same request parameters, increments the seed by `seed_inc` after each image, and stores the seed on each returned artifact. In this mode, `num_images_per_prompt` must stay `1`, and output filenames include the seed so the sweep is easy to inspect.

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "flux2-klein-9b",
    "prompt": "Walking cat with tall black hat.",
    "height": 1024,
    "width": 512,
    "inf_steps": 4,
    "seed": 42,
    "test_gen": {
      "count": 4,
      "seed_inc": 1
    }
  }'
```

## Supported models

| Name | Model | Notes |
|---|---|---|
| `tongyi-mai` | Tongyi-MAI/Z-Image-Turbo | 6B distilled, fast |
| `baidu-ernie-image` | Baidu/ERNIE-Image | |
| `flux2-klein-4b-small-decoder` | FLUX.2 Klein 4B + small decoder | fast |
| `flux2-klein-9b` | FLUX.2 Klein 9B | |
| `flux2-klein-9b-bfs` | FLUX.2 Klein 9B + BFS LoRA | see BFS LoRA below |
| `flux2-klein-9b-small-decoder` | FLUX.2 Klein 9B + small decoder | |
| `qwen-image` | Qwen/Qwen-Image-2512 | 20B, best text rendering, CPU offload (slow first token) |
| `qwen-image-edit` | Qwen/Qwen-Image-Edit-2511 | image editing, requires input images |
| `sd35-medium` | stabilityai/stable-diffusion-3.5-medium | gated repo * |
| `sd35-large` | stabilityai/stable-diffusion-3.5-large | gated repo *, CPU offload |
| `sana-sprint` | NVIDIA Sana Sprint 1.6B | 1-4 steps, very fast |
| `hunyuan-image` | HunyuanImage 2.1 | 17B, CPU offload |
| `lumina-2` | Alpha-VLLM/Lumina-Image-2.0 | 2.6B |
| `krea2-turbo` | krea/Krea-2-Turbo | 12B, 8-step distilled, gated repo * |

\* Gated Hugging Face repos require accepting the model license on huggingface.co and authenticating with `huggingface-cli login` or the `HF_TOKEN` environment variable.

Per-model defaults (steps, guidance, size) are defined in `src/models/registry.py` and can be overridden per model in `config.yaml` without code changes.

## BFS LoRA

`flux2-klein-9b-bfs` loads the base `black-forest-labs/FLUX.2-klein-9B` pipeline and applies a configured LoRA adapter. Configure it in `config.yaml` (or the Settings page):

```yaml
bfs_lora:
  source: /home/ushomi/lora/bsf                # file, directory, or HF repo id
  weight_name: bfs_head_v1_flux-klein_9b_step3750_rank64.safetensors
  scale: 1.0
```

A request-level `lora_weight_name` takes precedence over the configured `weight_name`.

## Development

```bash
uv run pytest              # API tests (fast, no GPU needed)
uvx ruff check src tests   # lint
```

Adding a new model: create a module in `src/models/` with a `generate(request, output_dir, job_id)` function (use `src.models.base.run_generation` to avoid boilerplate) and register it in `src/models/registry.py` with its defaults and capabilities.
