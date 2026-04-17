# SMILES / SMARTS / SMIRKS LLM Benchmark v1.0.0

Use this prompt to test an LLM **without tool use** (no RDKit, no interpreters, no
web).

## Instructions for the model under test

You are being evaluated on your ability to reason over SMILES, SMARTS, and SMIRKS
**without any external tools**. Produce answers purely from your own inference.

Rules:
0. **No tools.** Do not attempt to call any tool. Keep private reasoning concise so the
   full JSON answer fits in a normal chat completion.
1. Return **JSON only** (no markdown fences, no commentary around the JSON).
2. Return a top-level object with one key: `"answers"`.
3. `"answers"` must be a list of **one object per question** for all scored and
   diagnostic items in this prompt. Each object has:
   - `"id"`: question id
   - `"answer"`: payload described per question
4. **All 30 items must appear** in your answer list.
5. For lists where order is not chemically meaningful, order does not matter unless
   stated otherwise.
6. When a question asks for a SMILES string, return a **valid SMILES** (any
   tautomer/canonicalization of the intended molecule is accepted — matches will be
   made on canonical form).
7. Questions labeled `Diagnostic` are unscored research items. Answer them in the
   same JSON format as the scored items.

Use these controlled labels when a question asks for a stereochemical **relation**:
`"identical"`, `"enantiomers"`, `"diastereomers"`,
`"constitutionally_different"`, `"same_connectivity_one_or_more_undefined_centers"`.

---

## Section A — Long / repetitive structures (tokenizer stress)

### Q1
Consider this SMILES:

`CCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCOCCSCCO`

Return:
1. the total number of **heavy atoms**
2. the total number of **atoms including implicit hydrogens**
3. the number of **rotatable bonds** using the standard Lipinski definition
   (single, non-ring, non-terminal bonds between two heavy atoms, excluding bonds to
   terminal `CH3`/heteroatoms with only one heavy neighbor, and excluding amide C–N
   bonds).

`{"id":"Q1","answer":{"heavy_atoms":0,"total_atoms_with_H":0,"rotatable_bonds":0}}`

### Q2
Consider this SMILES:

`CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)CC(c1ccccc1)`

Return:
1. **heavy-atom count**
2. **number of aromatic rings**
3. **number of rotatable bonds** (Lipinski definition as in Q1)

`{"id":"Q2","answer":{"heavy_atoms":0,"aromatic_rings":0,"rotatable_bonds":0}}`

### Q3
Consider this SMILES:

`NCC(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)C(O)CN`

Return:
1. **heavy-atom count**
2. **total hydrogen-bond donors**
3. **total hydrogen-bond acceptors** (Lipinski definition)

`{"id":"Q3","answer":{"heavy_atoms":0,"h_bond_donors":0,"h_bond_acceptors":0}}`

### Q4
A SMARTS pattern consisting of **ten** consecutive generic carbons is applied to a
straight-chain undecane (11 carbons). The SMARTS is:

`[#6][#6][#6][#6][#6][#6][#6][#6][#6][#6]`

Target SMILES: `CCCCCCCCCCC`

Return the **number of substructure matches** using the standard substructure
search semantics where matches that cover the **same set of atoms** are counted
only once (i.e. the default "unique" match count).

`{"id":"Q4","answer":{"match_count":0}}`

### Q-C1 Diagnostic
Propose one valid SMILES for a neutral connected molecule with:
1. exactly **24 heavy atoms**
2. exactly **3 rings**
3. exactly **two benzene rings**
4. exactly **one additional saturated 6-membered ring**
5. exactly **2 nitrogen atoms** and **2 oxygen atoms**
6. **IHD = 8**
7. **no triple bonds, halogens, or metals**

`{"id":"Q-C1","answer":{"smiles":"..."}}`

---

## Section B — Unusual / complex ring systems

### Q5
Consider this fully aromatic polycyclic SMILES:

`c1cc2ccc3ccc4ccc5ccc6ccc1c1c2c3c4c5c61`

