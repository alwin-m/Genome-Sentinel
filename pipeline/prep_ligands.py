import os
import sys
import json

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIGANDS_DIR = os.path.join(BASE_DIR, "data", "ligands")

# Standard presets of interest for the guide's disease targets
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

def prepare_ligand(name, smiles, output_dir):
    name = name.lower().replace(" ", "_")
    output_path = os.path.join(output_dir, f"{name}.pdbqt")
    sdf_path = os.path.join(output_dir, f"{name}.sdf")
    
    print(f"Preparing ligand '{name}' from SMILES: {smiles}")
    
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from meeko import MoleculePreparation
        
        # Create Molecule from SMILES
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES string: {smiles}")
            
        # Add Hydrogens (necessary for 3D embedding and docking chemistry)
        mol = Chem.AddHs(mol)
        
        # Generate 3D Coordinates
        print("Generating 3D conformation...")
        # Use ETKDG method for coordinate generation
        params = AllChem.ETKDGv3()
        params.useBasicKnowledge = True
        params.randomSeed = 42
        embed_status = AllChem.EmbedMolecule(mol, params)
        
        if embed_status == -1:
            # Fallback embedding
            print("Warning: Standard 3D embedding failed. Trying with random coordinates...")
            embed_status = AllChem.EmbedMolecule(mol, randomSeed=42)
            if embed_status == -1:
                raise ValueError("Could not embed molecule in 3D space.")
                
        # Optimize structure using molecular mechanics (MMFF)
        print("Optimizing geometry using MMFF...")
        AllChem.MMFFOptimizeMolecule(mol)
        
        # Save as SDF for reference / 3D viewer
        writer = Chem.SDWriter(sdf_path)
        writer.write(mol)
        writer.close()
        print(f"Saved optimized 3D SDF to {sdf_path}")
        
        # Convert to PDBQT using Meeko
        print("Converting to PDBQT...")
        preparator = MoleculePreparation()
        preparator.prepare(mol)
        pdbqt_string = preparator.write_pdbqt_string()
        
        with open(output_path, "w") as f:
            f.write(pdbqt_string)
            
        print(f"Successfully prepared PDBQT at {output_path}")
        return {
            "success": True,
            "name": name,
            "pdbqt_file": output_path,
            "sdf_file": sdf_path
        }
        
    except ImportError:
        print("RDKit or Meeko not installed. Cannot prepare 3D structure from SMILES dynamically.", file=sys.stderr)
        return {"success": False, "error": "RDKit/Meeko not installed"}
    except Exception as e:
        print(f"Failed to prepare ligand '{name}': {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}

def main():
    os.makedirs(LIGANDS_DIR, exist_ok=True)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python prep_ligands.py --presets              (Prepares all built-in drug presets)")
        print("  python prep_ligands.py <name> <SMILES>        (Prepares a custom ligand)")
        sys.exit(1)
        
    if sys.argv[1] == "--presets":
        print(f"Preparing {len(PRESETS)} built-in ligand presets...")
        results = []
        for name, info in PRESETS.items():
            res = prepare_ligand(name, info["smiles"], LIGANDS_DIR)
            results.append(res)
            
        success_count = sum(1 for r in results if r["success"])
        print(f"\nCompleted preset prep: {success_count}/{len(PRESETS)} ligands prepared successfully.")
        
    else:
        name = sys.argv[1]
        smiles = sys.argv[2]
        res = prepare_ligand(name, smiles, LIGANDS_DIR)
        if not res["success"]:
            sys.exit(1)

if __name__ == "__main__":
    main()
