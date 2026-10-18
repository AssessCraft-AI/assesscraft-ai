# CS2040 Lecture Notes: B+ Tree Indexing and Query Performance

**Instructor:** Dr. Samantha Chen  
**Topic:** File Organization, B+ Tree Index Architecture, and Search Costs  

## 1. Storage Hierarchy and Access Costs
Data in an RDBMS is organized into pages (typically 4KB to 16KB blocks). I/O cost dominates execution time:
- **Heap File Scan:** Cost of searching for records in an unindexed heap file of $B$ pages is $B$ page transfers (for range queries or unsorted scans).
- **Binary Search on Sorted File:** Cost is $\lceil \log_2 B \rceil$ page transfers. However, maintaining physical sorted order upon insertions is prohibitively expensive ($O(B)$).

## 2. B+ Tree Structure & Invariants
A B+ tree of order $d$ (fan-out $2d$) is a balanced search tree where:
- All data records or record pointers reside exclusively in **leaf pages**.
- Internal nodes contain only routing search keys and child page pointers.
- Every internal node (except the root) has between $d$ and $2d$ keys.
- Leaves are chained in a doubly linked list, enabling efficient range scans ($O(\text{height} + \text{pages\_in\_range})$).
- The height of a B+ tree storing $N$ records with average fan-out $F$ is $h = \lceil \log_F N \rceil$. With fan-out $F \approx 100$, a 3-level tree indexes 1,000,000 pages with only 3 I/O operations.

## 3. Clustered vs. Unclustered Indexes
- **Clustered (Primary) Index:** The physical ordering of rows on disk matches the search key order of the index. A table can have at most **one** clustered index. Range scans on clustered indexes read consecutive contiguous disk blocks.
- **Unclustered (Secondary) Index:** Leaves contain record identifiers (RIDs). Rows on disk are scattered arbitrarily. In the worst case, each matching record retrieved via an unclustered index requires an independent, random disk block I/O.

## 4. Query Optimizer Rules of Thumb
- An unclustered index scan is only advantageous when the query selectivity is high (< 5% to 10% of total table rows).
- Composite indexes `(A, B)` can satisfy queries filtering on `A` or `(A AND B)`, but cannot accelerate filtering exclusively on `B` without a prefix scan.