Return:
1. **total ring count** (SSSR)
2. **heavy-atom count**
3. **molecular formula** as a string

`{"id":"Q5","answer":{"ring_count":0,"heavy_atoms":0,"molecular_formula":"..."}}`

### Q6
Consider this compound:

`O=C1CCC2(CC1)OCCO2`

Return:
1. **ring count**
2. a **SMILES for one reagent** that could convert the corresponding unprotected
   parent ketone (before ketal protection) into this product in a single step
3. the **canonical functional group** installed, identified by a single short
   chemistry term (e.g. `ester`, `amide`, `ketal`, `hemiacetal`, `acetal`,
   `lactone`, `orthoester`, `aminal`, `imine`, `enol ether`). Use exactly one of
   those tokens.

`{"id":"Q6","answer":{"ring_count":0,"reagent_smiles":"...","functional_group":"..."}}`

### Q7
Consider this cubic hydrocarbon SMILES:

`C12C3C4C1C5C2C3C45`

Return:
1. **heavy-atom count**
2. **ring count** (SSSR)
3. **number of unique carbon atoms** (count of topologically distinct carbon atoms in the idealized structure).

`{"id":"Q7","answer":{"heavy_atoms":0,"ring_count":0,"unique_carbons":0}}`

### Q8
Consider this SMILES:

`C12c3ccccc3C(c3cccnc31)c1ccccc12`

Return:
1. **heavy-atom count**
2. **number of aromatic rings**
3. **total ring count** (SSSR)

`{"id":"Q8","answer":{"heavy_atoms":0,"aromatic_rings":0,"ring_count":0}}`

### Q-C2 Diagnostic
Propose one valid SMILES for a neutral connected molecule with:
1. exactly **12 heavy atoms**
2. exactly **1 fully aromatic ring**
3. exactly **1 nitrogen atom**
4. exactly **1 explicitly specified stereocenter**
5. **no sp3 atoms**

`{"id":"Q-C2","answer":{"smiles":"..."}}`

### Q9
Consider this SMILES:

`CCCC#Cc1ccc(-c2ccc(O)cc2)cc1`

Return:
1. the **heavy-atom count**
2. the **number of sp-hybridized carbons**
3. a **SMILES for the corresponding ketone tautomer** (convert the central alkyne carbons to a carbonyl C=O on the side where the OH was, keeping the biphenyl skeleton unchanged). Answer with a valid SMILES.

`{"id":"Q9","answer":{"heavy_atoms":0,"sp_carbons":0,"tautomer_smiles":"..."}}`

---

## Section C — Reactions / transforms (SMIRKS)

### Q10
SMIRKS (literal transform):

`[C:1]=[C:2].[H][H:3]>>[C:1]([H:3])[C:2][H]`

Reactants:
- `C=Cc1ccccc1`
- `[H][H]`

Return the **canonical SMILES of the product** (single molecule).

`{"id":"Q10","answer":{"product_smiles":"..."}}`

### Q11
SMIRKS:

`[C:1](=[O:2])[OH:3].[OH:4][C:5]>>[C:1](=[O:2])[O:4][C:5].[H]O[H]`

Reactants:
- `CC(=O)O`
- `OCC`

Return the **list of canonical SMILES** for the **product fragments** (esterification
plus water).

`{"id":"Q11","answer":{"products":["...","..."]}}`

### Q12
SMIRKS:

`[C:1][Cl:2].[NH3:3]>>[C:1][NH2:3].[Cl-:2]`

Reactants:
- `CCCCCl`
- `N`

Return the **list of canonical SMILES** for the product fragments.

`{"id":"Q12","answer":{"products":["...","..."]}}`

### Q-C3 Diagnostic
Propose one valid SMILES for a connected molecule with:
1. exactly **10 heavy atoms**
2. one quaternary nitrogen written as `[N+]`
3. **no negatively charged atoms**
4. overall molecule is **neutral**

`{"id":"Q-C3","answer":{"smiles":"..."}}`

---

