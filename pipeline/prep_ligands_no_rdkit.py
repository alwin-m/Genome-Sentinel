import os
import sys
import re
import urllib.request
import urllib.error
import urllib.parse
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIGANDS_DIR = os.path.join(BASE_DIR, "data", "ligands")

PRESETS = {
    "donepezil": {
        "smiles": "COC1=C(C=C2C(=C1)CC(C2=O)CC3CCN(CC3)CC4=CC=CC=C4)OC",
        "description": "Alzheimer's treatment (BACE1 inhibitor)"
    },
    "chloroquine": {
        "smiles": "CCN(CC)CCCC(C)NC1=C2C=CC(=CC2=NC=C1)Cl",
        "description": "Antimalarial drug (PfDHFR target relative)"
    },
    "metformin": {
        "smiles": "CN(C)C(=N)N=C(N)N",
        "description": "Type 2 diabetes drug (DPP-4 pathway)"
    },
    "lapatinib": {
        "smiles": "CS(=O)(=O)CCNCC1=CC=C(O1)C2=CC3=C(C=C2)N=CN=C3NC4=CC(=C(C=C4)OCC5=CC(=CC=C5)F)Cl",
        "description": "Breast cancer drug (HER2 inhibitor)"
    },
    "aspirin": {
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "description": "Common anti-inflammatory"
    },
    "acetaminophen": {
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "description": "Common pain reliever (Paracetamol)"
    },
    "ibuprofen": {
        "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "description": "Common NSAID pain reliever"
    }
}

# Vina 1.2.5 atom types for 'vina' scoring (default):
#   C=aliphatic C, A=aromatic C, N=nitrogen, O=oxygen,
#   S=sulfur, P=phosphorus, H=hydrogen, F/Cl/Br/I=halogen
ELEMENT_TO_AD4 = {
    'C': 'C',
    'N': 'N',
    'O': 'O',
    'S': 'S',
    'P': 'P',
    'F': 'F',
    'Cl': 'Cl',
    'Br': 'Br',
    'I': 'I',
    'H': 'H',
}

ELEMENT_CHARGE = {
    'C': 0.0,
    'N': 0.0,
    'O': 0.0,
    'S': 0.0,
    'P': 0.0,
    'F': 0.0,
    'Cl': 0.0,
    'Br': 0.0,
    'I': 0.0,
    'H': 0.0,
}


def fetch_sdf_from_pubchem(smiles):
    encoded = urllib.parse.quote(smiles, safe='')
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/SDF"
    print(f"  Fetching from PubChem API...")
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')


def fetch_sdf_by_name(name):
    encoded = urllib.parse.quote(name, safe='')
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/SDF"
    print(f"  Fetching from PubChem API by name...")
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')


def parse_sdf_atoms(sdf_text):
    if '$$$$' in sdf_text:
        sdf_text = sdf_text.split('$$$$')[0]

    lines = sdf_text.splitlines()

    counts_idx = None
    for i, line in enumerate(lines):
        if i < 3:
            continue
        if 'V2000' in line or 'V3000' in line:
            counts_idx = i
            break
        if i == 3 and re.match(r'^\s*\d+\s+\d+', line):
            counts_idx = i
            break

    if counts_idx is None:
        raise ValueError("Could not locate counts line in SDF")

    num_atoms = int(lines[counts_idx][:3].strip())

    atoms = []
    for i in range(counts_idx + 1, counts_idx + 1 + num_atoms):
        line = lines[i]
        if len(line) < 30:
            continue

        x_str = line[0:10].strip()
        y_str = line[10:20].strip()
        z_str = line[20:30].strip()
        element = line[30:34].strip() if len(line) > 30 else ''

        if not element or element.isdigit():
            rest = line[34:].strip()
            if rest:
                element = rest.split()[0]

        if not x_str or not y_str or not z_str or not element:
            continue

        x, y, z = float(x_str), float(y_str), float(z_str)
        atoms.append((element, x, y, z))

    if len(atoms) != num_atoms:
        print(f"  Warning: expected {num_atoms} atoms but parsed {len(atoms)}")

    return atoms


