<div align="center">
  <h1>🛡️ Security Policy — Genome Sentinel</h1>
  <p><strong>Molecular Docking Suite v1.0.0</strong></p>
</div>

---

## Supported Versions

| Version | Status | Security Updates |
| ------- | ------ | ---------------- |
| 1.0.x   | ✅ Active | Receiving patches |
| < 1.0   | ❌ Unsupported | No longer maintained |

---

## Architecture Security Overview

Genome Sentinel runs as a **local-only** application with the following trust boundaries:

```
┌──────────────────────────────────────────────────────────┐
│  USER'S MACHINE (localhost:8000)                         │
│                                                          │
│  ┌──────────┐    HTTP     ┌──────────────┐               │
│  │ Browser  │◄──────────►│  server.py   │               │
│  │ Frontend │  (local)   │  (Python)    │               │
│  └──────────┘            └──────┬───────┘               │
│                                 │                        │
│                    subprocess   │   file I/O             │
│                    ┌────────────┼────────────┐           │
│                    ▼            ▼            ▼           │
│              ┌──────────┐ ┌─────────┐ ┌──────────┐      │
│              │ AutoDock │ │  data/  │ │ pipeline/│      │
│              │  Vina    │ │ (PDB,   │ │ (Python  │      │
│              │ (bin/)   │ │  PDBQT) │ │  scripts)│      │
│              └──────────┘ └─────────┘ └──────────┘      │
│                                                          │
│  Outbound HTTPS only:                                    │
│    → RCSB PDB (files.rcsb.org)                           │
│    → PubChem (pubchem.ncbi.nlm.nih.gov)                  │
│    → AlphaFold DB (alphafold.ebi.ac.uk)                  │
│    → Vina binary (github.com/ccsb-scripps)               │
└──────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### 1. Local HTTP Server (`server.py`)

| Risk | Severity | Current Mitigation |
| ---- | -------- | ------------------ |
| **Server binds to all interfaces** | Medium | The server uses `http.server` on `0.0.0.0:8000`. On shared/public networks, other machines could reach the API. |
| **No authentication** | Low (local tool) | There is no login or API key mechanism. Acceptable for single-user local use; not safe for deployment on a shared network. |
| **CORS set to `*`** | Low (local tool) | `Access-Control-Allow-Origin: *` is configured for development convenience. Any browser tab could make requests to the API. |
| **Subprocess execution** | Medium | Pipeline scripts invoke `subprocess.run()` / `subprocess.Popen()` to execute AutoDock Vina and Python helpers. Inputs (PDB IDs, SMILES strings) should be validated before passing to shell commands. |

**Recommendations for hardening:**
- Bind the server to `127.0.0.1` only (not `0.0.0.0`) to prevent network exposure.
- Validate and sanitize all user-supplied inputs (PDB IDs, SMILES strings, file names) before passing them to `subprocess` or file system operations.
- Restrict CORS to `http://localhost:8000` in production.
- Consider adding a simple API token for non-localhost deployments.

### 2. External API Calls

Genome Sentinel makes outbound HTTPS requests to the following trusted scientific databases:

| Service | Domain | Purpose | Data Sent |
| ------- | ------ | ------- | --------- |
| RCSB Protein Data Bank | `files.rcsb.org` | Download PDB structures | PDB ID (4 chars) |
| PubChem | `pubchem.ncbi.nlm.nih.gov` | Fetch 3D ligand structures | Compound name or SMILES |
| AlphaFold DB | `alphafold.ebi.ac.uk` | AI-predicted protein structures | UniProt ID or gene name |
| GitHub (Scripps) | `github.com` | Download Vina binary | None (static asset) |

**No user credentials, personal data, or research results are ever transmitted externally.**

### 3. File System & Data Integrity

| Concern | Details |
| ------- | ------- |
| **Data storage** | All protein (`.pdb`, `.pdbqt`), ligand, and docking result files are stored locally under `data/`. No cloud sync. |
| **File path traversal** | API endpoints that accept file names (e.g., delete protein/ligand) should validate that paths stay within `data/` and never escape to parent directories. |
| **Binary execution** | The `setup_env.py` script downloads `vina_1.2.5_win.exe` from the official Scripps GitHub release. Verify the binary hash after download if possible. |
| **Temporary files** | Pipeline scripts may create intermediate files in `data/`. These are not automatically cleaned and may accumulate over time. |

