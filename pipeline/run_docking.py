import os
import sys
import subprocess
import json
import time
import re
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(BASE_DIR, "bin")
DATA_DIR = os.path.join(BASE_DIR, "data")
PROTEINS_DIR = os.path.join(DATA_DIR, "proteins")
LIGANDS_DIR = os.path.join(DATA_DIR, "ligands")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# Executable Path
VINA_EXE = os.path.join(BIN_DIR, "vina.exe")

def parse_vina_log(log_path):
    """
    Parses AutoDock Vina log to extract binding affinities.
    Returns a list of floats (kcal/mol) for each mode.
    """
    affinities = []
    if not os.path.exists(log_path):
        return affinities
        
    pattern = re.compile(r'^\s*(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)')
    reading_table = False
    
    with open(log_path, 'r') as f:
        for line in f:
            if "mode |   affinity | dist from best mode" in line:
                reading_table = True
                continue
            if reading_table:
                if "-----+------------+-----------+----------" in line:
                    continue
                match = pattern.match(line)
                if match:
                    affinity = float(match.group(2))
                    affinities.append(affinity)
                elif line.strip() == "" or "Writing output" in line or "Refining ligand" in line:
                    # End of table
                    reading_table = False
                    
    return affinities

def update_summary(protein_id, ligand_name, affinity, grid_config, status="completed", error_msg=""):
    summary_path = os.path.join(RESULTS_DIR, "summary.json")
    summary = {}
    
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r') as f:
                summary = json.load(f)
        except Exception:
            pass
            
    key = f"{protein_id.upper()}_{ligand_name.lower()}"
    summary[key] = {
        "protein_id": protein_id.upper(),
        "ligand_name": ligand_name,
        "binding_affinity": affinity, # float or null
        "grid_config": grid_config,
        "status": status,
        "error": error_msg,
        "timestamp": datetime.now().isoformat(),
        "output_pose": f"data/results/{protein_id.lower()}_{ligand_name.lower()}_out.pdbqt",
        "log_file": f"data/results/{protein_id.lower()}_{ligand_name.lower()}_log.txt"
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=4)

def run_docking_vina(protein_id, ligand_name, x, y, z, size_x=20, size_y=20, size_z=20, exhaustiveness=8):
    protein_id = protein_id.strip().lower()
    ligand_name = ligand_name.strip().lower()
    
    # Input paths
    receptor_pdbqt = os.path.join(PROTEINS_DIR, f"{protein_id}.pdbqt")
    ligand_pdbqt = os.path.join(LIGANDS_DIR, f"{ligand_name}.pdbqt")
    
    # Output paths
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_pdbqt = os.path.join(RESULTS_DIR, f"{protein_id}_{ligand_name}_out.pdbqt")
    log_file = os.path.join(RESULTS_DIR, f"{protein_id}_{ligand_name}_log.txt")
    
    grid_config = {
        "center_x": x, "center_y": y, "center_z": z,
        "size_x": size_x, "size_y": size_y, "size_z": size_z,
        "exhaustiveness": exhaustiveness
    }
    
    # Validate files
    if not os.path.exists(VINA_EXE):
        msg = f"AutoDock Vina executable not found at {VINA_EXE}. Please run environment setup first."
        update_summary(protein_id, ligand_name, None, grid_config, "failed", msg)
        return {"success": False, "error": msg}
        
    if not os.path.exists(receptor_pdbqt):
        msg = f"Receptor file not found: {receptor_pdbqt}. Please download and prepare it first."
        update_summary(protein_id, ligand_name, None, grid_config, "failed", msg)
        return {"success": False, "error": msg}
        
    if not os.path.exists(ligand_pdbqt):
        msg = f"Ligand file not found: {ligand_pdbqt}. Please prepare it first."
        update_summary(protein_id, ligand_name, None, grid_config, "failed", msg)
        return {"success": False, "error": msg}
        
    # Command formulation (vina 1.2.5 doesn't support --log)
    cmd = [
        VINA_EXE,
        "--receptor", receptor_pdbqt,
        "--ligand", ligand_pdbqt,
        "--center_x", str(x),
        "--center_y", str(y),
        "--center_z", str(z),
        "--size_x", str(size_x),
        "--size_y", str(size_y),
        "--size_z", str(size_z),
        "--exhaustiveness", str(exhaustiveness),
        "--out", out_pdbqt,
        "--verbosity", "1"
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    update_summary(protein_id, ligand_name, None, grid_config, "running")
    
    start_time = time.time()
    try:
        # Run process; redirect stdout to log file (vina 1.2.5 writes scoring to stdout)
        with open(log_file, 'w') as lf:
            result = subprocess.run(cmd, stdout=lf, stderr=subprocess.PIPE, text=True, check=True)
        elapsed = time.time() - start_time
        print(f"Docking completed in {elapsed:.1f} seconds.")
        
        # Parse affinity
        affinities = parse_vina_log(log_file)
        best_affinity = affinities[0] if affinities else None
        
        if best_affinity is not None:
            print(f"Top Binding Affinity: {best_affinity} kcal/mol")
            update_summary(protein_id, ligand_name, best_affinity, grid_config, "completed")
            return {
                "success": True,
                "affinity": best_affinity,
                "output_pose": out_pdbqt,
                "log_file": log_file,
                "duration": elapsed
            }
        else:
            msg = "Docking completed but no affinity scores were found in the log file."
            update_summary(protein_id, ligand_name, None, grid_config, "failed", msg)
            return {"success": False, "error": msg}
            
    except subprocess.CalledProcessError as e:
        msg = f"AutoDock Vina failed with return code {e.returncode}.\nStderr: {e.stderr}"
        print(msg, file=sys.stderr)
        update_summary(protein_id, ligand_name, None, grid_config, "failed", msg)
        return {"success": False, "error": msg}
    except Exception as e:
        msg = f"An unexpected error occurred: {e}"
        print(msg, file=sys.stderr)
        update_summary(protein_id, ligand_name, None, grid_config, "failed", msg)
        return {"success": False, "error": msg}

if __name__ == "__main__":
    if len(sys.argv) < 9:
        print("Usage: python run_docking.py <protein_id> <ligand_name> <x> <y> <z> <size_x> <size_y> <size_z> [exhaustiveness]")
        sys.exit(1)
        
    protein_id = sys.argv[1]
    ligand_name = sys.argv[2]
    x = float(sys.argv[3])
    y = float(sys.argv[4])
    z = float(sys.argv[5])
    sx = int(sys.argv[6])
    sy = int(sys.argv[7])
    sz = int(sys.argv[8])
    
    exh = int(sys.argv[9]) if len(sys.argv) > 9 else 8
    
    res = run_docking_vina(protein_id, ligand_name, x, y, z, sx, sy, sz, exh)
    if res["success"]:
        print("Docking run script completed successfully.")
    else:
        print(f"Docking run script failed: {res['error']}", file=sys.stderr)
        sys.exit(1)
