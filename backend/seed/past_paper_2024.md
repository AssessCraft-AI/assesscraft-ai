# CS2040 Database Systems — Final Examination (2024)

**Time Allowed:** 2 Hours | **Total Marks:** 100

### Section A: Multiple Choice Questions (30 Marks — 15 Questions)

**Q1 [CLO1 / Understand]:** In an ER diagram, how is a multivalued attribute represented?
- (A) Rectangle
- (B) Double ellipse (double oval)
- (C) Dashed ellipse
- (D) Diamond
*Answer:* (B) | *Rationale:* A double ellipse denotes an attribute that can hold multiple values for a single entity instance.

**Q2 [CLO1 / Apply]:** When converting an M:N relationship set R between entities E1 and E2 into relational tables, what is the primary key of the resulting relation table for R?
- (A) The primary key of E1 only
- (B) The primary key of E2 only
- (C) The combination of primary keys of E1 and E2
- (D) A newly generated artificial surrogate key
*Answer:* (C) | *Rationale:* An M:N relationship table requires the composite primary key consisting of the primary keys of both participating entity sets.

**Q3 [CLO5 / Apply]:** Consider relation R(Course, Room, Teacher) with FDs {Course -> Teacher, Teacher -> Room}. In what normal form is R?
- (A) 1NF
- (B) 2NF
- (C) 3NF
- (D) BCNF
*Answer:* (B) | *Rationale:* Course is candidate key. Transitive dependency Course -> Teacher -> Room violates 3NF, but since all attributes are fully dependent on the primary key, it satisfies 2NF.

**Q4 [CLO5 / Apply]:** To decompose the relation R(A, B, C) with FD {A -> B} into BCNF, which set of relations is appropriate?
- (A) R1(A, B), R2(B, C)
- (B) R1(A, B), R2(A, C)
- (C) R1(A, C), R2(B, C)
- (D) R1(A, B, C)
*Answer:* (B) | *Rationale:* Decomposing into R1(A, B) and R2(A, C) is a lossless join decomposition preserving A as key of R1 and FK in R2.

**Q5 [CLO2 / Understand]:** What does the relational algebra expression $\pi_{\text{name}}(\sigma_{\text{age} > 21}(\text{Students}))$ do?
- (A) Selects ages of students named 21
- (B) Selects names of students whose age is strictly greater than 21
- (C) Projects all attributes for students over 21
- (D) Performs a cartesian product between age and name
*Answer:* (B) | *Rationale:* $\sigma$ filters rows where age > 21, and $\pi$ projects the name attribute.

**Q6 [CLO2 / Apply]:** Which SQL clause must precede `HAVING` in a valid query structure?
- (A) ORDER BY
- (B) GROUP BY
- (C) LIMIT
- (D) UNION
*Answer:* (B) | *Rationale:* `HAVING` filters aggregated row groups established by `GROUP BY`.

**Q7 [CLO2 / Apply]:** Consider the relations Students(id, name) and Enrollments(s_id, course_id). Which SQL query preserves all students regardless of whether they are enrolled in any course?
- (A) SELECT * FROM Students INNER JOIN Enrollments ON Students.id = Enrollments.s_id;
- (B) SELECT * FROM Students LEFT OUTER JOIN Enrollments ON Students.id = Enrollments.s_id;
- (C) SELECT * FROM Students RIGHT OUTER JOIN Enrollments ON Students.id = Enrollments.s_id;
- (D) SELECT * FROM Students CROSS JOIN Enrollments;
*Answer:* (B) | *Rationale:* LEFT OUTER JOIN preserves all tuples from the left relation (Students) even if there is no matching record in Enrollments, filling missing enrollment columns with NULL.

**Q8 [CLO3 / Understand]:** What occurs during a "dirty read" anomaly?
- (A) Transaction T1 reads data modified by uncommitted transaction T2
- (B) Two transactions write to the same row simultaneously
- (C) A committed transaction cannot read its own previous writes
- (D) A transaction reads different versions of a row after another transaction commits
*Answer:* (A) | *Rationale:* A dirty read occurs when uncommitted modifications are read by an external transaction.

**Q9 [CLO3 / Analyse]:** Under Strict Two-Phase Locking (Strict 2PL), when are exclusive locks released?
- (A) Immediately after the data item is modified
- (B) At the end of the transaction upon commit or abort
- (C) As soon as the shrinking phase begins
- (D) When another transaction requests a shared lock
*Answer:* (B) | *Rationale:* Strict 2PL holds all exclusive (X) locks until the transaction terminates (commit/abort), avoiding cascading rollbacks.

**Q10 [CLO3 / Analyse]:** If a serialization precedence graph has a cycle between transactions T1 and T2, what is true?
- (A) The schedule is conflict serializable
- (B) The schedule is not conflict serializable
- (C) The schedule cannot be recovered
- (D) The schedule guarantees strict isolation
*Answer:* (B) | *Rationale:* A directed cycle in the precedence graph implies non-serializable conflicting operations.

**Q11 [CLO4 / Understand]:** Why are B+ tree leaf nodes linked together using pointers?
- (A) To permit fast binary search
- (B) To enable sequential and range scans without traversing internal nodes
- (C) To handle variable length keys
- (D) To conserve disk space
*Answer:* (B) | *Rationale:* Doubly linked leaf nodes allow $O(\text{pages})$ sequential traversal for range queries.

**Q12 [CLO4 / Apply]:** Suppose a B+ tree node can store up to 100 keys. If an existing leaf node contains 100 keys and a new key is inserted, what occurs?
- (A) An overflow page is appended
- (B) The node splits into two nodes of approximately 50 keys each, and a parent key is inserted
- (C) The least recently used key is discarded
- (D) The transaction is aborted with key collision
*Answer:* (B) | *Rationale:* B+ tree leaf node overflow triggers node splitting and elevation of a search key to the parent index node.

**Q13 [CLO4 / Evaluate]:** Under which query condition is a composite B+ tree index on `(department_id, hire_date)` ineffective?
- (A) WHERE department_id = 10 AND hire_date > '2020-01-01'
- (B) WHERE department_id = 10
- (C) WHERE hire_date > '2020-01-01'
- (D) WHERE department_id = 10 ORDER BY hire_date
*Answer:* (C) | *Rationale:* A composite index on `(A, B)` requires the leading key `A` in the predicate to perform an index seek; filtering exclusively on `B` requires a full index scan.

**Q14 [CLO5 / Understand]:** What is the main problem that database normalization solves?
- (A) Slow network communication
- (B) Data redundancy and insertion/deletion/update anomalies
- (C) Lack of index fan-out
- (D) Disk fragmentation
*Answer:* (B) | *Rationale:* Normalization decomposes schemas to eliminate redundancy and anomaly hazards.

**Q15 [CLO3 / Remember]:** Which isolation level guarantees complete absence of dirty reads, non-repeatable reads, and phantom reads?
- (A) Read Uncommitted
- (B) Read Committed
- (C) Repeatable Read
- (D) Serializable
*Answer:* (D) | *Rationale:* Serializable is the highest standard ANSI isolation level, prohibiting all three phenomena.