### 4. Subprocess & Command Injection

The docking pipeline constructs command-line invocations dynamically. Key safeguards:

- **PDB IDs** are validated to be exactly 4 alphanumeric characters before use.
- **SMILES strings** should be sanitized to reject shell metacharacters (`;`, `|`, `&`, `` ` ``, `$`, etc.) before being passed to any subprocess.
- **File names** derived from user input should be stripped of path separators and special characters.
- Always prefer `subprocess.run([...], shell=False)` (list form) over string-based `shell=True` invocation.

### 5. Client-Side Security (Web Dashboard)

| Concern | Details |
| ------- | ------- |
| **XSS prevention** | User-supplied text (compound names, annotations) inserted into the DOM should use `textContent` / `innerText` rather than `innerHTML` to prevent script injection. |
| **localStorage** | Theme preference and onboarding state are stored in `localStorage`. No sensitive data is persisted client-side. |
| **3Dmol.js** | The 3D viewer library is loaded from a local bundled copy (`3Dmol-min.js`), not from a CDN, reducing supply-chain risk. |

---

## Data Privacy

Genome Sentinel is designed as an **offline-first, privacy-respecting** research tool:

- ✅ **No telemetry** — No usage analytics, crash reports, or tracking of any kind.
- ✅ **No cloud storage** — All data remains on the user's local machine.
- ✅ **No accounts** — No registration, login, or personal information collection.
- ✅ **No external dependencies at runtime** — Once proteins and ligands are downloaded, the tool operates fully offline.
- ✅ **Open source** — All code is inspectable. No obfuscated or minified application logic (except the vendored `3Dmol-min.js` library).

---

## Dependency Inventory

| Dependency | Type | Source | Notes |
| ---------- | ---- | ------ | ----- |
| Python 3.x | Runtime | System install | Core runtime |
| AutoDock Vina 1.2.5 | Binary | [Scripps GitHub](https://github.com/ccsb-scripps/AutoDock-Vina) | Downloaded by `setup_env.py` |
| 3Dmol.js | JS Library | Bundled locally | `app/3Dmol-min.js` |
| Font Awesome 6.4 | CSS/Fonts | CDN (`cdnjs.cloudflare.com`) | Icon library |
| Plus Jakarta Sans | Font | CDN (`fonts.googleapis.com`) | Typography |
| JetBrains Mono | Font | CDN (`fonts.googleapis.com`) | Monospace font |
| RDKit (optional) | Python package | PyPI | For advanced ligand prep |
| Meeko (optional) | Python package | PyPI | PDBQT conversion |
| Requests (optional) | Python package | PyPI | HTTP downloads |

**CDN dependencies** (Font Awesome, Google Fonts) are loaded over HTTPS. For fully air-gapped environments, these can be self-hosted by downloading the assets into the `app/` directory.

---

## Reporting a Vulnerability

If you discover a security vulnerability in Genome Sentinel, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. **Email**: Send a detailed report to the project maintainer via the contact information in the repository.
3. **Include**:
   - A clear description of the vulnerability
   - Steps to reproduce the issue
   - The potential impact
   - Suggested fix (if you have one)
4. **Response timeline**:
   - **Acknowledgment**: Within 48 hours of report
   - **Assessment**: Within 7 days
   - **Fix & disclosure**: Within 30 days for confirmed vulnerabilities

We follow **coordinated disclosure** — we will credit reporters (unless anonymity is requested) and publish a security advisory once the fix is released.

---

## Security Best Practices for Users

When running Genome Sentinel on your machine:

1. **Run on localhost only** — Do not expose port 8000 to the internet or untrusted networks.
2. **Keep Python updated** — Use Python 3.10+ with the latest security patches.
3. **Verify downloads** — When `setup_env.py` downloads the Vina binary, verify it matches the expected file size and hash from the official Scripps release page.
4. **Review SMILES inputs** — If accepting SMILES strings from external sources (papers, databases), visually verify them before processing.
5. **Firewall rules** — Consider adding a firewall rule to block inbound connections on port 8000 from non-localhost addresses.
6. **Backup your data** — The `data/` directory contains your research results. Back it up regularly.

---

## License

This security policy is part of the Genome Sentinel project, licensed under the [MIT License](LICENSE).

---

<div align="center">
  <sub>Last updated: September 2026 · Genome Sentinel v1.0.0</sub>
</div>