## Section D — Polymers / retrosynthesis (monomer ID)

### Q13
Below is a short stretch of a homopolymer's backbone (trailing dangling bonds not
drawn):

`CC(C)(C(=O)OC)CC(C)(C(=O)OC)CC(C)(C(=O)OC)CC(C)(C(=O)OC)`

Return the **SMILES of the monomer** that would produce this polymer by
radical addition polymerization (single vinyl monomer).

`{"id":"Q13","answer":{"monomer_smiles":"..."}}`

### Q14
Poly(4-vinylpyridine) oligomer segment (trailing dangling bonds not drawn):

`CC(c1ccncc1)CC(c1ccncc1)CC(c1ccncc1)CC(c1ccncc1)`

Return:
1. the **SMILES of the single vinyl monomer** that would produce this polymer by
   radical addition polymerization
2. the **number of aromatic rings** in the shown oligomer

`{"id":"Q14","answer":{"monomer_smiles":"...","aromatic_rings":0}}`

---

## Section E — SMARTS matching on complex targets

### Q15
SMARTS:

`[c;$(c1ccccc1)][CX3](=[OX1])[OX2][c;$(c1ccccc1)]`

Target SMILES:

`O=C(Oc1ccc(Cl)cc1)Oc1ccc([N+](=O)[O-])cc1`

Return the **number of distinct substructure matches** (each mapping counted once).

`{"id":"Q15","answer":{"match_count":0}}`

### Q16
SMARTS:

`[CX4H0]([#6])([#6])([#6])([#6])`

Target SMILES:

`CC(C)(C)C(C)(C)C(C)(C)C(C)(C)C`

Return the **number of substructure matches** using the standard substructure
search semantics where matches that cover the **same set of atoms** are counted
only once (i.e. the default "unique" match count).

`{"id":"Q16","answer":{"match_count":0}}`

### Q-C5 Diagnostic
Propose one valid SMILES for a neutral connected molecule with:
1. exactly **20 heavy atoms**
2. heteroatoms drawn from **exactly two heteroatom elements**
3. heteroatom counts **N = 2, O = 2, S = 1**

`{"id":"Q-C5","answer":{"smiles":"..."}}`

---

## Section F — SMILES string handling

For each input below, return:
1. the **corrected SMILES** (remove any whitespace characters)
2. the **canonical SMILES** of that molecule as you would write it

For Q17–Q19, input is provided on a single line between `<<<` and `>>>`; everything
between those delimiters is literally part of the SMILES, including any whitespace.

### Q17
Input: `<<<CCOC(=O) c1cc ccc1>>>`

`{"id":"Q17","answer":{"fixed_smiles":"...","canonical_smiles":"..."}}`

### Q18
Input: `<<<CCCCCC	CCCCCC>>>` (there is a single literal TAB between the two
`CCCCCC` halves)

`{"id":"Q18","answer":{"fixed_smiles":"...","canonical_smiles":"..."}}`

### Q19
Input (a single literal newline appears between `CC(=` and `O)N`):

```
<<<CC(=
O)N>>>
```

`{"id":"Q19","answer":{"fixed_smiles":"...","canonical_smiles":"..."}}`

---

## Section G — Open-ended design

### Q20
Propose a **single valid SMILES** for a molecule that satisfies **all** of the
following constraints simultaneously:

1. exactly **50 heavy atoms**
2. exactly **6 rings** (SSSR count)
3. contains **atoms of exactly three different heteroatom elements** (e.g. N, O,
   and S; no other heteroatoms present). Halogens do not count as heteroatoms for
   this question; they must not appear at all.
4. **no single ring** contains **more than one type of heteroatom** (rings may
   contain zero heteroatoms, or all heteroatoms within one ring must be the same
   element)
5. is a **single connected molecule** (no `.` disconnects)
6. is **neutral** (total formal charge = 0)

Return exactly one SMILES string.

`{"id":"Q20","answer":{"smiles":"..."}}`

