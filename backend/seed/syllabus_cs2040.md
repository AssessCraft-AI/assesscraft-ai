# CS2040: Database Systems — Course Syllabus

**Academic Unit:** School of Computing, AssessCraft University  
**Module Code:** CS2040  
**Modular Credits:** 4 MCs  
**Prerequisites:** CS1010 Programming Methodology, CS1231 Discrete Structures  

## 1. Course Description
CS2040 introduces the fundamental concepts of relational database management systems (RDBMS). The course focuses on conceptual data modeling using the Entity-Relationship (ER) model, relational algebra, SQL DDL/DML, functional dependencies, schema decomposition and normalization (up to BCNF and 3NF), physical storage and B+ tree indexing, transaction management (ACID properties), concurrency control anomalies, serializability, and write-ahead logging (WAL) crash recovery.

## 2. Course Learning Outcomes (CLOs)
- **CLO1 [Create]:** Design relational database schemas from conceptual enterprise specifications using Entity-Relationship diagrams and functional dependencies.
- **CLO2 [Apply]:** Formulate declarative SQL queries involving multi-table joins (inner, outer, self-joins), nested subqueries, grouping aggregations, and window functions.
- **CLO3 [Analyse]:** Analyze transaction isolation levels, concurrency anomalies (dirty reads, non-repeatable reads, phantom rows), and conflict serializability schedules under two-phase locking (2PL).
- **CLO4 [Evaluate]:** Evaluate B+ tree indexing strategies, index scan costs, and query execution plans for database performance tuning.
- **CLO5 [Apply]:** Decompose and normalize relational tables to Boyce-Codd Normal Form (BCNF) and Third Normal Form (3NF) to eliminate insertion, deletion, and update anomalies.

## 3. Weekly Curricular Topics
1. **Week 1-2:** Entity-Relationship (ER) Modeling, Weak Entities, Cardinality Constraints, and Generalization Hierarchies.
2. **Week 3:** Relational Model, Relational Algebra (Selection, Projection, Join, Division), and Integrity Constraints.
3. **Week 4-5:** SQL Fundamentals, Multi-table Joins (INNER, LEFT OUTER, RIGHT OUTER, FULL OUTER), and Set Operations.
4. **Week 6:** Nested Subqueries (IN, EXISTS, ALL, ANY), Correlated Subqueries, and Grouping with Aggregations.
5. **Week 7-8:** Functional Dependencies, Attribute Closure, Minimal Cover, Lossless Join Decomposition, and Normalization (1NF, 2NF, 3NF, BCNF).
6. **Week 9:** Physical Storage, Heap Files, Clustered vs. Unclustered Indexing, and B+ Tree Search/Insert Algorithms.
7. **Week 10-11:** Transactions, ACID Guarantees, Conflict and View Serializability, Two-Phase Locking (2PL), and Strict 2PL.
8. **Week 12:** Database Recovery, Write-Ahead Logging (WAL), Checkpointing, and ARIES Recovery Algorithm.

## 4. Assessment Scheme
- Continuous Assessment (Assignments & Midterm): 40%
- Final Examination (2 Hours, 100 Marks): 60%
  - Multiple Choice Questions (MCQ): 40 Marks (20 questions × 2 marks)
  - Structured Short Answer Questions: 60 Marks (10 questions × 6 marks)
