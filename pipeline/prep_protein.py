import os
import sys
import urllib.request
import re

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTEINS_DIR = os.path.join(BASE_DIR, "data", "proteins")

def clean_pdb(input_path, output_path):
    """
    Cleans a PDB file by:
    1. Removing water molecules (HOH, WAT)
    2. Removing common crystallization buffers and non-protein heteroatoms
    3. Keeping only standard amino acid chains (typically Chain A is preferred, but we keep all ATOM records)
    """
    print(f"Cleaning PDB: {input_path} -> {output_path}")
    
    # Common water and crystallization agent residue names to remove
    remove_residues = {"HOH", "WAT", "DOD", "ACT", "EDT", "PEG", "FMT", "GOL", "SO4", "PO4", "CON"}
    
    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            if line.startswith("ATOM"):
                outfile.write(line)
            elif line.startswith("HETATM"):
                # Extract residue name (characters 17-20 in standard PDB)
                res_name = line[17:20].strip()
                if res_name not in remove_residues:
                    outfile.write(line)
            elif line.startswith("CONECT") or line.startswith("MASTER"):
                # Skip conect and master records to avoid format issues after cleaning
                continue
            elif line.startswith("TER") or line.startswith("ENDMDL") or line.startswith("END"):
                outfile.write(line)
                
    print("PDB cleaning completed.")

def prepare_receptor_pdbqt(pdb_path, pdbqt_path):
    """
    Converts PDB to PDBQT using RDKit (to add hydrogens) and Meeko.
    """
    print(f"Preparing receptor PDBQT: {pdb_path} -> {pdbqt_path}")
    try:
        from rdkit import Chem
        from meeko import Polymer
        
        # Load molecule using RDKit
        # removeHs=False because we want to load existing if any, then add standard ones
        print("Loading protein structure in RDKit...")
        mol = Chem.MolFromPDBFile(pdb_path, removeHs=False, sanitize=False)
        if mol is None:
            raise ValueError(f"RDKit failed to load PDB from {pdb_path}")
            
        print("Adding polar hydrogens...")
        # Since we are prepping a protein, standard AddHs can be used to ensure we have hydrogens.
        # Although it doesn't do pKa optimization, it's sufficient for basic docking grid calculation.
        mol_h = Chem.AddHs(mol, addCoords=True)
        
        # Write back to a temp PDB with hydrogens so Meeko can parse it as a PDB file
        temp_h_pdb = pdb_path.replace(".pdb", "_h.pdb")
        Chem.MolToPDBFile(mol_h, temp_h_pdb)
        
        print("Running Meeko Polymer parameterization...")
        polymer = Polymer.from_pdb_file(temp_h_pdb)
        pdbqt_string = polymer.write_pdbqt_string()
        
        with open(pdbqt_path, "w") as f:
            f.write(pdbqt_string)
            
        # Clean up temp file
        if os.path.exists(temp_h_pdb):
            os.remove(temp_h_pdb)
            
        print(f"Successfully created receptor PDBQT at {pdbqt_path}")
        return True
        
    except ImportError:
        print("RDKit or Meeko not installed. Falling back to a direct text conversion (no charges/hydrogens, Vina can still run).")
        # Direct fallback copy-convert:
        # Vina receptor files are very similar to PDB files.
        # A basic fallback just appends standard atom type at the end of each ATOM line.
        try:
            with open(pdb_path, 'r') as infile, open(pdbqt_path, 'w') as outfile:
                for line in infile:
                    if line.startswith("ATOM") or line.startswith("HETATM"):
                        # Get element symbol from columns 77-78
                        element = line[76:78].strip()
                        if not element:
                            # Fallback: get element from atom name
                            atom_name = line[12:16].strip()
                            element = atom_name[0] if atom_name else 'C'
                        # Write line with dummy charge (0.00) and element type as AD4 type
                        line_content = line[:54] # coordinates end at 54
                        # Vina expects: coordinates, occupancy (54-60), temp factor (60-66), partial charge (70-76), atom type (77-78)
                        charge = "  0.000"
                        outfile.write(f"{line_content.ljust(54)}  1.00  0.00{charge.rjust(14)} {element.upper()}\n")
                    elif line.startswith("TER") or line.startswith("END"):
                        outfile.write(line)
            print(f"Fallback converter completed receptor PDBQT at {pdbqt_path}")
            return True
        except Exception as e:
            print(f"Fallback converter failed: {e}", file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"Failed to prepare receptor PDBQT: {e}", file=sys.stderr)
        return False

def download_pdb(pdb_id, output_dir):
    pdb_id = pdb_id.strip().lower()
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    raw_path = os.path.join(output_dir, f"{pdb_id}_raw.pdb")
    clean_path = os.path.join(output_dir, f"{pdb_id}_clean.pdb")
    pdbqt_path = os.path.join(output_dir, f"{pdb_id}.pdbqt")
    
    print(f"Downloading PDB structure '{pdb_id.upper()}' from {url}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(raw_path, 'wb') as out_file:
            out_file.write(response.read())
        print(f"Downloaded raw structure to {raw_path}")
        
        # Clean protein
        clean_pdb(raw_path, clean_path)
        
        # Convert to PDBQT
        prepare_receptor_pdbqt(clean_path, pdbqt_path)
        
        return {
            "success": True,
            "pdb_id": pdb_id.upper(),
            "raw_file": raw_path,
            "clean_file": clean_path,
            "pdbqt_file": pdbqt_path
        }
    except Exception as e:
        print(f"Error downloading or processing PDB {pdb_id}: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prep_protein.py <PDB_ID>")
        sys.exit(1)
        
    pdb_id = sys.argv[1]
    os.makedirs(PROTEINS_DIR, exist_ok=True)
    res = download_pdb(pdb_id, PROTEINS_DIR)
    if res["success"]:
        print(f"Protein preparation completed successfully: {res['pdbqt_file']}")
    else:
        print(f"Failed to prepare protein: {res['error']}", file=sys.stderr)
        sys.exit(1)
