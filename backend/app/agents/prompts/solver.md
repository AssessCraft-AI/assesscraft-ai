# Multi-Version Paper Assembly Solver Documentation (v1.0)

## Problem Formulation & Constraints
Parallel university examinations (Main Exam Version A, Repeat Exam Version B, Morning/Afternoon sessions) must guarantee mathematical parity while maintaining strict security and academic integrity.

## Strict Optimization Constraints
1. **Zero Item Overlap ($\sum_v x_{i,v} \le 1$)**:
   - No item may appear in more than one version.
   - Strictly enforced as a hard Boolean constraint in Google OR-Tools CP-SAT.
2. **Deterministic Blueprint Parity**:
   - Every version $v$ must satisfy identical Course Learning Outcome (CLO) mark totals.
   - Exact Bloom taxonomy distribution (identical counts for remember, understand, apply, analyse, evaluate, create).
   - Exact question format split (e.g., 20 MCQs $\times$ 2 marks = 40 marks, 10 Short Answer $\times$ 6 marks = 60 marks).
3. **Exact Total Marks ($\sum_i marks_i \cdot x_{i,v} = targetMarks$)**:
   - Every version must sum to exactly target marks (e.g. 100 marks).
4. **Flaw & Flag Exclusion**:
   - Any candidate item marked `status == "rejected"` or flagged with an unresolved high-severity flag (`key_mismatch`, `duplicate_past`) is strictly excluded ($x_{i,v} = 0$).

## Objective Function: Difficulty Balance
$$\min \left( \max_{v_1, v_2} \left| D_{v_1} - D_{v_2} \right| \right)$$
Where $D_v = \sum_i \text{difficulty}_i \cdot x_{i,v}$ scaled to integer domain. Minimizing the inter-version difficulty gap ensures parallel cohorts face comparable cognitive challenges.

## Academic Equivalence Bounds
- **Guaranteed Structural Equivalence**: Exact blueprint, marks, cognitive demand, and question format matching.
- **Estimated Empirical Equivalence**: Difficulty balance within $\pm 0.15$ on a 1–5 scale.
- **Limitation Notice**: Structural parity does not prove empirical parity; final calibration requires post-exam Item Response Theory (IRT) student response data.
