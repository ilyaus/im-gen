# im-gen

FastAPI-based image generation service with deferred job execution.

## Run the API

```bash
uv run uvicorn src.main:app --reload
```

## Endpoints

- `GET /health` - service health check
- `GET /models` - list supported model names
- `POST /jobs` - submit a generation request
- `GET /jobs/{job_id}` - get job status
- `GET /jobs/{job_id}/result` - fetch completed job metadata
- `GET /jobs/{job_id}/artifacts/{filename}` - download a generated image

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

`num_images_per_prompt` defaults to `1`. Multi-image generation is supported only by the FLUX models; `tongyi-mai` requires `num_images_per_prompt=1`.

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

- `tongyi-mai`
- `flux2-klein-4b-small-decoder`
- `flux2-klein-9b`
- `flux2-klein-9b-bfs`
- `flux2-klein-9b-small-decoder`

## BFS LoRA

`flux2-klein-9b-bfs` loads the base `black-forest-labs/FLUX.2-klein-9B`
pipeline and applies a configured LoRA adapter. Set `IM_GEN_BFS_LORA` to the
LoRA file, directory, or Hugging Face repository ID before submitting jobs for
this model. If the repository or directory contains multiple weight files, set
`IM_GEN_BFS_LORA_WEIGHT_NAME` to the specific checkpoint filename. Optionally
set `IM_GEN_BFS_LORA_SCALE` to control adapter strength; it defaults to `1.0`.

```sh
export IM_GEN_BFS_LORA="/home/ushomi/lora/bsf"
export IM_GEN_BFS_LORA_WEIGHT_NAME="bfs_head_v1_flux-klein_4b.safetensors"
export IM_GEN_BFS_LORA_WEIGHT_NAME="bfs_head_v1_flux-klein_9b_step3750_rank64.safetensors"
export IM_GEN_BFS_LORA_WEIGHT_NAME="bfs_head_v1_flux-klein_9b_step3500_rank128.safetensors"
```