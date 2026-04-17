"""Grader for the current SMILES / SMARTS / SMIRKS benchmark."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, Lipinski, rdChemReactions, rdMolDescriptors

# ----------------------------
# Low-level helpers
# ----------------------------


def mol(smiles: str) -> Optional[Chem.Mol]:
    if smiles is None:
        return None
    try:
        return Chem.MolFromSmiles(smiles)
    except Exception:
        return None


def canon(smiles: str) -> Optional[str]:
    m = mol(smiles)
    if m is None:
        return None
    try:
        return Chem.MolToSmiles(m, canonical=True)
    except Exception:
        return None


def canon_or_none(s: Any) -> Optional[str]:
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    return canon(s)


def canon_list(values: List[str]) -> List[str]:
    out = []
    for v in values or []:
        c = canon_or_none(v)
        if c is None:
            out.append(None)
        else:
            out.append(c)
    return out


def canon_list_sorted(values: List[str]) -> List[str]:
    cleaned = [c for c in canon_list(values) if c is not None]
    return sorted(cleaned)


def atoms_with_H(smiles: str) -> Optional[int]:
    m = mol(smiles)
    if m is None:
        return None
    return Chem.AddHs(m).GetNumAtoms()


def sp_carbon_count(smiles: str) -> Optional[int]:
    m = mol(smiles)
    if m is None:
        return None
    return sum(
        1
        for a in m.GetAtoms()
        if a.GetSymbol() == "C" and a.GetHybridization() == Chem.HybridizationType.SP
    )


def unique_carbon_environments(smiles: str) -> Optional[int]:
    m = mol(smiles)
    if m is None:
        return None
    ranks = list(Chem.CanonicalRankAtoms(m, breakTies=False))
    carbon_ranks = {ranks[i] for i, a in enumerate(m.GetAtoms()) if a.GetSymbol() == "C"}
    return len(carbon_ranks)


def smarts_match_count(smarts: str, target_smiles: str) -> Optional[int]:
    patt = Chem.MolFromSmarts(smarts)
    t = mol(target_smiles)
    if patt is None or t is None:
        return None
    return len(t.GetSubstructMatches(patt))


def run_smirks_single(smirks: str, reactants: List[str]) -> Optional[List[str]]:
    """Run a SMIRKS transform and return one deterministic set of product SMILES."""
    rxn = rdChemReactions.ReactionFromSmarts(smirks)
    mols = [mol(r) for r in reactants]
    if any(m is None for m in mols):
        return None
    outs = rxn.RunReactants(tuple(mols))
    if not outs:
        return None
    frags = outs[0]
    result = []
    for p in frags:
        try:
            Chem.SanitizeMol(p)
        except Exception:
            pass
        result.append(Chem.MolToSmiles(p))
    return sorted(canon_list(result))


# ----------------------------
# Answer-key computation
# ----------------------------


_Q1_SMILES = "CCSCCO" * 28
_Q2_SMILES = "CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)"
_Q3_SMILES = "NCC(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)CN"
_Q4_SMARTS = "[#6][#6][#6][#6][#6][#6][#6][#6][#6][#6]"
_Q4_TARGET = "C" * 11
_Q5_SMILES = "c1cc2ccc3ccc4ccc5ccc6ccc1c1c2c3c4c5c61"
_Q6_SMILES = "O=C1CCC2(CC1)OCCO2"
_Q7_SMILES = "C12C3C4C1C5C2C3C45"
_Q8_SMILES = "C12c3ccccc3C(c3cccnc31)c1ccccc12"
_Q9_SMILES = "CCCC#Cc1ccc(-c2ccc(O)cc2)cc1"
_Q9_TAUT = "CCCC(=O)c1ccc(-c2ccc(O)cc2)cc1"
_Q10_SMIRKS = "[C:1]=[C:2].[H][H:3]>>[C:1]([H:3])[C:2][H]"
_Q10_REACTANTS = ["C=Cc1ccccc1", "[H][H]"]
_Q11_SMIRKS = "[C:1](=[O:2])[OH:3].[OH:4][C:5]>>[C:1](=[O:2])[O:4][C:5].[H]O[H]"
_Q11_REACTANTS = ["CC(=O)O", "OCC"]
_Q12_SMIRKS = "[C:1][Cl:2].[NH3:3]>>[C:1][NH2:3].[Cl-:2]"
_Q12_REACTANTS = ["CCCCCl", "N"]
_Q13_MONOMER = "CC(=C)C(=O)OC"
_Q14_OLIGO = "CC(c1ccncc1)CC(c1ccncc1)CC(c1ccncc1)CC(c1ccncc1)"
_Q14_MONOMER = "C=Cc1ccncc1"
_Q15_SMARTS = "[c;$(c1ccccc1)][CX3](=[OX1])[OX2][c;$(c1ccccc1)]"
_Q15_TARGET = "O=C(Oc1ccc(Cl)cc1)Oc1ccc([N+](=O)[O-])cc1"
_Q16_SMARTS = "[CX4H0]([#6])([#6])([#6])([#6])"
_Q16_TARGET = "CC(C)(C)C(C)(C)C(C)(C)C(C)(C)C"
_Q17_RAW = "CCOC(=O)c1cc ccc1"
_Q18_RAW = "CCCCCC\tCCCCCC"
_Q19_RAW = "CC(=\nO)N"

_Q6_PARENT = "O=C1CCC(=O)CC1"
_Q6_ALLOWED_REAGENTS = ["OCCO"]
_Q6_FUNCTIONAL_GROUP_ALIASES = {"ketal", "acetal"}

_Q13_ACCEPTED_MONOMERS = ["CC(=C)C(=O)OC"]
_Q14_ACCEPTED_MONOMERS = ["C=Cc1ccncc1"]

_PUBLIC_DIAGNOSTIC_REFERENCE = {
    "Q-C1": {
        "status": "unscored diagnostic",
        "prompt_summary": "IHD vs ring-budget contradiction",
        "public_reference_answer": {
            "smiles": "c1ccc(cc1)C2CCC(NC(=O)c3ccccc3)CC2O",
        },
    },
    "Q-C2": {
        "status": "unscored diagnostic",
        "prompt_summary": "fully aromatic ring with explicit stereocenter but no sp3 atoms",
        "public_reference_answer": {
            "smiles": "c1cc[nH]c(c1)[C@H](C)C",
        },
    },
    "Q-C3": {
        "status": "unscored diagnostic",
        "prompt_summary": "quaternary ammonium required to be neutral without a countercharge",
        "public_reference_answer": {
            "smiles": "C[N+](C)(C)CCO",
        },
    },
    "Q-C5": {
        "status": "unscored diagnostic",
        "prompt_summary": "heteroatom element count conflicts with stated N/O/S totals",
        "public_reference_answer": {
            "smiles": "c1nc(=O)sc(c1)N",
        },
    },
    "Q-C8": {
        "status": "unscored diagnostic",
        "prompt_summary": "formula and ring topology contradict the stated unsaturation budget",
        "public_reference_answer": {
            "smiles": "c1ccc(cc1)C2CCC(N(C)C)CC2C3CCC(O)CC3O",
        },
    },
    "Q-C10": {
        "status": "unscored diagnostic",
        "prompt_summary": "symmetry reduces the stated stereoisomer count",
        "public_reference_answer": {
            "smiles_list": [
                "OC[C@H]1[C@H](CO)[C@H](CO)[C@H]1CO",
            ],
        },
    },
}


def compute_answer_key() -> Dict[str, Any]:
    m1 = mol(_Q1_SMILES)
    m2 = mol(_Q2_SMILES)
    m3 = mol(_Q3_SMILES)
    m5 = mol(_Q5_SMILES)
    m6 = mol(_Q6_SMILES)
    m7 = mol(_Q7_SMILES)
    m8 = mol(_Q8_SMILES)
    m9 = mol(_Q9_SMILES)
    m14 = mol(_Q14_OLIGO)
    m16 = mol(_Q16_TARGET)

    return {
        "Q1": {
            "heavy_atoms": m1.GetNumHeavyAtoms(),
            "total_atoms_with_H": atoms_with_H(_Q1_SMILES),
            "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(m1),
        },
        "Q2": {
            "heavy_atoms": m2.GetNumHeavyAtoms(),
            "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(m2),
            "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(m2),
        },
        "Q3": {
            "heavy_atoms": m3.GetNumHeavyAtoms(),
            "h_bond_donors": Lipinski.NumHDonors(m3),
            "h_bond_acceptors": Lipinski.NumHAcceptors(m3),
        },
        "Q4": {"match_count": smarts_match_count(_Q4_SMARTS, _Q4_TARGET)},
        "Q5": {
            "ring_count": m5.GetRingInfo().NumRings(),
            "heavy_atoms": m5.GetNumHeavyAtoms(),
            "molecular_formula": rdMolDescriptors.CalcMolFormula(m5),
        },
        "Q6": {
            "ring_count": m6.GetRingInfo().NumRings(),
            "reagent_canonical_smiles_allowed": sorted(
                canon(r) for r in _Q6_ALLOWED_REAGENTS
            ),
            "parent_ketone": canon(_Q6_PARENT),
            "functional_group_allowed": sorted(_Q6_FUNCTIONAL_GROUP_ALIASES),
        },
        "Q7": {
            "heavy_atoms": m7.GetNumHeavyAtoms(),
            "ring_count": m7.GetRingInfo().NumRings(),
            "unique_carbons": unique_carbon_environments(_Q7_SMILES),
        },
        "Q8": {
            "heavy_atoms": m8.GetNumHeavyAtoms(),
            "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(m8),
            "ring_count": m8.GetRingInfo().NumRings(),
        },
        "Q9": {
            "heavy_atoms": m9.GetNumHeavyAtoms(),
            "sp_carbons": sp_carbon_count(_Q9_SMILES),
            "tautomer_canon": canon(_Q9_TAUT),
        },
        "Q10": {
            "product_canon_accepted": [canon("CCc1ccccc1")],
        },
        "Q11": {
            "products_canon_sorted": sorted([canon("CCOC(C)=O"), canon("O")]),
        },
        "Q12": {
            "products_canon_sorted": sorted([canon("CCCCN"), canon("[Cl-]")]),
        },
        "Q13": {
            "monomer_canon_accepted": sorted(canon(s) for s in _Q13_ACCEPTED_MONOMERS),
        },
        "Q14": {
            "monomer_canon_accepted": sorted(canon(s) for s in _Q14_ACCEPTED_MONOMERS),
            "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(m14),
        },
        "Q15": {"match_count": smarts_match_count(_Q15_SMARTS, _Q15_TARGET)},
        "Q16": {"match_count": smarts_match_count(_Q16_SMARTS, _Q16_TARGET)},
        "Q17": {
            "fixed_smiles": "".join(_Q17_RAW.split()),
            "canonical_smiles": canon("".join(_Q17_RAW.split())),
        },
        "Q18": {
            "fixed_smiles": "".join(_Q18_RAW.split()),
            "canonical_smiles": canon("".join(_Q18_RAW.split())),
        },
        "Q19": {
            "fixed_smiles": "".join(_Q19_RAW.split()),
            "canonical_smiles": canon("".join(_Q19_RAW.split())),
        },
        "Q20": {
            "constraints": {
                "heavy_atoms": 50,
                "rings": 6,
                "distinct_heteroatom_elements": 3,
                "no_halogens": True,
                "single_connected": True,
                "neutral": True,
                "no_ring_with_mixed_heteroatoms": True,
            },
            "example_solution": canon(
                "CCCCCCCCCCCc1cccc(Cc2ccccc2Cc2ccccc2Cc2ccncc2Cc2ccoc2Cc2ccsc2)c1"
            ),
        },
    }


def compute_public_answer_key() -> Dict[str, Any]:
    public_key: Dict[str, Any] = {}
    for qid in [f"Q{i}" for i in range(1, 25)]:
        public_key[qid] = {
            "status": "trusted answer withheld",
            "public_note": "Trusted scoring material is withheld from the public repository.",
        }
    public_key.update(_PUBLIC_DIAGNOSTIC_REFERENCE)
    return public_key


# ----------------------------
# Grading per-question (returns earned, max, details)
# ----------------------------


def _grade_multi_fields(
    expected: Dict[str, Any], got: Dict[str, Any], fields: List[Tuple[str, float]]
) -> Tuple[float, float, Dict[str, Any]]:
    total = sum(w for _, w in fields)
    earned = 0.0
    detail: Dict[str, Any] = {}
    got = got if isinstance(got, dict) else {}
    for key, weight in fields:
        want = expected.get(key)
        have = got.get(key)
        ok = have == want
        earned += weight if ok else 0.0
        detail[key] = {"expected": want, "got": have, "ok": ok, "weight": weight}
    return earned, total, detail


def _grade_smiles_equals(expected_canon: Optional[str], got: Any) -> Tuple[bool, Dict[str, Any]]:
    got_canon = canon_or_none(got)
    ok = got_canon is not None and got_canon == expected_canon
    return ok, {"expected_canon": expected_canon, "got_canon": got_canon}


def _grade_smiles_in_list(allowed_canons: List[str], got: Any) -> Tuple[bool, Dict[str, Any]]:
    got_canon = canon_or_none(got)
    ok = got_canon is not None and got_canon in set(allowed_canons)
    return ok, {"allowed_canons": allowed_canons, "got_canon": got_canon}


def _grade_sorted_smiles_list(
    expected_sorted_canons: List[str], got: Any
) -> Tuple[bool, Dict[str, Any]]:
    if not isinstance(got, list):
        return False, {"expected": expected_sorted_canons, "got": got, "note": "not_a_list"}
    got_sorted = canon_list_sorted(got)
    ok = got_sorted == expected_sorted_canons
    return ok, {"expected": expected_sorted_canons, "got_sorted": got_sorted}


def _validate_q20(smi: Any, constraints: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    report: Dict[str, Any] = {"checks": {}}
    m = mol(smi) if isinstance(smi, str) else None
    if m is None:
        report["checks"]["parseable"] = False
        return False, report
    report["checks"]["parseable"] = True

    ri = m.GetRingInfo()
    heavy = m.GetNumHeavyAtoms()
    rings = ri.NumRings()
    report["checks"]["heavy_atoms"] = {
        "expected": constraints["heavy_atoms"],
        "got": heavy,
        "ok": heavy == constraints["heavy_atoms"],
    }
    report["checks"]["rings"] = {
        "expected": constraints["rings"],
        "got": rings,
        "ok": rings == constraints["rings"],
    }
    hets = set()
    halo = False
    for a in m.GetAtoms():
        z = a.GetAtomicNum()
        if z in (9, 17, 35, 53):
            halo = True
        if z not in (1, 6):
            hets.add(a.GetSymbol())
    hets.discard("F")
    hets.discard("Cl")
    hets.discard("Br")
    hets.discard("I")
    report["checks"]["no_halogens"] = {"ok": not halo, "got_halogens": halo}
    report["checks"]["distinct_heteroatom_elements"] = {
        "expected": constraints["distinct_heteroatom_elements"],
        "got_elements": sorted(hets),
        "got_count": len(hets),
        "ok": len(hets) == constraints["distinct_heteroatom_elements"],
    }
    single_type = True
    ring_hets = []
    for ring in ri.AtomRings():
        ts = {
            m.GetAtomWithIdx(i).GetSymbol()
            for i in ring
            if m.GetAtomWithIdx(i).GetAtomicNum() not in (1, 6)
        }
        ring_hets.append(sorted(ts))
        if len(ts) > 1:
            single_type = False
    report["checks"]["no_ring_with_mixed_heteroatoms"] = {
        "ok": single_type,
        "ring_heteroatom_sets": ring_hets,
    }
    charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    report["checks"]["neutral"] = {"ok": charge == 0, "formal_charge": charge}
    frags = Chem.GetMolFrags(m)
    report["checks"]["single_connected"] = {"ok": len(frags) == 1, "fragment_count": len(frags)}
    all_ok = all(
        v.get("ok", False) for v in report["checks"].values() if isinstance(v, dict)
    )
    return all_ok, report


def _count_fused_ring_pairs(m: Chem.Mol) -> int:
    """Count pairs of rings that share 2+ atoms (fused)."""
    ri = m.GetRingInfo()
    rings = [set(r) for r in ri.AtomRings()]
    pairs = 0
    for i in range(len(rings)):
        for j in range(i + 1, len(rings)):
            if len(rings[i] & rings[j]) >= 2:
                pairs += 1
    return pairs


def _atoms_in_at_least_k_rings(m: Chem.Mol, k: int) -> int:
    """Count atoms that belong to at least k rings."""
    from collections import Counter
    ri = m.GetRingInfo()
    cnt = Counter()
    for r in ri.AtomRings():
        for idx in r:
            cnt[idx] += 1
    return sum(1 for c in cnt.values() if c >= k)


def _ring_size_histogram(m: Chem.Mol) -> Dict[int, int]:
    """Return histogram of ring sizes."""
    ri = m.GetRingInfo()
    from collections import Counter
    return Counter(len(r) for r in ri.AtomRings())


def _aromatic_atom_count(m: Chem.Mol) -> int:
    return sum(1 for a in m.GetAtoms() if a.GetIsAromatic())


def _hetero_nos_counts(m: Chem.Mol) -> Tuple[int, int, int]:
    """Return (N_count, O_count, S_count)."""
    n = o = s = 0
    for a in m.GetAtoms():
        z = a.GetAtomicNum()
        if z == 7:
            n += 1
        elif z == 8:
            o += 1
        elif z == 16:
            s += 1
    return n, o, s


def _count_nH_aromatic(m: Chem.Mol) -> int:
    patt = Chem.MolFromSmarts("[nH]")
    if patt is None:
        return 0
    return len(m.GetSubstructMatches(patt))


def _has_isotopes(m: Chem.Mol) -> bool:
    return any(a.GetIsotope() != 0 for a in m.GetAtoms())


def _has_atom_mapping(m: Chem.Mol) -> bool:
    return any(a.GetAtomMapNum() != 0 for a in m.GetAtoms())


def _has_formal_charges(m: Chem.Mol) -> bool:
    return any(a.GetFormalCharge() != 0 for a in m.GetAtoms())


def _validate_q21(smi: Any) -> Tuple[bool, Dict[str, Any]]:
    report: Dict[str, Any] = {"checks": {}}
    m = mol(smi) if isinstance(smi, str) else None
    if m is None:
        report["checks"]["parseable"] = False
        return False, report
    report["checks"]["parseable"] = True

    # heavy atoms
    heavy = m.GetNumHeavyAtoms()
    report["checks"]["heavy_atoms"] = {"expected": 34, "got": heavy, "ok": heavy == 34}
    # sssr rings
    rings = m.GetRingInfo().NumRings()
    report["checks"]["rings"] = {"expected": 7, "got": rings, "ok": rings == 7}
    # ring sizes: five 6-membered, two 5-membered
    hist = _ring_size_histogram(m)
    ok_sizes = hist.get(6, 0) == 5 and hist.get(5, 0) == 2
    report["checks"]["ring_sizes"] = {"expected": {6: 5, 5: 2}, "got": dict(hist), "ok": ok_sizes}
    # aromatic atoms
    arom_atoms = _aromatic_atom_count(m)
    report["checks"]["aromatic_atoms"] = {"expected": 34, "got": arom_atoms, "ok": arom_atoms == 34}
    # hetero counts N,O,S
    n, o, s = _hetero_nos_counts(m)
    ok_hetero = (n == 3 and o == 1 and s == 1)
    report["checks"]["hetero_counts"] = {"expected": {"N": 3, "O": 1, "S": 1}, "got": {"N": n, "O": o, "S": s}, "ok": ok_hetero}
    # fused pairs
    fused = _count_fused_ring_pairs(m)
    report["checks"]["fused_pairs"] = {"expected": 3, "got": fused, "ok": fused == 3}
    # atoms in >=2 rings
    atoms_2plus = _atoms_in_at_least_k_rings(m, 2)
    report["checks"]["atoms_in_at_least_2_rings"] = {"expected": 6, "got": atoms_2plus, "ok": atoms_2plus == 6}
    # neutral
    charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    report["checks"]["neutral"] = {"ok": charge == 0, "formal_charge": charge}
    report["checks"]["no_isotopes"] = {"ok": not _has_isotopes(m), "has_isotopes": _has_isotopes(m)}
    report["checks"]["no_charges"] = {"ok": not _has_formal_charges(m), "has_charges": _has_formal_charges(m)}
    # no halogens
    halos = any(a.GetAtomicNum() in (9, 17, 35, 53) for a in m.GetAtoms())
    report["checks"]["no_halogens"] = {"ok": not halos, "has_halogens": halos}
    # single connected
    frags = Chem.GetMolFrags(m)
    report["checks"]["single_connected"] = {"ok": len(frags) == 1, "fragment_count": len(frags)}

    all_ok = all(v.get("ok", False) for v in report["checks"].values() if isinstance(v, dict))
    return all_ok, report


def _validate_q22(smi: Any) -> Tuple[bool, Dict[str, Any]]:
    report: Dict[str, Any] = {"checks": {}}
    m = mol(smi) if isinstance(smi, str) else None
    if m is None:
        report["checks"]["parseable"] = False
        return False, report
    report["checks"]["parseable"] = True

    heavy = m.GetNumHeavyAtoms()
    report["checks"]["heavy_atoms"] = {"expected": 34, "got": heavy, "ok": heavy == 34}
    rings = m.GetRingInfo().NumRings()
    report["checks"]["rings"] = {"expected": 7, "got": rings, "ok": rings == 7}
    hist = _ring_size_histogram(m)
    ok_sizes = hist.get(6, 0) == 5 and hist.get(5, 0) == 2
    report["checks"]["ring_sizes"] = {"expected": {6: 5, 5: 2}, "got": dict(hist), "ok": ok_sizes}
    arom_atoms = _aromatic_atom_count(m)
    report["checks"]["aromatic_atoms"] = {"expected": 34, "got": arom_atoms, "ok": arom_atoms == 34}
    n, o, s = _hetero_nos_counts(m)
    ok_hetero = (n == 4 and o == 1 and s == 1)
    report["checks"]["hetero_counts"] = {"expected": {"N": 4, "O": 1, "S": 1}, "got": {"N": n, "O": o, "S": s}, "ok": ok_hetero}
    # HBA/HBD
    hbd = Lipinski.NumHDonors(m)
    hba = Lipinski.NumHAcceptors(m)
    report["checks"]["hbd"] = {"expected": 0, "got": hbd, "ok": hbd == 0}
    report["checks"]["hba"] = {"expected": 6, "got": hba, "ok": hba == 6}
    fused = _count_fused_ring_pairs(m)
    report["checks"]["fused_pairs"] = {"expected": 3, "got": fused, "ok": fused == 3}
    rot = rdMolDescriptors.CalcNumRotatableBonds(m)
    report["checks"]["rotatable_bonds"] = {"expected": 3, "got": rot, "ok": rot == 3}
    charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    report["checks"]["neutral"] = {"ok": charge == 0, "formal_charge": charge}
    report["checks"]["no_isotopes"] = {"ok": not _has_isotopes(m), "has_isotopes": _has_isotopes(m)}
    report["checks"]["no_atom_mapping"] = {
        "ok": not _has_atom_mapping(m),
        "has_atom_mapping": _has_atom_mapping(m),
    }
    halos = any(a.GetAtomicNum() in (9, 17, 35, 53) for a in m.GetAtoms())
    report["checks"]["no_halogens"] = {"ok": not halos, "has_halogens": halos}
    frags = Chem.GetMolFrags(m)
    report["checks"]["single_connected"] = {"ok": len(frags) == 1, "fragment_count": len(frags)}

    all_ok = all(v.get("ok", False) for v in report["checks"].values() if isinstance(v, dict))
    return all_ok, report


def _validate_q23(smi: Any) -> Tuple[bool, Dict[str, Any]]:
    report: Dict[str, Any] = {"checks": {}}
    m = mol(smi) if isinstance(smi, str) else None
    if m is None:
        report["checks"]["parseable"] = False
        return False, report
    report["checks"]["parseable"] = True

    heavy = m.GetNumHeavyAtoms()
    report["checks"]["heavy_atoms"] = {"expected": 28, "got": heavy, "ok": heavy == 28}
    rings = m.GetRingInfo().NumRings()
    report["checks"]["rings"] = {"expected": 6, "got": rings, "ok": rings == 6}
    hist = _ring_size_histogram(m)
    ok_sizes = hist.get(6, 0) == 4 and hist.get(5, 0) == 2
    report["checks"]["ring_sizes"] = {"expected": {6: 4, 5: 2}, "got": dict(hist), "ok": ok_sizes}
    arom_atoms = _aromatic_atom_count(m)
    report["checks"]["aromatic_atoms"] = {"expected": 28, "got": arom_atoms, "ok": arom_atoms == 28}
    n, o, s = _hetero_nos_counts(m)
    ok_hetero = (n == 4 and o == 1 and s == 0)
    report["checks"]["hetero_counts"] = {"expected": {"N": 4, "O": 1, "S": 0}, "got": {"N": n, "O": o, "S": s}, "ok": ok_hetero}
    hbd = Lipinski.NumHDonors(m)
    hba = Lipinski.NumHAcceptors(m)
    report["checks"]["hbd"] = {"expected": 0, "got": hbd, "ok": hbd == 0}
    report["checks"]["hba"] = {"expected": 5, "got": hba, "ok": hba == 5}
    fused = _count_fused_ring_pairs(m)
    report["checks"]["fused_pairs"] = {"expected": 3, "got": fused, "ok": fused == 3}
    rot = rdMolDescriptors.CalcNumRotatableBonds(m)
    report["checks"]["rotatable_bonds"] = {"expected": 2, "got": rot, "ok": rot == 2}
    charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    report["checks"]["neutral"] = {"ok": charge == 0, "formal_charge": charge}
    report["checks"]["no_isotopes"] = {"ok": not _has_isotopes(m), "has_isotopes": _has_isotopes(m)}
    report["checks"]["no_charges"] = {"ok": not _has_formal_charges(m), "has_charges": _has_formal_charges(m)}
    halos = any(a.GetAtomicNum() in (9, 17, 35, 53) for a in m.GetAtoms())
    report["checks"]["no_halogens"] = {"ok": not halos, "has_halogens": halos}
    frags = Chem.GetMolFrags(m)
    report["checks"]["single_connected"] = {"ok": len(frags) == 1, "fragment_count": len(frags)}

    all_ok = all(v.get("ok", False) for v in report["checks"].values() if isinstance(v, dict))
    return all_ok, report


def _validate_q24(smi: Any) -> Tuple[bool, Dict[str, Any]]:
    report: Dict[str, Any] = {"checks": {}}
    m = mol(smi) if isinstance(smi, str) else None
    if m is None:
        report["checks"]["parseable"] = False
        return False, report
    report["checks"]["parseable"] = True

    heavy = m.GetNumHeavyAtoms()
    report["checks"]["heavy_atoms"] = {"expected": 25, "got": heavy, "ok": heavy == 25}
    rings = m.GetRingInfo().NumRings()
    report["checks"]["rings"] = {"expected": 5, "got": rings, "ok": rings == 5}
    hist = _ring_size_histogram(m)
    ok_sizes = hist.get(6, 0) == 4 and hist.get(5, 0) == 1
    report["checks"]["ring_sizes"] = {"expected": {6: 4, 5: 1}, "got": dict(hist), "ok": ok_sizes}
    arom_atoms = _aromatic_atom_count(m)
    report["checks"]["aromatic_atoms"] = {"expected": 25, "got": arom_atoms, "ok": arom_atoms == 25}
    n, o, s = _hetero_nos_counts(m)
    ok_hetero = (n == 2 and o == 1 and s == 0)
    report["checks"]["hetero_counts"] = {"expected": {"N": 2, "O": 1, "S": 0}, "got": {"N": n, "O": o, "S": s}, "ok": ok_hetero}
    hbd = Lipinski.NumHDonors(m)
    hba = Lipinski.NumHAcceptors(m)
    report["checks"]["hbd"] = {"expected": 0, "got": hbd, "ok": hbd == 0}
    report["checks"]["hba"] = {"expected": 3, "got": hba, "ok": hba == 3}
    fused = _count_fused_ring_pairs(m)
    report["checks"]["fused_pairs"] = {"expected": 2, "got": fused, "ok": fused == 2}
    rot = rdMolDescriptors.CalcNumRotatableBonds(m)
    report["checks"]["rotatable_bonds"] = {"expected": 2, "got": rot, "ok": rot == 2}
    charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    report["checks"]["neutral"] = {"ok": charge == 0, "formal_charge": charge}
    report["checks"]["no_isotopes"] = {"ok": not _has_isotopes(m), "has_isotopes": _has_isotopes(m)}
    report["checks"]["no_charges"] = {"ok": not _has_formal_charges(m), "has_charges": _has_formal_charges(m)}
    halos = any(a.GetAtomicNum() in (9, 17, 35, 53) for a in m.GetAtoms())
    report["checks"]["no_halogens"] = {"ok": not halos, "has_halogens": halos}
    frags = Chem.GetMolFrags(m)
    report["checks"]["single_connected"] = {"ok": len(frags) == 1, "fragment_count": len(frags)}

    all_ok = all(v.get("ok", False) for v in report["checks"].values() if isinstance(v, dict))
    return all_ok, report


def grade(submission_json: Dict[str, Any]) -> Dict[str, Any]:
    key = compute_answer_key()
    answers_by_id = {a.get("id"): a.get("answer") for a in submission_json.get("answers", [])}

    breakdown: Dict[str, Any] = {}
    total_max = 0.0
    total_earned = 0.0

    # Q1 - 3 fields, 1 point each
    got1 = answers_by_id.get("Q1", {}) or {}
    e, mx, det = _grade_multi_fields(
        key["Q1"], got1, [("heavy_atoms", 1), ("total_atoms_with_H", 1), ("rotatable_bonds", 1)]
    )
    breakdown["Q1"] = {"earned": e, "max": mx, "detail": det}
    total_earned += e
    total_max += mx

    # Q2 - 3 fields
    got = answers_by_id.get("Q2", {}) or {}
    e, mx, det = _grade_multi_fields(
        key["Q2"], got, [("heavy_atoms", 1), ("aromatic_rings", 1), ("rotatable_bonds", 1)]
    )
    breakdown["Q2"] = {"earned": e, "max": mx, "detail": det}
    total_earned += e
    total_max += mx

    # Q3 - 3 fields
    got = answers_by_id.get("Q3", {}) or {}
    e, mx, det = _grade_multi_fields(
        key["Q3"], got, [("heavy_atoms", 1), ("h_bond_donors", 1), ("h_bond_acceptors", 1)]
    )
    breakdown["Q3"] = {"earned": e, "max": mx, "detail": det}
    total_earned += e
    total_max += mx

    # Q4 - 2 points, integer exact
    got = answers_by_id.get("Q4", {}) or {}
    ok = got.get("match_count") == key["Q4"]["match_count"]
    breakdown["Q4"] = {
        "earned": 2.0 if ok else 0.0,
        "max": 2.0,
        "detail": {"expected": key["Q4"]["match_count"], "got": got.get("match_count"), "ok": ok},
    }
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q5 - 3 fields (1 each)
    got = answers_by_id.get("Q5", {}) or {}
    e, mx, det = _grade_multi_fields(
        key["Q5"], got, [("ring_count", 1), ("heavy_atoms", 1), ("molecular_formula", 1)]
    )
    breakdown["Q5"] = {"earned": e, "max": mx, "detail": det}
    total_earned += e
    total_max += mx

    # Q6 - 3 subparts (1 each)
    got = answers_by_id.get("Q6", {}) or {}
    ring_ok = got.get("ring_count") == key["Q6"]["ring_count"]
    reagent_ok, reagent_det = _grade_smiles_in_list(
        key["Q6"]["reagent_canonical_smiles_allowed"], got.get("reagent_smiles")
    )
    fg = (got.get("functional_group") or "").strip().lower()
    fg_ok = fg in key["Q6"]["functional_group_allowed"]
    e = (1.0 if ring_ok else 0.0) + (1.0 if reagent_ok else 0.0) + (1.0 if fg_ok else 0.0)
    breakdown["Q6"] = {
        "earned": e,
        "max": 3.0,
        "detail": {
            "ring_count": {"ok": ring_ok, "expected": key["Q6"]["ring_count"], "got": got.get("ring_count")},
            "reagent": {"ok": reagent_ok, **reagent_det},
            "functional_group": {
                "ok": fg_ok,
                "expected_any_of": key["Q6"]["functional_group_allowed"],
                "got": got.get("functional_group"),
            },
        },
    }
    total_earned += e
    total_max += 3.0

    # Q7
    got = answers_by_id.get("Q7", {}) or {}
    e, mx, det = _grade_multi_fields(
        key["Q7"], got, [("heavy_atoms", 1), ("ring_count", 1), ("unique_carbons", 1)]
    )
    breakdown["Q7"] = {"earned": e, "max": mx, "detail": det}
    total_earned += e
    total_max += mx

    # Q8
    got = answers_by_id.get("Q8", {}) or {}
    e, mx, det = _grade_multi_fields(
        key["Q8"], got, [("heavy_atoms", 1), ("aromatic_rings", 1), ("ring_count", 1)]
    )
    breakdown["Q8"] = {"earned": e, "max": mx, "detail": det}
    total_earned += e
    total_max += mx

    # Q9
    got = answers_by_id.get("Q9", {}) or {}
    heavy_ok = got.get("heavy_atoms") == key["Q9"]["heavy_atoms"]
    sp_ok = got.get("sp_carbons") == key["Q9"]["sp_carbons"]
    taut_ok, taut_det = _grade_smiles_equals(key["Q9"]["tautomer_canon"], got.get("tautomer_smiles"))
    e = (1.0 if heavy_ok else 0.0) + (1.0 if sp_ok else 0.0) + (1.0 if taut_ok else 0.0)
    breakdown["Q9"] = {
        "earned": e,
        "max": 3.0,
        "detail": {
            "heavy_atoms": {"ok": heavy_ok, "expected": key["Q9"]["heavy_atoms"], "got": got.get("heavy_atoms")},
            "sp_carbons": {"ok": sp_ok, "expected": key["Q9"]["sp_carbons"], "got": got.get("sp_carbons")},
            "tautomer": {"ok": taut_ok, **taut_det},
        },
    }
    total_earned += e
    total_max += 3.0

    # Q10
    got = answers_by_id.get("Q10", {}) or {}
    ok, det = _grade_smiles_in_list(key["Q10"]["product_canon_accepted"], got.get("product_smiles"))
    breakdown["Q10"] = {"earned": 2.0 if ok else 0.0, "max": 2.0, "detail": {"ok": ok, **det}}
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q11 products list
    got = answers_by_id.get("Q11", {}) or {}
    ok, det = _grade_sorted_smiles_list(key["Q11"]["products_canon_sorted"], got.get("products"))
    breakdown["Q11"] = {"earned": 2.0 if ok else 0.0, "max": 2.0, "detail": {"ok": ok, **det}}
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q12
    got = answers_by_id.get("Q12", {}) or {}
    ok, det = _grade_sorted_smiles_list(key["Q12"]["products_canon_sorted"], got.get("products"))
    breakdown["Q12"] = {"earned": 2.0 if ok else 0.0, "max": 2.0, "detail": {"ok": ok, **det}}
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q13
    got = answers_by_id.get("Q13", {}) or {}
    ok, det = _grade_smiles_in_list(key["Q13"]["monomer_canon_accepted"], got.get("monomer_smiles"))
    breakdown["Q13"] = {"earned": 2.0 if ok else 0.0, "max": 2.0, "detail": {"ok": ok, **det}}
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q14
    got = answers_by_id.get("Q14", {}) or {}
    mon_ok, mon_det = _grade_smiles_in_list(
        key["Q14"]["monomer_canon_accepted"], got.get("monomer_smiles")
    )
    ar_ok = got.get("aromatic_rings") == key["Q14"]["aromatic_rings"]
    e = (1.5 if mon_ok else 0.0) + (1.5 if ar_ok else 0.0)
    breakdown["Q14"] = {
        "earned": e,
        "max": 3.0,
        "detail": {
            "monomer": {"ok": mon_ok, **mon_det},
            "aromatic_rings": {
                "ok": ar_ok,
                "expected": key["Q14"]["aromatic_rings"],
                "got": got.get("aromatic_rings"),
            },
        },
    }
    total_earned += e
    total_max += 3.0

    # Q15
    got = answers_by_id.get("Q15", {}) or {}
    ok = got.get("match_count") == key["Q15"]["match_count"]
    breakdown["Q15"] = {
        "earned": 2.0 if ok else 0.0,
        "max": 2.0,
        "detail": {"expected": key["Q15"]["match_count"], "got": got.get("match_count"), "ok": ok},
    }
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q16
    got = answers_by_id.get("Q16", {}) or {}
    ok = got.get("match_count") == key["Q16"]["match_count"]
    breakdown["Q16"] = {
        "earned": 2.0 if ok else 0.0,
        "max": 2.0,
        "detail": {"expected": key["Q16"]["match_count"], "got": got.get("match_count"), "ok": ok},
    }
    total_earned += 2.0 if ok else 0.0
    total_max += 2.0

    # Q17-Q19 broken SMILES recovery (2 pts each: 1 fixed, 1 canonical)
    for qid, raw in [("Q17", _Q17_RAW), ("Q18", _Q18_RAW), ("Q19", _Q19_RAW)]:
        got = answers_by_id.get(qid, {}) or {}
        fixed_target = key[qid]["fixed_smiles"]
        canon_target = key[qid]["canonical_smiles"]
        got_fixed = got.get("fixed_smiles")
        got_canon_raw = got.get("canonical_smiles")
        got_fixed_canon = canon_or_none(got_fixed)
        fixed_ok = got_fixed_canon is not None and got_fixed_canon == canon_target
        canon_ok_raw = canon_or_none(got_canon_raw) == canon_target
        e = (1.0 if fixed_ok else 0.0) + (1.0 if canon_ok_raw else 0.0)
        breakdown[qid] = {
            "earned": e,
            "max": 2.0,
            "detail": {
                "fixed_smiles": {"ok": fixed_ok, "got": got_fixed, "expected_canon": canon_target},
                "canonical_smiles": {
                    "ok": canon_ok_raw,
                    "got": got_canon_raw,
                    "expected_canon": canon_target,
                },
            },
        }
        total_earned += e
        total_max += 2.0

    # Q20 - strict constraint-satisfaction validator
    got = answers_by_id.get("Q20", {}) or {}
    ok, report = _validate_q20(got.get("smiles"), key["Q20"]["constraints"])
    checks = report.get("checks", {})
    per_check_detail = {}
    for k, c in checks.items():
        is_ok = bool(c) if k == "parseable" else bool(c and c.get("ok"))
        per_check_detail[k] = {"ok": is_ok, "raw": c}
    breakdown["Q20"] = {
        "earned": 5.0 if ok else 0.0,
        "max": 5.0,
        "detail": {"got_smiles": got.get("smiles"), "all_constraints_ok": ok, "per_check": per_check_detail},
    }
    total_earned += 5.0 if ok else 0.0
    total_max += 5.0

    # Q21-Q24 high-precision constraint validators (strict pass/fail)
    for qid, validator in [("Q21", _validate_q21), ("Q22", _validate_q22), ("Q23", _validate_q23), ("Q24", _validate_q24)]:
        got = answers_by_id.get(qid, {}) or {}
        ok, report = validator(got.get("smiles"))
        breakdown[qid] = {
            "earned": 3.0 if ok else 0.0,
            "max": 3.0,
            "detail": report,
        }
        total_earned += 3.0 if ok else 0.0
        total_max += 3.0

    return {
        "score": round(total_earned, 3),
        "max_points": round(total_max, 3),
        "percent": round(100.0 * total_earned / total_max, 2) if total_max else 0.0,
        "per_question": breakdown,
    }


if __name__ == "__main__":
    import sys

    sub = json.loads(sys.stdin.read())
    out = grade(sub)
    print(json.dumps(out, indent=2, default=str))
