# Jeen Lab

Computational genetics and molecular docking research workspace for Windows.

Jeen Lab combines open scientific data sources, local protein/ligand preparation, AutoDock Vina docking, 3Dmol.js molecular visualization, inheritance visualization, and research-report drafting. It is designed for education and early-stage computational hypothesis generation.

It is not a medical device, diagnostic system, treatment system, genome-editing protocol, or proof of cure.

## What Works

- Disease and gene target atlas for Parkinson's disease, Gilbert syndrome, and Alzheimer's research.
- RCSB PDB protein download and fallback PDBQT preparation.
- AlphaFold DB model download by UniProt accession.
- PubChem ligand preparation from SMILES or preset compounds.
- AutoDock Vina docking through the bundled `bin/vina.exe`.
- Binding-score table, Vina log viewer, and 3D protein plus docked ligand visualization.
- Inheritance probability visualization for simple autosomal recessive and dominant models.
- Manuscript draft generation using only completed local docking runs.

## Research Limits

- Docking scores are computational screening signals only.
- Predicted AlphaFold structures require confidence review and may be unsuitable for some docking workflows.
- The fallback PDBQT preparation is dependency-light and convenient, but serious research should validate protonation, charges, tautomers, cofactors, metals, binding-site selection, and receptor flexibility.
- Genetic inheritance diagrams show expected probability splits, not diagnosis or a personalized prediction.
- Any genome editing, germline work, clinical interpretation, prevention claim, or treatment decision requires qualified medical, ethical, regulatory, and laboratory review.

## Open Data Sources

- RCSB Protein Data Bank: https://www.rcsb.org/
- AlphaFold Protein Structure Database: https://alphafold.ebi.ac.uk/
- PubChem PUG-REST: https://pubchem.ncbi.nlm.nih.gov/
- AutoDock Vina: https://vina.scripps.edu/
- 3Dmol.js: https://3dmol.csb.pitt.edu/

## Run

```powershell
cd C:\Users\alwin\Downloads\Genome-Sentinel-main\Genome-Sentinel-main
python server.py
```

Open http://localhost:8000 in your browser.

The server binds to `127.0.0.1` for local research use.

## First Workflow

1. Open the dashboard and refresh environment status.
2. Use Disease Atlas to pick a target, or Step 1 to download a PDB ID.
3. Prepare ligand presets or add a ligand from a SMILES string.
4. Set a biologically justified docking grid.
5. Run Vina and inspect logs/results.
6. Open the 3D viewer and verify pose placement.
7. Generate a manuscript draft only after completed runs exist.

## Project Structure

```text
bin/             AutoDock Vina executable
data/            proteins, ligands, docking results, disease metadata
pipeline/        protein preparation, ligand preparation, docking scripts
app/             HTML/CSS/JS single-page interface and 3Dmol.js
server.py        local REST API and static file server
run.bat          Windows launcher
```
