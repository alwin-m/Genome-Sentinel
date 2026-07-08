import os
import sys
import re
import urllib.request
import urllib.error
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTEINS_DIR = os.path.join(BASE_DIR, "data", "proteins")

REMOVE_RESIDUES = {"HOH", "WAT", "DOD", "ACT", "EDT", "PEG", "FMT", "GOL", "SO4", "PO4", "CON", "NAG", "BMA", "MAN", "GLC", "NDG"}

ELEMENT_TO_AD4_RECEPTOR = {
    'C': 'C', 'N': 'N', 'O': 'O', 'S': 'S',
    'P': 'P', 'F': 'F', 'Cl': 'Cl', 'Br': 'Br', 'I': 'I',
    'H': 'H', 'CA': 'CA', 'MG': 'MG', 'MN': 'MN',
    'ZN': 'ZN', 'FE': 'FE', 'CU': 'CU', 'NA': 'NA', 'K': 'K',
}


def extract_element_from_pdb_line(line):
    element = line[76:78].strip()
    if element:
        return element

    atom_name = line[12:16].strip()
    if atom_name:
        name_alpha = re.sub(r'[^A-Za-z]', '', atom_name)
        if len(name_alpha) >= 2:
            return name_alpha[:2]
        elif name_alpha:
            return name_alpha[0]

    return 'C'


def clean_pdb(input_path, output_path):
    print(f"  Cleaning PDB: removing water/heteroatoms...")

    kept = 0
    removed = 0

    with open(input_path, 'r') as inf, open(output_path, 'w') as outf:
        for line in inf:
            if line.startswith("ATOM"):
                outf.write(line)
                kept += 1
            elif line.startswith("HETATM"):
                res_name = line[17:20].strip()
                if res_name not in REMOVE_RESIDUES:
                    outf.write(line)
                    kept += 1
                else:
                    removed += 1
            elif line.startswith("TER") or line.startswith("END"):
                outf.write(line)

    print(f"  Cleaned PDB: kept {kept} atoms, removed {removed} heteroatoms")
    return kept > 0


def pdb_to_pdbqt_direct(input_pdb, output_pdbqt):
    print(f"  Converting PDB -> PDBQT (direct, no RDKit)...")

    atom_count = 0

    with open(input_pdb, 'r') as inf, open(output_pdbqt, 'w') as outf:
        for line in inf:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                element = extract_element_from_pdb_line(line)
                ad4_type = ELEMENT_TO_AD4_RECEPTOR.get(element, 'C')

                coord_x = line[30:38].strip()
                coord_y = line[38:46].strip()
                coord_z = line[46:54].strip()

                chain = line[21:22].strip() if len(line) > 21 else ' '
                res_name = line[17:20].strip() if len(line) > 17 else 'UNK'
                res_num = line[22:26].strip() if len(line) > 22 else '1'
                atom_name = line[12:16].strip() if len(line) > 12 else 'X'

                if not coord_x or not coord_y or not coord_z:
                    continue

                x, y, z = float(coord_x), float(coord_y), float(coord_z)

                alt_loc = line[16:17].strip() if len(line) > 16 else ' '
                occ = line[54:60].strip() if len(line) > 54 else '1.00'
                temp = line[60:66].strip() if len(line) > 60 else '0.00'

                line_start = line[:54] if len(line) >= 54 else line[:len(line)]

                # Vina 1.2.5 PDBQT: charge at cols 67-76 (10 chars), atom type at cols 77-80 (4 chars)
                charge_str = f"{0.000:>10.3f}"
                type_str = f"{ad4_type:>4s}"
                outf.write(
                    f"ATOM  {line[6:11].strip():>5s} {atom_name:<4s}{alt_loc:1s}"
                    f"{res_name:<3s} {chain:1s}{res_num:>4s}    "
                    f"{x:8.3f}{y:8.3f}{z:8.3f}"
                    f"{float(occ) if occ else 1.00:6.2f}{float(temp) if temp else 0.00:6.2f}"
                    f"{charge_str}{type_str}\n"
                )
                atom_count += 1
            elif line.startswith("TER") or line.startswith("END"):
                outf.write(line)

    print(f"  Wrote {atom_count} atoms to {output_pdbqt}")
    return atom_count > 0


def download_pdb(pdb_id, output_dir):
    pdb_id = pdb_id.strip().lower()
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    raw_path = os.path.join(output_dir, f"{pdb_id}_raw.pdb")

    print(f"  Downloading PDB {pdb_id.upper()} from RCSB...")
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp, open(raw_path, 'wb') as out:
        out.write(resp.read())

    print(f"  Saved raw PDB to {raw_path}")
    return raw_path


def prepare_protein(pdb_id, output_dir, pdb_path=None):
    pdb_id = pdb_id.strip().lower()
    pdbqt_path = os.path.join(output_dir, f"{pdb_id}.pdbqt")

    if os.path.exists(pdbqt_path):
        print(f"[SKIP] '{pdb_id}' PDBQT already exists at {pdbqt_path}")
        return {"success": True, "pdb_id": pdb_id, "pdbqt_file": pdbqt_path, "skipped": True}

    print(f"Preparing protein '{pdb_id.upper()}'...")

    try:
        if pdb_path is None:
            raw_path = download_pdb(pdb_id, output_dir)
        else:
            raw_path = pdb_path

        clean_path = os.path.join(output_dir, f"{pdb_id}_clean.pdb")

        clean_pdb(raw_path, clean_path)
        success = pdb_to_pdbqt_direct(clean_path, pdbqt_path)

        if not success:
            raise ValueError("No atoms written to PDBQT")

        print(f"  Successfully prepared PDBQT at {pdbqt_path}")
        return {
            "success": True,
            "pdb_id": pdb_id,
            "raw_file": raw_path if pdb_path is None else pdb_path,
            "clean_file": clean_path,
            "pdbqt_file": pdbqt_path,
            "skipped": False,
        }

    except urllib.error.HTTPError as e:
        print(f"  FAILED: Download error ({e.code}): {e.reason}")
        return {"success": False, "error": f"Download HTTP {e.code}: {e.reason}"}

    except urllib.error.URLError as e:
        print(f"  FAILED: Network error: {e.reason}")
        return {"success": False, "error": f"Network error: {e.reason}"}

    except Exception as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def main():
    os.makedirs(PROTEINS_DIR, exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python prep_protein_no_rdkit.py <PDB_ID>")
        print("  python prep_protein_no_rdkit.py <PDB_ID> <local_pdb_path>")
        sys.exit(1)

    pdb_id = sys.argv[1]
    pdb_path = sys.argv[2] if len(sys.argv) > 2 else None

    res = prepare_protein(pdb_id, PROTEINS_DIR, pdb_path)
    if res["success"]:
        print(f"Protein preparation completed: {res['pdbqt_file']}")
    else:
        print(f"Failed to prepare protein: {res['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
