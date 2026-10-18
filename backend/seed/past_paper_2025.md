# CS2040 Database Systems — Final Examination (2025)

**Time Allowed:** 2 Hours | **Total Marks:** 100

### Section A: Multiple Choice Questions (30 Marks — 15 Questions)

**Q1 [CLO1 / Understand]:** In the Extended Entity-Relationship (EER) model, what does an "overlapping" constraint on a specialization hierarchy denote?
- (A) An entity instance can belong to multiple specialized subclasses simultaneously
- (B) An entity instance must belong to exactly one subclass
- (C) Subclasses cannot contain foreign keys
- (D) The superclass has no primary key
*Answer:* (A) | *Rationale:* Overlapping allows entity membership in more than one subclass; disjoint restricts it to at most one.

**Q2 [CLO1 / Apply]:** In relational mapping, what is the best strategy for a 1:1 relationship between Employee and Department where participation is mandatory for Department but optional for Employee?
- (A) Place the Department primary key as a foreign key in Employee
- (B) Place the Employee primary key as a foreign key in Department with a NOT NULL constraint
- (C) Create a separate junction table with composite keys
- (D) Combine both entities into a single universal table
*Answer:* (B) | *Rationale:* Placing Employee ID in Department avoids NULL values because every department must have an employee.

**Q3 [CLO5 / Apply]:** Relation R(A, B, C, D) has FDs {AB -> C, C -> D, D -> A}. What are all candidate keys?
- (A) AB only
- (B) AB, BC, and BD
- (C) C and D
- (D) A, B, C, D
*Answer:* (B) | *Rationale:* {AB}+ = ABCD. Since D -> A, {BD}+ = BCDA. Since C -> D, {BC}+ = BCDA. Thus AB, BC, BD are candidate keys.

**Q4 [CLO5 / Evaluate]:** What distinguishes Boyce-Codd Normal Form (BCNF) from Third Normal Form (3NF)?
- (A) 3NF permits non-prime attributes to determine superkeys
- (B) In 3NF, the dependency X -> Y is allowed if Y is a prime attribute, even if X is not a superkey
- (C) BCNF does not require 1NF
- (D) 3NF guarantees zero data redundancy
*Answer:* (B) | *Rationale:* 3NF relaxes BCNF by allowing X -> Y if Y is prime (part of a candidate key).

**Q5 [CLO2 / Apply]:** Which SQL query retrieves the second highest employee salary?
- (A) SELECT MAX(salary) FROM Employees;
- (B) SELECT MAX(salary) FROM Employees WHERE salary < (SELECT MAX(salary) FROM Employees);
- (C) SELECT salary FROM Employees ORDER BY salary DESC LIMIT 2;
- (D) SELECT salary FROM Employees WHERE salary = SECOND(MAX(salary));
*Answer:* (B) | *Rationale:* The subquery finds the maximum salary; the outer query finds the maximum salary strictly less than that value.

**Q6 [CLO2 / Apply]:** Given table Orders(id, customer_id, amount), what does `SELECT customer_id, SUM(amount) FROM Orders GROUP BY customer_id HAVING COUNT(*) >= 3;` return?
- (A) All customers with order amounts over $3
- (B) Customers who placed at least 3 orders, alongside their total order amount
- (C) Total order amounts for the first 3 customers
- (D) An error because COUNT(*) cannot be used in HAVING
*Answer:* (B) | *Rationale:* Groups by customer and filters out customers with fewer than 3 orders.

**Q7 [CLO2 / Understand]:** What happens when an `INNER JOIN` is performed between two relations where the join condition matches zero rows for a given tuple?
- (A) The tuple is output with NULL attributes
- (B) The tuple is omitted from the result set
- (C) An exception is raised by the SQL engine
- (D) The Cartesian product is substituted
*Answer:* (B) | *Rationale:* INNER JOIN requires the join predicate to evaluate to TRUE; unmatched rows are discarded.

**Q8 [CLO3 / Understand]:** Which ACID property prevents uncommitted transaction updates from being overwritten by another concurrent transaction?
- (A) Atomicity
- (B) Consistency
- (C) Isolation
- (D) Durability
*Answer:* (C) | *Rationale:* Isolation prevents lost updates and concurrent write-write overwrites.

**Q9 [CLO3 / Analyse]:** Consider transactions T1 and T2: T1: R(A), W(A); T2: R(A), W(A). In what order must operations execute for the schedule to be conflict equivalent to serial schedule <T1, T2>?
- (A) All conflicting operations of T1 on A must precede the conflicting operations of T2 on A
- (B) T2 must read A before T1 writes A
- (C) Conflicting operations may interleave arbitrarily
- (D) T1 and T2 must hold shared locks simultaneously
*Answer:* (A) | *Rationale:* In conflict equivalence, the relative order of any two conflicting operations must match the target serial order.

**Q10 [CLO3 / Analyse]:** What type of deadlock detection algorithm is standard in RDBMS concurrency managers?
- (A) Timestamp ordering
- (B) Wait-For Graph cycle detection
- (C) Precedence graph validation
- (D) Strict Two-Phase Commit
*Answer:* (B) | *Rationale:* A cycle in the dynamic Wait-For Graph indicates a mutual deadlock condition.

**Q11 [CLO4 / Understand]:** In a clustered B+ tree index, how are data rows organized physically on disk?
- (A) In arbitrary order in a heap file
- (B) Sorted sequentially according to the search key of the clustered index
- (C) Grouped randomly into hash buckets
- (D) Stored exclusively in system RAM
*Answer:* (B) | *Rationale:* Clustered indexes define the physical sequential storage order of table rows on storage.

**Q12 [CLO4 / Apply]:** How many page transfers are required to insert a key into a B+ tree of height 3 when no node splitting occurs?
- (A) 1 read, 1 write
- (B) 3 reads, 1 write
- (C) 3 reads, 3 writes
- (D) 6 reads, 0 writes
*Answer:* (B) | *Rationale:* 3 page reads to traverse from root to leaf, plus 1 page write to persist the modified leaf block.

**Q13 [CLO4 / Evaluate]:** What is the primary performance benefit of an "index-only scan" (covering index)?
- (A) It eliminates table row locking
- (B) The query can be satisfied entirely from the index leaf pages without fetching base heap pages
- (C) It bypasses the buffer pool
- (D) It compresses disk pages
*Answer:* (B) | *Rationale:* If all columns requested in SELECT and WHERE are in the index key/included attributes, heap page I/O is completely avoided.

**Q14 [CLO5 / Apply]:** If a table has candidate key {A} and attributes {A, B, C}, with FD {B -> C}, which normal form does it violate?
- (A) 1NF
- (B) 2NF
- (C) 3NF
- (D) 4NF
*Answer:* (C) | *Rationale:* B is not a superkey and C is not prime, so B -> C is a transitive dependency violating 3NF.

**Q15 [CLO3 / Remember]:** In write-ahead logging (WAL), when must a log record for a database update be flushed to non-volatile storage?
- (A) After the corresponding data page is flushed to disk
- (B) Strictly before the corresponding modified data page is written to disk
- (C) Only when the database server shuts down
- (D) Once every 60 seconds
*Answer:* (B) | *Rationale:* The fundamental WAL invariant states that the undo log record must hit disk before the dirty database page is written.