### Q-C8 Diagnostic
Propose one valid SMILES for a neutral connected molecule with:
1. molecular formula **C18H30N2O2**
2. exactly **4 rings**
3. exactly **one benzene ring**
4. all remaining rings fully saturated
5. exactly **two tertiary amines**
6. exactly **two alcohols**
7. **no double bonds outside benzene**

`{"id":"Q-C8","answer":{"smiles":"..."}}`

---

## Section H — High-precision constraint satisfaction (hardest)

### Q21
Propose a **single valid SMILES** for a molecule that satisfies **all** of the
following constraints simultaneously:

1. exactly **34 heavy atoms**
2. exactly **7 rings** by SSSR
3. ring sizes are exactly **five 6-membered rings and two 5-membered rings**
4. exactly **34 aromatic atoms**
5. contains atoms of exactly three heteroatom elements: **N, O, and S**
6. heteroatom counts are exactly **N = 3, O = 1, S = 1**
7. exactly **3 fused ring pairs**
8. exactly **6 atoms belong to two rings each**
9. is a single connected neutral molecule
10. contains **no halogens, no isotopes, no charges, and no disconnected components**

Return exactly one SMILES string.

`{"id":"Q21","answer":{"smiles":"..."}}`

### Q22
Propose a **single valid SMILES** for a molecule that satisfies **all** of the
following constraints simultaneously:

1. exactly **34 heavy atoms**
2. exactly **7 rings** by SSSR
3. ring sizes are exactly **five 6-membered rings and two 5-membered rings**
4. exactly **34 aromatic atoms**
5. contains atoms of exactly three heteroatom elements: **N, O, and S**
6. heteroatom counts are exactly **N = 4, O = 1, S = 1**
7. exactly **6 H-bond acceptors**
8. exactly **0 H-bond donors**
9. exactly **3 fused ring pairs**
10. exactly **3 rotatable bonds**
11. is a single connected neutral molecule
12. contains **no halogens, no isotopes, and no atom mapping**

Return exactly one SMILES string.

`{"id":"Q22","answer":{"smiles":"..."}}`

### Q23
Propose a **single valid SMILES** for a molecule that satisfies **all** of the
following constraints simultaneously:

1. exactly **28 heavy atoms**
2. exactly **6 rings** by SSSR
3. ring sizes are exactly **four 6-membered rings and two 5-membered rings**
4. exactly **28 aromatic atoms**
5. contains atoms of exactly two heteroatom elements: **N and O** (no S)
6. heteroatom counts are exactly **N = 4, O = 1**
7. exactly **0 H-bond donors**
8. exactly **5 H-bond acceptors**
9. exactly **3 fused ring pairs**
10. exactly **2 rotatable bonds**
11. is a single connected neutral molecule
12. contains **no halogens, no isotopes, and no formal charges**

Return exactly one SMILES string.

`{"id":"Q23","answer":{"smiles":"..."}}`

### Q24
Propose a **single valid SMILES** for a molecule that satisfies **all** of the
following constraints simultaneously:

1. exactly **25 heavy atoms**
2. exactly **5 rings** by SSSR
3. ring sizes are exactly **four 6-membered rings and one 5-membered ring**
4. exactly **25 aromatic atoms**
5. contains atoms of exactly two heteroatom elements: **N and O** (no S)
6. heteroatom counts are exactly **N = 2, O = 1**
7. exactly **0 H-bond donors**
8. exactly **3 H-bond acceptors**
9. exactly **2 fused ring pairs**
10. exactly **2 rotatable bonds**
11. is a single connected neutral molecule
12. contains **no halogens, no isotopes, no charges, and no disconnected components**

Return exactly one SMILES string.

`{"id":"Q24","answer":{"smiles":"..."}}`

### Q-C10 Diagnostic
Consider `1,2,3,4-tetrakis(hydroxymethyl)cyclobutane`.
Assume four tetrahedral stereocenters and list **all 16 stereoisomers** as valid
SMILES.

`{"id":"Q-C10","answer":{"smiles_list":["..."]}}`
