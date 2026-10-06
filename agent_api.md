# Genome Sentinel Agent Interface

Genome Sentinel exposes a local, machine-readable interface so an agentic AI can inspect and operate the workspace without relying on visual clicking.

## Discovery

When Genome Sentinel is running locally:

- `GET /api/info` — application/version metadata
- `GET /api/capabilities` — supported agent actions
- `GET /api/status` — current environment and prepared resources
- `GET /api/results` — current docking result summary

## Controlled actions

Use:

`POST /api/agent/execute`

with a JSON body containing an `action` field.

Supported actions:

- `get_status`
- `get_results`
- `download_protein` with `pdb_id`
- `prepare_presets`
- `prepare_custom_ligand` with `name` and `smiles`
- `run_docking` with protein, ligand and grid parameters
- `clear_results`

The endpoint is intentionally explicit: an agent must name the action rather than submitting arbitrary Python or shell commands.

## Agent design principles

1. JSON in / JSON out.
2. Explicit capability discovery.
3. Versioned API metadata.
4. No arbitrary command execution endpoint.
5. Local-first operation.
6. Human UI remains the primary visual interface.
7. Destructive actions should be clearly identified as non-read-only.

For remote or multi-user deployments, authentication and authorization must be added before exposing the API beyond localhost.
