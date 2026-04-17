# Answer Key

Generated for benchmark version `1.1.0`.

## Long Chains

### Q1

```json
{
  "heavy_atoms": 168,
  "total_atoms_with_H": 394,
  "rotatable_bonds": 165
}
```

### Q2

```json
{
  "heavy_atoms": 56,
  "aromatic_rings": 7,
  "rotatable_bonds": 19
}
```

### Q3

```json
{
  "heavy_atoms": 40,
  "h_bond_donors": 20,
  "h_bond_acceptors": 20
}
```

### Q4

```json
{
  "match_count": 2
}
```

## Ring Systems

### Q5

```json
{
  "ring_count": 7,
  "heavy_atoms": 24,
  "molecular_formula": "C24H12"
}
```

### Q6

```json
{
  "ring_count": 2,
  "reagent_smiles": "OCCO",
  "functional_group": "ketal"
}
```

### Q7

```json
{
  "heavy_atoms": 8,
  "ring_count": 6,
  "unique_carbons": 1
}
```

### Q8

```json
{
  "heavy_atoms": 22,
  "aromatic_rings": 4,
  "ring_count": 5
}
```

### Q9

```json
{
  "heavy_atoms": 17,
  "sp_carbons": 2,
  "tautomer_smiles": "O=C(CCC)c1ccc(-c2ccc(O)cc2)cc1"
}
```

## Reactions

### Q10

```json
{
  "product_smiles": "CCc1ccccc1"
}
```

### Q11

```json
{
  "products": [
    "CCOC(C)=O",
    "O"
  ]
}
```

### Q12

```json
{
  "products": [
    "CCCCN",
    "[Cl-]"
  ]
}
```

## Polymers

### Q13

```json
{
  "monomer_smiles": "COC(=O)C(=C)C"
}
```

### Q14

```json
{
  "monomer_smiles": "C=Cc1ccncc1",
  "aromatic_rings": 4
}
```

## SMARTS

### Q15

```json
{
  "match_count": 2
}
```

### Q16

```json
{
  "match_count": 4
}
```

## SMILES Fix

### Q17

```json
{
  "fixed_smiles": "CCOC(=O)c1ccccc1",
  "canonical_smiles": "CCOC(=O)c1ccccc1"
}
```

### Q18

```json
{
  "fixed_smiles": "CCCCCCCCCCCC",
  "canonical_smiles": "CCCCCCCCCCCC"
}
```

### Q19

```json
{
  "fixed_smiles": "CC(=O)N",
  "canonical_smiles": "CC(=O)N"
}
```

## Design

### Q20

```json
{
  "smiles": "CCCCCCCCCCCc1cccc(Cc2ccccc2Cc3ccccc3Cc4ccncc4Cc5ccoc5Cc6ccsc6)c1"
}
```

## Constraints

### Q21

```json
{
  "smiles": "c1ccc2c(c1)c3ccc(cc3c2S)Nc4ccc(cc4)O"
}
```

### Q22

```json
{
  "smiles": "c1ccc2c(c1)c3ccc(cc3c2S)Nc4ccc(cc4Nc5ccc(cc5)O)O"
}
```

### Q23

```json
{
  "smiles": "c1ccc2c(c1)c3ccc(cc3c2N)Nc4ccc(cc4)O"
}
```

### Q24

```json
{
  "smiles": "c1ccc2c(c1)c3ccc(cc3c2N)O"
}
```

## Diagnostic

### Q-C1

```json
{
  "prompt_summary": "IHD vs ring-budget contradiction",
  "public_reference_answer": {
    "smiles": "c1ccc(cc1)C2CCC(NC(=O)c3ccccc3)CC2O"
  },
  "status": "unscored diagnostic"
}
```

### Q-C2

```json
{
  "prompt_summary": "fully aromatic ring with explicit stereocenter but no sp3 atoms",
  "public_reference_answer": {
    "smiles": "c1cc[nH]c(c1)[C@H](C)C"
  },
  "status": "unscored diagnostic"
}
```

### Q-C3

```json
{
  "prompt_summary": "quaternary ammonium required to be neutral without a countercharge",
  "public_reference_answer": {
    "smiles": "C[N+](C)(C)CCO"
  },
  "status": "unscored diagnostic"
}
```

### Q-C5

```json
{
  "prompt_summary": "heteroatom element count conflicts with stated N/O/S totals",
  "public_reference_answer": {
    "smiles": "c1nc(=O)sc(c1)N"
  },
  "status": "unscored diagnostic"
}
```

### Q-C8

```json
{
  "prompt_summary": "formula and ring topology contradict the stated unsaturation budget",
  "public_reference_answer": {
    "smiles": "c1ccc(cc1)C2CCC(N(C)C)CC2C3CCC(O)CC3O"
  },
  "status": "unscored diagnostic"
}
```

### Q-C10

```json
{
  "prompt_summary": "symmetry reduces the stated stereoisomer count",
  "public_reference_answer": {
    "smiles_list": [
      "OC[C@H]1[C@H](CO)[C@H](CO)[C@H]1CO"
    ]
  },
  "status": "unscored diagnostic"
}
```
