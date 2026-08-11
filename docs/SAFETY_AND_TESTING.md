# Jeen Lab Safety and Testing Notes

Jeen Lab is a computational research prototype for open-data protein exploration, ligand preparation, docking, 3D visualization, simple inheritance education, and report drafting.

It is not a medical device, diagnostic tool, treatment planner, autonomous genome-editing system, or cure-generation platform.

## Safety Position

- The application may generate research hypotheses, not medical conclusions.
- Docking scores are virtual-screening signals only. They do not prove binding in cells, biological efficacy, safety, dosage, delivery, or disease prevention.
- AlphaFold structures are predicted protein models. Confidence, missing regions, cofactors, metals, membrane context, protonation, and biological assembly must be reviewed before serious docking use.
- Inheritance diagrams show simplified probability models. They are not a replacement for clinical genetics, genetic testing, or genetic counseling.
- Any genome editing, germline intervention, embryo editing, clinical use, or claim to prevent inherited disease requires qualified clinical, ethical, legal, and laboratory oversight.

## Data Sources

- RCSB Protein Data Bank for experimentally resolved protein structures.
- AlphaFold Protein Structure Database for predicted protein models by UniProt accession.
- PubChem PUG-REST for public compound structures and SMILES-backed ligand preparation.
- AutoDock Vina for local molecular docking.
- 3Dmol.js for local 3D molecular rendering.

## Security Controls Added

- The server binds to `127.0.0.1` instead of all network interfaces.
- CORS is restricted to local app origins.
- Static file and log access use containment checks instead of unsafe string-prefix checks.
- Protein IDs, UniProt accessions, ligand names, manuscript names, docking grid sizes, and exhaustiveness values are validated.
- Request bodies are capped at 1 MB.
- Delete endpoints only remove expected file types for exact target names.
- Stale `running` jobs are marked failed after restart/timeout so old jobs do not appear live.
- Manuscript generation no longer inserts fake example binding scores.

## Automated E2E Test

The automated browser test is stored at:

```text
tests/e2e-jeen-lab.js
```

It drives a real Chrome or Edge browser and validates:

- Dashboard loads and reports Vina/Python readiness.
- Disease Atlas renders open-data disease, gene, and protein targets.
- Inheritance visualization renders and responds to mode changes.
- Protein preparation works with real RCSB PDB ID `1CRN`.
- Custom ligand preparation works with caffeine SMILES through PubChem-backed preparation.
- Docking grid controls accept and display values.
- AutoDock Vina completes a real `2B8L + aspirin` docking run.
- Analysis table and 3Dmol.js viewer load a docked complex.
- Manuscript generation uses completed local runs and does not fabricate example data.
- `/api/log` blocks path traversal attempts.

## Latest Verified Run

- Date: 2026-08-11
- Base URL: `http://127.0.0.1:8000`
- Docking validation: `2B8L + aspirin`
- Binding affinity: `-3.382 kcal/mol`
- Screenshots and machine-readable report:

```text
test-artifacts/
```

## How To Run The Test

Start Jeen Lab first:

```powershell
python server.py
```

Then run:

```powershell
$env:NODE_PATH='C:\Users\alwin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\alwin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests\e2e-jeen-lab.js
```

The test opens a visible browser window, performs the workflow, and saves screenshots plus `e2e-report.json` under `test-artifacts/`.

## Remaining Research Gaps Before Serious Scientific Use

- Add RDKit/Meeko-first preparation validation for charges, torsions, stereochemistry, protonation, and tautomers.
- Add active-site metadata provenance for each preset, with citations.
- Add confidence display for AlphaFold models, especially pLDDT/PAE review.
- Add reproducible random seeds and multi-run docking statistics.
- Add explicit compound provenance and PubChem CID capture.
- Add unit tests around pipeline parsers and result-state handling.
- Add a reviewed ethics page for genetics/genome-editing boundaries.
