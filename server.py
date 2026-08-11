import os
import sys
import json
import urllib.parse
import http.server
import socketserver
import subprocess
import threading
import mimetypes
import shutil
import importlib.util
import importlib
import re
import urllib.request
from datetime import datetime, timedelta

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")
DATA_DIR = os.path.join(BASE_DIR, "data")
BIN_DIR = os.path.join(BASE_DIR, "bin")

PORT = 8000
ALLOWED_ORIGINS = {f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"}
PDB_ID_RE = re.compile(r"^[A-Za-z0-9]{4}$")
UNIPROT_RE = re.compile(r"^[A-Za-z0-9]{5,12}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SUMMARY_LOCK = threading.Lock()

DISEASE_TARGETS = [
    {
        "disease": "Parkinson's disease",
        "inheritance": "Most cases are not inherited in a simple Mendelian pattern, but familial risk genes exist.",
        "genes": ["LRRK2", "SNCA", "GBA1", "PRKN", "PINK1"],
        "targets": [
            {"gene": "LRRK2", "protein": "Leucine-rich repeat kinase 2", "uniprot": "Q5S007", "structure_source": "AlphaFold DB"},
            {"gene": "SNCA", "protein": "Alpha-synuclein", "uniprot": "P37840", "structure_source": "AlphaFold DB"}
        ],
        "research_note": "Use as a target-discovery starting point. Parkinson's prevention or treatment decisions require clinical genetics and laboratory validation."
    },
    {
        "disease": "Gilbert syndrome",
        "inheritance": "Commonly autosomal recessive or reduced-function promoter variation affecting bilirubin glucuronidation.",
        "genes": ["UGT1A1"],
        "targets": [
            {"gene": "UGT1A1", "protein": "UDP-glucuronosyltransferase 1A1", "uniprot": "P22309", "structure_source": "AlphaFold DB"}
        ],
        "research_note": "UGT1A1 variants affect bilirubin metabolism. This app can visualize protein models, but it cannot diagnose or prescribe."
    },
    {
        "disease": "Alzheimer's disease research",
        "inheritance": "Usually complex; rare familial forms can involve APP, PSEN1, and PSEN2.",
        "genes": ["APP", "BACE1", "PSEN1", "PSEN2"],
        "targets": [
            {"gene": "BACE1", "protein": "Beta-secretase 1", "uniprot": "P56817", "pdb": "2B8L", "structure_source": "RCSB PDB"},
            {"gene": "APP", "protein": "Amyloid-beta precursor protein", "uniprot": "P05067", "structure_source": "AlphaFold DB"}
        ],
        "research_note": "Docking scores are screening signals only, not evidence of efficacy."
    }
]


def path_is_inside(path, root):
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
    except ValueError:
        return False


def clean_summary_state(summary):
    """Mark obviously stale jobs so the UI does not show old runs as live."""
    changed = False
    cutoff = datetime.now() - timedelta(hours=6)
    for job in summary.values():
        if job.get("status") != "running":
            continue
        try:
            started = datetime.fromisoformat(job.get("timestamp", ""))
        except ValueError:
            started = datetime.min
        if started < cutoff:
            job["status"] = "failed"
            job["error"] = "Marked failed: job was still running after server restart or timeout."
            changed = True
    return changed

class GenomeSentinelHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Suppress noise in stdout, log to screen cleanly
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format%args))
        
    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # 1. Serve API Endpoints
        if path == "/api/status":
            self.handle_api_status()
        elif path == "/api/results":
            self.handle_api_results()
        elif path == "/api/disease_targets":
            self.handle_api_disease_targets()
        elif path.startswith("/api/log"):
            self.handle_api_log(parsed_url.query)
        # 2. Serve Static files
        else:
            self.handle_static_files(path)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read content length and parse JSON body
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 1024 * 1024:
            self.send_error_response(413, "Request body too large")
            return
        post_data = self.rfile.read(content_length)
        
        data = {}
        if post_data:
            try:
                data = json.loads(post_data.decode('utf-8'))
            except Exception as e:
                print(f"Error parsing JSON post data: {e}")
                
        if path == "/api/setup":
            self.handle_api_setup()
        elif path == "/api/download_protein":
            self.handle_api_download_protein(data)
        elif path == "/api/download_alphafold":
            self.handle_api_download_alphafold(data)
        elif path == "/api/prep_presets":
            self.handle_api_prep_presets()
        elif path == "/api/prep_custom_ligand":
            self.handle_api_prep_custom_ligand(data)
        elif path == "/api/run_docking":
            self.handle_api_run_docking(data)
        elif path == "/api/delete_protein":
            self.handle_api_delete_protein(data)
        elif path == "/api/delete_ligand":
            self.handle_api_delete_ligand(data)
        elif path == "/api/clear_results":
            self.handle_api_clear_results()
        elif path == "/api/download_manuscript":
            self.handle_api_download_manuscript(data)
        else:
            self.send_error_response(404, "API endpoint not found")

    # API Handler: Status
    def handle_api_status(self):
        vina_path = os.path.join(BIN_DIR, "vina.exe")
        vina_installed = os.path.exists(vina_path)
        
        rdkit_installed = False
        meeko_installed = False
        requests_installed = False
        
        # Fast check using find_spec (avoids DLL load delays)
        rdkit_installed = importlib.util.find_spec("rdkit") is not None
        meeko_installed = importlib.util.find_spec("meeko") is not None
        requests_installed = importlib.util.find_spec("requests") is not None
        
        # Check no-rdkit fallback scripts exist
        no_rdkit_protein = os.path.exists(os.path.join(BASE_DIR, "pipeline", "prep_protein_no_rdkit.py"))
        no_rdkit_ligand = os.path.exists(os.path.join(BASE_DIR, "pipeline", "prep_ligands_no_rdkit.py"))
        fallback_ready = no_rdkit_protein and no_rdkit_ligand
            
        # Get downloaded proteins list
        proteins = []
        proteins_dir = os.path.join(DATA_DIR, "proteins")
        if os.path.exists(proteins_dir):
            for file in os.listdir(proteins_dir):
                if file.endswith(".pdbqt"):
                    proteins.append(file.replace(".pdbqt", "").upper())
                    
        # Get prepared ligands list
        ligands = []
        ligands_dir = os.path.join(DATA_DIR, "ligands")
        if os.path.exists(ligands_dir):
            for file in os.listdir(ligands_dir):
                if file.endswith(".pdbqt"):
                    ligands.append(file.replace(".pdbqt", ""))
        
        status = {
            "vina_installed": vina_installed,
            "rdkit_installed": rdkit_installed,
            "meeko_installed": meeko_installed,
            "requests_installed": requests_installed,
            "pipeline_ready": fallback_ready or (rdkit_installed and meeko_installed),
            "proteins": sorted(proteins),
            "ligands": sorted(ligands),
            "data_sources": {
                "rcsb_pdb": "https://www.rcsb.org/",
                "pubchem": "https://pubchem.ncbi.nlm.nih.gov/",
                "alphafold_db": "https://alphafold.ebi.ac.uk/"
            },
            "research_mode": "screening_only"
        }
        self.send_json_response(200, status)

    def handle_api_disease_targets(self):
        self.send_json_response(200, {
            "targets": DISEASE_TARGETS,
            "sources": [
                "RCSB Protein Data Bank",
                "AlphaFold Protein Structure Database",
                "PubChem PUG-REST"
            ],
            "disclaimer": "Educational and early-stage computational research only. Not medical advice, diagnosis, prevention, or treatment."
        })

    # API Handler: Environment Setup
    def handle_api_setup(self):
        def run_setup():
            setup_script = os.path.join(BASE_DIR, "pipeline", "setup_env.py")
            subprocess.run([sys.executable, setup_script])
            
        # Run setup asynchronously to avoid blocking the server
        threading.Thread(target=run_setup).start()
        self.send_json_response(200, {"success": True, "message": "Environment setup initiated in the background."})

    # API Handler: Download Protein
    def handle_api_download_protein(self, data):
        pdb_id = data.get("pdb_id", "").strip().upper()
        if not PDB_ID_RE.match(pdb_id):
            self.send_json_response(400, {"success": False, "error": "Invalid PDB ID (must be 4 alphanumeric characters)"})
            return
            
        def run_download():
            prep_script = os.path.join(BASE_DIR, "pipeline", "prep_protein_no_rdkit.py")
            subprocess.run([sys.executable, prep_script, pdb_id])
            
        threading.Thread(target=run_download).start()
        self.send_json_response(200, {"success": True, "message": f"Download and preparation of {pdb_id} initiated."})

    def handle_api_download_alphafold(self, data):
        accession = data.get("uniprot", "").strip().upper()
        label = data.get("label", accession).strip().lower().replace(" ", "_")
        if not UNIPROT_RE.match(accession):
            self.send_json_response(400, {"success": False, "error": "Invalid UniProt accession."})
            return
        if not SAFE_NAME_RE.match(label):
            self.send_json_response(400, {"success": False, "error": "Invalid local label."})
            return

        def run_download():
            try:
                os.makedirs(os.path.join(DATA_DIR, "proteins"), exist_ok=True)
                api_url = f"https://alphafold.ebi.ac.uk/api/prediction/{accession}"
                req = urllib.request.Request(api_url, headers={'User-Agent': 'JeenLab/1.0 research prototype'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    records = json.loads(resp.read().decode("utf-8"))
                if not records:
                    raise ValueError("No AlphaFold prediction found for accession.")
                pdb_url = records[0].get("pdbUrl")
                if not pdb_url:
                    raise ValueError("AlphaFold response did not include a PDB URL.")
                raw_path = os.path.join(DATA_DIR, "proteins", f"{label}_raw.pdb")
                with urllib.request.urlopen(pdb_url, timeout=60) as pdb_resp, open(raw_path, "wb") as out:
                    out.write(pdb_resp.read())
                prep_script = os.path.join(BASE_DIR, "pipeline", "prep_protein_no_rdkit.py")
                subprocess.run([sys.executable, prep_script, label, raw_path], check=False)
            except Exception as e:
                print(f"AlphaFold download failed for {accession}: {e}", file=sys.stderr)

        threading.Thread(target=run_download).start()
        self.send_json_response(200, {
            "success": True,
            "message": f"AlphaFold model download for {accession} initiated.",
            "source": "AlphaFold Protein Structure Database"
        })

    # API Handler: Prepare presets
    def handle_api_prep_presets(self):
        def run_presets():
            prep_script = os.path.join(BASE_DIR, "pipeline", "prep_ligands_no_rdkit.py")
            subprocess.run([sys.executable, prep_script, "--presets"])
            
        threading.Thread(target=run_presets).start()
        self.send_json_response(200, {"success": True, "message": "Ligand presets preparation initiated."})

    # API Handler: Prepare custom ligand
    def handle_api_prep_custom_ligand(self, data):
        name = data.get("name", "").strip().replace(" ", "_")
        smiles = data.get("smiles", "").strip()
        if not SAFE_NAME_RE.match(name) or not smiles or len(smiles) > 512:
            self.send_json_response(400, {"success": False, "error": "Name and SMILES are required."})
            return
            
        def run_custom():
            prep_script = os.path.join(BASE_DIR, "pipeline", "prep_ligands_no_rdkit.py")
            subprocess.run([sys.executable, prep_script, name, smiles])
            
        threading.Thread(target=run_custom).start()
        self.send_json_response(200, {"success": True, "message": f"Preparation of ligand {name} initiated."})

    # API Handler: Run Vina docking
    def handle_api_run_docking(self, data):
        protein_id = data.get("protein_id", "").strip()
        ligand_name = data.get("ligand_name", "").strip()
        x = data.get("center_x")
        y = data.get("center_y")
        z = data.get("center_z")
        size_x = data.get("size_x", 20)
        size_y = data.get("size_y", 20)
        size_z = data.get("size_z", 20)
        exhaustiveness = data.get("exhaustiveness", 8)
        
        if not SAFE_NAME_RE.match(protein_id) or not SAFE_NAME_RE.match(ligand_name) or x is None or y is None or z is None:
            self.send_json_response(400, {"success": False, "error": "Missing parameters for docking simulation."})
            return
        try:
            x, y, z = float(x), float(y), float(z)
            size_x, size_y, size_z = int(size_x), int(size_y), int(size_z)
            exhaustiveness = int(exhaustiveness)
            if any(v < 8 or v > 40 for v in (size_x, size_y, size_z)) or exhaustiveness not in (4, 8, 16, 32):
                raise ValueError
        except (TypeError, ValueError):
            self.send_json_response(400, {"success": False, "error": "Invalid grid or exhaustiveness values."})
            return
            
        def run_dock():
            dock_script = os.path.join(BASE_DIR, "pipeline", "run_docking.py")
            cmd = [
                sys.executable, dock_script,
                protein_id, ligand_name,
                str(x), str(y), str(z),
                str(size_x), str(size_y), str(size_z),
                str(exhaustiveness)
            ]
            subprocess.run(cmd)
            
        threading.Thread(target=run_dock).start()
        self.send_json_response(200, {"success": True, "message": f"Docking of {ligand_name} with {protein_id} started."})

    # API Handler: Get results summary
    def handle_api_results(self):
        summary_path = os.path.join(DATA_DIR, "results", "summary.json")
        summary_data = {}
        if os.path.exists(summary_path):
            try:
                with SUMMARY_LOCK:
                    with open(summary_path, 'r') as f:
                        summary_data = json.load(f)
                    if clean_summary_state(summary_data):
                        with open(summary_path, 'w') as f:
                            json.dump(summary_data, f, indent=4)
            except Exception as e:
                print(f"Error reading summary file: {e}")
        self.send_json_response(200, summary_data)

    # API Handler: Delete Protein
    def handle_api_delete_protein(self, data):
        name = data.get("name", "").strip()
        if not SAFE_NAME_RE.match(name):
            self.send_json_response(400, {"success": False, "error": "No protein name specified"})
            return
        results_dir = os.path.join(DATA_DIR, "proteins")
        deleted = 0
        for f in os.listdir(results_dir):
            root, ext = os.path.splitext(f)
            if root.lower() in {name.lower(), f"{name.lower()}_raw", f"{name.lower()}_clean"} and ext.lower() in {".pdb", ".pdbqt"}:
                os.remove(os.path.join(results_dir, f))
                deleted += 1
        self.send_json_response(200, {"success": True, "deleted": deleted})

    # API Handler: Delete Ligand
    def handle_api_delete_ligand(self, data):
        name = data.get("name", "").strip()
        if not SAFE_NAME_RE.match(name):
            self.send_json_response(400, {"success": False, "error": "No ligand name specified"})
            return
        ligands_dir = os.path.join(DATA_DIR, "ligands")
        deleted = 0
        for f in os.listdir(ligands_dir):
            root, ext = os.path.splitext(f)
            if root.lower() == name.lower() and ext.lower() == ".pdbqt":
                os.remove(os.path.join(ligands_dir, f))
                deleted += 1
        self.send_json_response(200, {"success": True, "deleted": deleted})

    # API Handler: Clear Results
    def handle_api_clear_results(self):
        results_dir = os.path.join(DATA_DIR, "results")
        if os.path.exists(results_dir):
            for f in os.listdir(results_dir):
                fp = os.path.join(results_dir, f)
                if os.path.isfile(fp) and os.path.splitext(f)[1].lower() in {".json", ".txt", ".pdbqt"}:
                    os.remove(fp)
        self.send_json_response(200, {"success": True})

    # API Handler: Download Manuscript
    def handle_api_download_manuscript(self, data):
        content = data.get("content", "").strip()
        filename = data.get("filename", "manuscript.md")
        if not content:
            self.send_json_response(400, {"success": False, "error": "No content provided"})
            return
        safe_name = os.path.basename(filename).replace("..", "")
        if not safe_name.lower().endswith(".md"):
            self.send_json_response(400, {"success": False, "error": "Only markdown manuscript files are supported"})
            return
        file_path = os.path.join(DATA_DIR, safe_name)
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            self.send_json_response(200, {"success": True, "url": f"/data/{safe_name}"})
        except Exception as e:
            self.send_json_response(500, {"success": False, "error": str(e)})

    # API Handler: Get specific log
    def handle_api_log(self, query):
        params = urllib.parse.parse_qs(query)
        file_path = params.get("file", [None])[0]
        
        if not file_path:
            self.send_json_response(400, {"success": False, "error": "No file parameter specified"})
            return
            
        # Ensure file path is local to data directory for security
        full_path = os.path.normpath(os.path.join(BASE_DIR, file_path))
        if not path_is_inside(full_path, DATA_DIR) or not os.path.exists(full_path):
            self.send_json_response(403, {"success": False, "error": "Forbidden or file not found"})
            return
            
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            self.send_json_response(200, {"success": True, "content": content})
        except Exception as e:
            self.send_json_response(500, {"success": False, "error": str(e)})

    # Static Files Handler
    def handle_static_files(self, path):
        # Default routing: "/" -> "/app/index.html"
        if path == "/":
            path = "/app/index.html"
            
        # Map relative path to local filesystem
        # Route requests starting with /data/ to DATA_DIR, /app/ to APP_DIR, otherwise APP_DIR
        if path.startswith("/data/"):
            relative_path = path[6:] # Strip /data/
            file_path = os.path.normpath(os.path.join(DATA_DIR, relative_path))
        elif path.startswith("/app/"):
            relative_path = path[5:] # Strip /app/
            file_path = os.path.normpath(os.path.join(APP_DIR, relative_path))
        else:
            file_path = os.path.normpath(os.path.join(APP_DIR, path.lstrip("/")))
            
        # Validate that the file resides inside our project directory (prevent path traversal)
        if not (path_is_inside(file_path, APP_DIR) or path_is_inside(file_path, DATA_DIR)):
            self.send_error_response(403, "Access denied")
            return
            
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_error_response(404, "File not found")
            return
            
        # Serve the file
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        # Text/PDBQT/PDB adjustments for WebGL/3Dmol.js loading
        if file_path.endswith(".pdbqt") or file_path.endswith(".pdb"):
            mime_type = "text/plain"
            
        try:
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(os.path.getsize(file_path)))
                self.end_headers()
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error_response(500, f"Error reading file: {e}")

    # Helpers
    def send_json_response(self, status_code, data):
        try:
            response_content = json.dumps(data).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_content)))
            self.end_headers()
            self.wfile.write(response_content)
        except Exception as e:
            print(f"Error sending JSON response: {e}")

    def send_error_response(self, status_code, message):
        self.send_json_response(status_code, {"success": False, "error": message})

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

def main():
    # Make sure app folder exists
    os.makedirs(APP_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print(f"Starting server on http://localhost:{PORT}")
    print(f"Serving web client from {APP_DIR}")
    print(f"Serving data folder from {DATA_DIR}")
    
    with ThreadedHTTPServer(("127.0.0.1", PORT), GenomeSentinelHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            sys.exit(0)

if __name__ == "__main__":
    main()
