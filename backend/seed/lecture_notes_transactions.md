# CS2040 Lecture Notes: Transactions and Concurrency Control

**Instructor:** Dr. Samantha Chen  
**Topic:** ACID Properties, Serializability, Isolation Levels, and Two-Phase Locking  

## 1. Transaction Concept and ACID Properties
A database transaction is a logical unit of work consisting of one or more SQL operations. To maintain data integrity across failures and concurrent execution, the RDBMS enforces ACID:
1. **Atomicity:** All-or-nothing execution. Guaranteed via write-ahead undo logging.
2. **Consistency:** A transaction transforms the database from one valid state satisfying all declarative constraints to another valid state.
3. **Isolation:** Concurrent transactions execute without interfering with one another. Each transaction behaves as if it runs in isolation.
4. **Durability:** Once committed, changes survive server crashes. Guaranteed via redo logging.

## 2. Concurrency Anomalies
Uncontrolled interleaved execution produces three classic anomalies:
- **Dirty Read (Read Uncommitted):** Transaction T2 reads uncommitted modifications made by T1. If T1 subsequently aborts, T2 operated on invalid phantom data.
- **Non-Repeatable Read (Fuzzy Read):** T1 reads row R, T2 modifies or deletes R and commits, then T1 rereads R and observes changed values.
- **Phantom Read:** T1 executes a predicate query (e.g., `WHERE balance > 1000`), T2 inserts a new row matching that predicate and commits, then T1 re-executes the query and discovers extra rows.

## 3. ANSI SQL Isolation Levels
| Isolation Level | Dirty Read Permitted? | Non-Repeatable Read Permitted? | Phantom Read Permitted? |
| :--- | :--- | :--- | :--- |
| **Read Uncommitted** | Yes | Yes | Yes |
| **Read Committed** | No | Yes | Yes |
| **Repeatable Read** | No | No | Yes |
| **Serializable** | No | No | No |

## 4. Conflict Serializability & Precedence Graphs
Two consecutive actions in a schedule conflict if and only if:
1. They belong to different transactions;
2. They access the same database element;
3. At least one of the actions is a write operation (`W(X)`).

A schedule is conflict serializable if it is conflict equivalent to some serial schedule.
**Precedence Graph (Serialization Graph):**
- Nodes represent committed transactions.
- A directed edge `Ti -> Tj` exists if an action of `Ti` conflicts with and precedes a corresponding action of `Tj`.
- **Theorem:** A schedule S is conflict serializable if and only if its precedence graph contains no directed cycles.

## 5. Two-Phase Locking (2PL)
- **Growing Phase:** A transaction may acquire locks (Shared `S` or Exclusive `X`), but may not release any lock.
- **Shrinking Phase:** A transaction may release locks, but may not acquire any new locks.
- **Strict 2PL:** All exclusive locks held by a transaction are held until the transaction commits or aborts. Strict 2PL guarantees recoverability and avoids cascading aborts.
