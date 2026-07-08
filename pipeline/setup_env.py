import os
import sys
import subprocess
import urllib.request
import shutil

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(BASE_DIR, "bin")
DATA_DIR = os.path.join(BASE_DIR, "data")
PROTEINS_DIR = os.path.join(DATA_DIR, "proteins")
LIGANDS_DIR = os.path.join(DATA_DIR, "ligands")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# Constants
VINA_URL = "https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_win.exe"
VINA_EXE_PATH = os.path.join(BIN_DIR, "vina.exe")

def ensure_directories():
    print("Creating directory structure...")
    for path in [BIN_DIR, DATA_DIR, PROTEINS_DIR, LIGANDS_DIR, RESULTS_DIR]:
        os.makedirs(path, exist_ok=True)
        print(f"  Created or verified: {path}")

def download_vina():
    if os.path.exists(VINA_EXE_PATH):
        print(f"AutoDock Vina already exists at {VINA_EXE_PATH}")
        return True
    
    print(f"Downloading AutoDock Vina from {VINA_URL}...")
    try:
        # User-agent header to avoid potential rate-limiting/blocking
        req = urllib.request.Request(
            VINA_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(VINA_EXE_PATH, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"Successfully downloaded AutoDock Vina to {VINA_EXE_PATH}")
        return True
    except Exception as e:
        print(f"Error downloading AutoDock Vina: {e}", file=sys.stderr)
        return False

def install_dependencies():
    packages = ["rdkit", "meeko", "requests", "safe-mol"]
    print("Checking and installing Python dependencies: ", ", ".join(packages))
    try:
        # Check and install each package
        for package in packages:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("All dependencies installed successfully.")
        return True
    except Exception as e:
        print(f"Error installing dependencies: {e}", file=sys.stderr)
        return False

def main():
    print("=== Genome Sentinel Environment Setup ===")
    ensure_directories()
    
    vina_success = download_vina()
    deps_success = install_dependencies()
    
    if vina_success and deps_success:
        print("\nSetup completed successfully! Environment is ready.")
        sys.exit(0)
    else:
        print("\nSetup encountered warnings or errors. Check logs above.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
