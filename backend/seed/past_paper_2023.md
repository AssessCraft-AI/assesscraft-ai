# CS2040 Database Systems — Final Examination (2023)

**Time Allowed:** 2 Hours | **Total Marks:** 100

### Section A: Multiple Choice Questions (30 Marks — 15 Questions)

**Q1 [CLO1 / Remember]:** Which component of an Entity-Relationship (ER) diagram represents a relationship set that does not possess its own primary key attributes?
- (A) Multivalued attribute
- (B) Weak entity set
- (C) Identifying relationship set
- (D) Recursive relationship
*Answer:* (B) | *Rationale:* Weak entity sets depend on an owner entity set for identification via partial discriminator keys.

**Q2 [CLO1 / Understand]:** In an ER diagram, if an entity in set E must participate in at least one relationship instance in relationship set R, what constraint is this?
- (A) Partial participation
- (B) Total participation
- (C) Cardinality ratio 1:1
- (D) Key constraint
*Answer:* (B) | *Rationale:* Total participation requires every entity instance to participate in the relationship.

**Q3 [CLO5 / Apply]:** Given the relation R(A, B, C, D) with functional dependencies {A -> B, B -> C, C -> D}, what is the candidate key of R?
- (A) A
- (B) AB
- (C) AD
- (D) BCD
*Answer:* (A) | *Rationale:* The attribute closure {A}+ = {A, B, C, D}, making A the minimal superkey.

**Q4 [CLO5 / Apply]:** In the relation R(A, B, C, D) with functional dependencies {A -> B, B -> C, C -> D}, which normal form is violated?
- (A) 1NF
- (B) 2NF
- (C) 3NF
- (D) None, it is in BCNF
*Answer:* (C) | *Rationale:* Transitive dependencies A -> B and B -> C violate 3NF for non-prime attributes.

**Q5 [CLO2 / Understand]:** Which relational algebra operator corresponds to the SQL `UNION` operation?
- (A) Selection
- (B) Projection
- (C) Set union ($\cup$)
- (D) Cartesian product ($\times$)
*Answer:* (C) | *Rationale:* Both input relations must be union-compatible.

**Q6 [CLO2 / Apply]:** Which SQL clause is evaluated after `GROUP BY` to filter aggregated groups?
- (A) WHERE
- (B) HAVING
- (C) ORDER BY
- (D) LIMIT
*Answer:* (B) | *Rationale:* HAVING filters groups formed by GROUP BY.

**Q7 [CLO2 / Apply]:** What is the result of executing `SELECT COUNT(*) FROM Employees WHERE salary = NULL;` in standard SQL?
- (A) The total number of employees
- (B) The number of employees with missing salary
- (C) 0
- (D) A syntax error
*Answer:* (C) | *Rationale:* Three-valued logic: `salary = NULL` evaluates to UNKNOWN for all rows; `IS NULL` must be used instead.

**Q8 [CLO3 / Understand]:** Which ACID property is directly guaranteed by the database write-ahead log (WAL) undo mechanism?
- (A) Consistency
- (B) Atomicity
- (C) Isolation
- (D) Durability
*Answer:* (B) | *Rationale:* Undo logging rolls back uncommitted transactions upon abort or crash, preserving atomicity.

**Q9 [CLO3 / Analyse]:** A schedule contains the sequence: T1 reads X, T2 writes X, T2 commits, T1 reads X. What anomaly does T1 experience?
- (A) Dirty read
- (B) Non-repeatable read
- (C) Phantom read
- (D) Lost update
*Answer:* (B) | *Rationale:* T1 reads X twice within the same transaction and observes different committed values.

**Q10 [CLO3 / Analyse]:** Consider two transactions T1 and T2. Under Two-Phase Locking (2PL), when does a transaction enter its shrinking phase?
- (A) As soon as it commits
- (B) As soon as it releases its first lock
- (C) When all locks are acquired
- (D) When a deadlock is detected
*Answer:* (B) | *Rationale:* The shrinking phase begins upon the first lock release; no subsequent locks may be acquired.

**Q11 [CLO4 / Understand]:** In a B+ tree of order d, where are the actual data records or record pointers stored?
- (A) In the root node only
- (B) In all internal nodes
- (C) Exclusively in leaf nodes
- (D) Evenly distributed across all levels
*Answer:* (C) | *Rationale:* In a B+ tree, internal nodes contain only indexing keys; all data records reside in leaf nodes.

**Q12 [CLO4 / Apply]:** A B+ tree has a height of 3 (root, one internal level, leaf level). What is the maximum number of disk I/Os required for an exact key lookup?
- (A) 1
- (B) 2
- (C) 3
- (D) 4
*Answer:* (C) | *Rationale:* Traversing root -> internal node -> leaf node requires 3 page reads.

**Q13 [CLO4 / Evaluate]:** Why does a database query optimizer avoid an unclustered index scan when query selectivity exceeds 15%?
- (A) The index becomes corrupted
- (B) Each unclustered record retrieval can cause a random disk I/O, costing more than a sequential table scan
- (C) Unclustered indexes cannot handle numerical comparisons
- (D) The leaf nodes cannot be traversed sequentially
*Answer:* (B) | *Rationale:* Random I/O overhead on scattered disk blocks quickly surpasses contiguous block scanning.

**Q14 [CLO5 / Apply]:** A relation R(A, B, C) has functional dependencies {A -> B, B -> A, B -> C}. What are all the candidate keys?
- (A) A only
- (B) B only
- (C) A and B
- (D) AB and BC
*Answer:* (C) | *Rationale:* Both {A}+ = {A, B, C} and {B}+ = {A, B, C} are minimal superkeys.

**Q15 [CLO3 / Remember]:** Which isolation level prevents both dirty reads and non-repeatable reads, but still permits phantom reads?
- (A) Read Uncommitted
- (B) Read Committed
- (C) Repeatable Read
- (D) Serializable
*Answer:* (C) | *Rationale:* Repeatable Read locks individual rows, but does not use predicate/range locks to prevent insertions.
