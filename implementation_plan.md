# Implementation Plan: Interactive Computational Drug Discovery Workspace

This plan outlines the design and implementation of a local, interactive computational drug discovery workspace in `d:\Drug Discovery Research`. The workspace will feature an automated Python pipeline for protein download, ligand preparation, and AutoDock Vina docking, alongside a beautiful web-based control center and 3D visualizer.

## User Review Required

> [!IMPORTANT]
> The workspace relies on Python and standard command-line tools to automate the drug discovery process. We will:
> 1. Write Python scripts to download proteins (RCSB PDB) and FDA-approved ligands (PubChem/ZINC).
> 2. Automatically download the official AutoDock Vina Windows executable (`vina_1.2.5_win.exe`) to a local directory so you don't have to install it manually.
> 3. Provide an interactive single-page web dashboard using `3Dmol.js` to visualize the protein, target binding site, and docked ligands directly on your laptop.

## Proposed Changes

We will create a structured project inside `d:\Drug Discovery Research`:

```
d:\Drug Discovery Research\
├── bin/                          # AutoDock Vina executables
├── data/                         # Protein, ligand, and docking result files
│   ├── proteins/
│   ├── ligands/
│   └── results/
├── pipeline/                     # Core computational drug discovery scripts
│   ├── setup_env.py              # Automated script to download Vina & install pip packages
│   ├── prep_protein.py           # Download and prepare target proteins (clean PDB, remove water)
│   ├── prep_ligands.py           # Fetch/prepare ligand library (SMILES/SDF to PDBQT via Meeko)
│   └── run_docking.py            # Automation script to screen ligands with AutoDock Vina
├── app/                          # Web Control Dashboard
│   ├── index.html                # Modern, dark-themed control center dashboard
│   ├── style.css                 # Beautiful glassmorphism, animations, and typography
│   └── app.js                    # SPA dashboard logic & 3Dmol.js integration
├── server.py                     # Zero-dependency local web server to serve the frontend & bridge Python scripts
└── run.bat                       # Double-clickable Windows batch script to launch the server and open browser
```

---

### Component 1: Python Pipeline (`pipeline/`)

These Python scripts automate the technical steps of fetching, cleaning, and preparing files, and running AutoDock Vina.

#### [NEW] [setup_env.py](file:///d:/Drug%20Discovery%20Research/pipeline/setup_env.py)
* Downloads the official pre-compiled Windows executable `vina_1.2.5_win.exe` from Scripps GitHub into `bin/`.
* Attempts to run `pip install rdkit meeko requests` to set up ligand prep tools.

#### [NEW] [prep_protein.py](file:///d:/Drug%20Discovery%20Research/pipeline/prep_protein.py)
* Downloads a PDB file from RCSB PDB using a given PDB ID.
* Strips water molecules and prepares the protein structure.

#### [NEW] [prep_ligands.py](file:///d:/Drug%20Discovery%20Research/pipeline/prep_ligands.py)
* Prepares ligand libraries (e.g. downloads list of FDA-approved drugs or processes a list of user-provided SMILES/SDFs).
* Uses `rdkit` to generate 3D coordinates and `meeko` to convert them to PDBQT.

#### [NEW] [run_docking.py](file:///d:/Drug%20Discovery%20Research/pipeline/run_docking.py)
* Automates running Vina for each prepared ligand.
* Takes grid coordinates (x, y, z) and box sizes, writes configuration files, and executes Vina in a background process.
* Parses the output log to extract binding affinity values (kcal/mol) and updates a local JSON results file.

---

### Component 2: Dashboard Frontend (`app/`)

A high-fidelity single-page application that serves as the controller and visualization tool.

#### [NEW] [index.html](file:///d:/Drug%20Discovery%20Research/app/index.html)
* Structured layout including a side navigation panel and main content area divided into steps.
* Features:
  - **Status panel** showing if Vina is ready and packages are installed.
  - **Step 1: Protein Selector**: Download targets (e.g. Alzheimer's BACE1, Malaria PfDHFR) or custom PDB IDs.
  - **Step 2: Ligand Library**: View/manage candidate drugs (e.g. Acetaminophen, Chloroquine, Metformin).
  - **Step 3: Grid Configuration**: Choose docking coordinates.
  - **Step 4: Screen execution**: Press button to launch Python runner, view live logs.
  - **Step 5: Visualizer**: Interactive table of binding scores + 3D canvas (3Dmol.js) showing binding pose and hydrogen bonds.
  - **Step 6: Paper Builder**: Write Abstract, Intro, Discussion, and export draft to Markdown.

#### [NEW] [style.css](file:///d:/Drug%20Discovery%20Research/app/style.css)
* Custom, responsive CSS following the "Rich Aesthetics" design framework.
* Dark slate-grey and midnight backgrounds with vibrant indigo, violet, and electric teal highlights.
* Glassmorphic cards, smooth transitions, elegant buttons, and glowing indicator states.

#### [NEW] [app.js](file:///d:/Drug%20Discovery%20Research/app/app.js)
* Handles state management and interacts with backend API endpoints.
* Embeds and controls the `3Dmol.js` viewer (e.g., loading the receptor as a gray cartoon and ligand as CPK sticks, highlighting binding pocket).

---

### Component 3: Local Server & Runner (`server.py`, `run.bat`)

#### [NEW] [server.py](file:///d:/Drug%20Discovery%20Research/server.py)
* Runs a local HTTP server that hosts the `app/` folder and exposes REST APIs:
  - `/api/status` (Check environment status)
  - `/api/setup` (Run environment setup)
  - `/api/download_protein` (Download & prepare target)
  - `/api/run_docking` (Launch screens)
  - `/api/results` (Fetch score tables)
  - `/api/files/` (Serve protein/ligand files for 3D visualizer)

#### [NEW] [run.bat](file:///d:/Drug%20Discovery%20Research/run.bat)
* Single-click batch file to execute Python server and open `http://localhost:8000` in the default web browser.

---

## Verification Plan

### Automated/Local Verification
- Verify that `setup_env.py` successfully downloads the Vina binary and checks python packages.
- Verify that `prep_protein.py` downloads a PDB structure successfully (e.g. PfDHFR PDB `1SGZ`).
- Verify that `prep_ligands.py` prepares standard ligands successfully.
- Verify that `run_docking.py` executes Vina commands properly.
- Verify that the web server successfully launches on port 8000 and the web UI renders all elements, visualizes 3D structures, and communicates with python APIs.