def write_ligand_pdbqt(atoms, output_path):
    if not atoms:
        raise ValueError("No atoms to write")

    with open(output_path, 'w') as f:
        f.write("ROOT\n")
        for idx, (element, x, y, z) in enumerate(atoms, start=1):
            ad4_type = ELEMENT_TO_AD4.get(element, 'CA')
            atom_name = f"{element}{idx}"
            charge = ELEMENT_CHARGE.get(element, 0.0)

            # Proper PDB column alignment for Vina 1.2.5
            serial = f"{idx:>5d}"
            name = f"{atom_name:<4s}"
            res_name = "LIG"
            chain = "X"
            res_num = "1"
            occ = "1.00"
            temp = "0.00"
            charge_str = f"{charge:>10.3f}"
            type_str = f"{ad4_type:>4s}"
            f.write(
                f"ATOM  {serial} {name} {res_name} {chain}{res_num:>4s}    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}"
                f"{occ:>6s}{temp:>6s}{charge_str}{type_str}\n"
            )
        f.write("ENDROOT\n")
        f.write("TORSDOF 0\n")

    return True


def prepare_ligand(name, smiles, output_dir):
    name = name.lower().replace(" ", "_")
    output_path = os.path.join(output_dir, f"{name}.pdbqt")

    if os.path.exists(output_path):
        print(f"[SKIP] '{name}' PDBQT already exists at {output_path}")
        return {"success": True, "name": name, "pdbqt_file": output_path, "skipped": True}

    print(f"Preparing ligand '{name}' from SMILES: {smiles}")

    try:
        print("  Fetching 3D structure from PubChem...")
        try:
            sdf_text = fetch_sdf_from_pubchem(smiles)
        except urllib.error.HTTPError:
            print("  SMILES lookup failed, trying name-based lookup...")
            sdf_text = fetch_sdf_by_name(name)

        atoms = parse_sdf_atoms(sdf_text)
        print(f"  Parsed {len(atoms)} atoms from PubChem SDF")

        if not atoms:
            raise ValueError("No atoms parsed from SDF")

        print("  Writing PDBQT file...")
        write_ligand_pdbqt(atoms, output_path)
        print(f"  Successfully prepared PDBQT at {output_path}")

        return {"success": True, "name": name, "pdbqt_file": output_path, "skipped": False}

    except urllib.error.HTTPError as e:
        print(f"  FAILED: PubChem API error ({e.code}): {e.reason}")
        print(f"  Compound may not be in PubChem. Try prep_ligands.py (RDKit) instead.")
        return {"success": False, "error": f"PubChem HTTP {e.code}: {e.reason}"}

    except urllib.error.URLError as e:
        print(f"  FAILED: Network error: {e.reason}")
        return {"success": False, "error": f"Network error: {e.reason}"}

    except Exception as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def main():
    os.makedirs(LIGANDS_DIR, exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python prep_ligands_no_rdkit.py --presets")
        print("  python prep_ligands_no_rdkit.py <name> <SMILES>")
        sys.exit(1)

    if sys.argv[1] == "--presets":
        print(f"Preparing {len(PRESETS)} built-in ligand presets (no RDKit)...")
        results = []
        for name, info in PRESETS.items():
            res = prepare_ligand(name, info["smiles"], LIGANDS_DIR)
            results.append(res)
            time.sleep(0.3)

        success_count = sum(1 for r in results if r["success"])
        skipped_count = sum(1 for r in results if r.get("skipped"))
        print(f"\nDone: {success_count}/{len(PRESETS)} prepared ({skipped_count} skipped)")
    else:
        name = sys.argv[1]
        smiles = sys.argv[2]
        res = prepare_ligand(name, smiles, LIGANDS_DIR)
        if not res["success"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
