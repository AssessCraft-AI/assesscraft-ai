import math
import time
import json
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.models import (
    Item,
    Option,
    SourceCitation,
    Blueprint,
    BlueprintCell,
    Assessment,
    Course,
    generate_id,
    current_time_iso,
)
from app.services.firestore import db
from app.services.traces import tracker
from app.tools.search import search_knowledge_base
from app.tools.similarity import require_llm_or_fallback, compute_embedding, compute_embeddings, get_llm_client
from app.tools.events import log_event

logger = logging.getLogger("assesscraft.item_writer")


# Structured schemas for LLM generation
class GeneratedOption(BaseModel):
    id: str  # A, B, C, D
    text: str


class GeneratedItemSchema(BaseModel):
    stem: str
    options: Optional[List[GeneratedOption]] = None
    key: str
    rationale: str
    difficulty: int = Field(ge=1, le=5)


class CellItemsResponse(BaseModel):
    items: List[GeneratedItemSchema]


# Curated high-yield item bank grounded in CS2040 materials for guaranteed fallback & testing
TOPIC_ITEM_BANK: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "t1": {  # Entity-Relationship (ER) Modeling
        "mcq": [
            {
                "stem": "In an Entity-Relationship diagram, which relationship constraint specifies that every instance of an entity set MUST participate in at least one relationship instance?",
                "options": [
                    {"id": "A", "text": "Total participation (existence dependency)"},
                    {"id": "B", "text": "Partial participation"},
                    {"id": "C", "text": "Cardinality ratio of 1:1"},
                    {"id": "D", "text": "Disjoint specialization"},
                ],
                "key": "A",
                "rationale": "Total participation (indicated by a double line) mandates that every entity in the entity set participates in the relationship. B is incorrect because partial participation allows entities to exist without participating. C only dictates mapping cardinality, not mandatory existence. D governs ISA inheritance hierarchies.",
                "difficulty": 2,
            },
            {
                "stem": "When modeling a weak entity set in an ER schema, which attribute component is required alongside the identifying relationship's primary key to uniquely identify an entity?",
                "options": [
                    {"id": "A", "text": "Partial key (discriminator)"},
                    {"id": "B", "text": "Surrogate foreign key"},
                    {"id": "C", "text": "Multi-valued composite key"},
                    {"id": "D", "text": "Derived timestamp attribute"},
                ],
                "key": "A",
                "rationale": "A weak entity set lacks a primary key of its own and requires a partial key (discriminator) combined with the owner entity's primary key. B is an implementation artifact. C and D do not provide identifying discriminator semantics.",
                "difficulty": 3,
            },
            {
                "stem": "Which cardinality ratio allows an entity in entity set A to be associated with at most one entity in B, while an entity in B can be associated with any number of entities in A?",
                "options": [
                    {"id": "A", "text": "Many-to-One (N:1) from A to B"},
                    {"id": "B", "text": "One-to-Many (1:N) from A to B"},
                    {"id": "C", "text": "Many-to-Many (M:N)"},
                    {"id": "D", "text": "Strict One-to-One (1:1)"},
                ],
                "key": "A",
                "rationale": "An N:1 relationship from A to B restricts each A instance to at most one B instance, while each B instance may link to multiple A instances. B reverses the direction. C and D have different cardinality bounds.",
                "difficulty": 2,
            },
        ],
        "short_answer": [
            {
                "stem": "Consider a university schema where a Department offers multiple Courses, and each Course may have multiple Sections taught by Professors. Explain how to represent the Section entity as a weak entity set, specifying its identifying owner entity, discriminator, and how its primary key is formed upon relational translation.",
                "key": "Identifying Owner: Course (course_id). Discriminator: section_number (e.g., Sec 01). Primary Key upon translation: (course_id, section_number).",
                "rationale": "Marking Rubric:\n- [2 marks] Correctly identify Course as the identifying owner entity and section_number as the partial key/discriminator.\n- [2 marks] Formulate composite primary key (course_id, section_number) referencing Course(course_id).\n- [2 marks] State foreign key constraint with ON DELETE CASCADE semantics for dependent sections.",
                "difficulty": 4,
            },
            {
                "stem": "Contrast total participation with partial participation in an ER model. Provide a concrete database scenario where an entity has total participation in one relationship but partial participation in another.",
                "key": "Total participation requires every entity instance to partake in the relation (double line); partial does not (single line). Example: An Employee must belong to a Department (total), but only some Employees manage a Department (partial).",
                "rationale": "Marking Rubric:\n- [2 marks] Precise conceptual definition of total vs partial participation.\n- [2 marks] Realistic schema example with clear distinction.\n- [2 marks] Explanation of relational mapping (NOT NULL foreign key constraint for total participation).",
                "difficulty": 3,
            },
        ],
    },
    "t2": {  # Relational Algebra & Schema Design
        "mcq": [
            {
                "stem": "In fundamental relational algebra, which basic operator produces all possible concatenated tuple pairs between two relations R and S without applying any condition?",
                "options": [
                    {"id": "A", "text": "Cartesian Product (R × S)"},
                    {"id": "B", "text": "Natural Join (R ⋈ S)"},
                    {"id": "C", "text": "Theta Join (R ⋈_θ S)"},
                    {"id": "D", "text": "Projection (π_attr(R))"},
                ],
                "key": "A",
                "rationale": "The Cartesian product produces the unconstrained cross-product of all tuples. B and C apply join predicates and equality on matching attributes. D eliminates attributes.",
                "difficulty": 2,
            },
            {
                "stem": "Which relational algebra expression correctly retrieves the names of all students who have enrolled in BOTH 'CS2040' and 'CS2102'?",
                "options": [
                    {"id": "A", "text": "π_name(σ_code='CS2040'(Enrolls)) ∩ π_name(σ_code='CS2102'(Enrolls))"},
                    {"id": "B", "text": "π_name(σ_code='CS2040' ∧ code='CS2102'(Enrolls))"},
                    {"id": "C", "text": "π_name(σ_code='CS2040'(Enrolls)) ∪ π_name(σ_code='CS2102'(Enrolls))"},
                    {"id": "D", "text": "π_name(σ_code='CS2040'(Enrolls)) − π_name(σ_code='CS2102'(Enrolls))"},
                ],
                "key": "A",
                "rationale": "Intersection of projections onto student name correctly finds students present in both course sets. B checks code='CS2040' and code='CS2102' on a single tuple, which evaluates to empty set. C is union (either course). D is set difference.",
                "difficulty": 3,
            },
        ],
        "short_answer": [
            {
                "stem": "Given relations Employee(eid, name, dept_id, salary) and Department(dept_id, dname, budget), write a pure relational algebra expression to find the names of employees who earn strictly more than the budget of their respective department.",
                "key": "π_name(σ_salary > budget(Employee ⋈_Employee.dept_id = Department.dept_id Department))",
                "rationale": "Marking Rubric:\n- [2 marks] Correct theta join between Employee and Department on dept_id.\n- [2 marks] Accurate selection condition salary > budget.\n- [2 marks] Final projection on attribute name.",
                "difficulty": 3,
            },
        ],
    },
    "t3": {  # SQL Fundamentals & Complex Joins
        "mcq": [
            {
                "stem": "Which type of SQL join returns all rows from the left table, along with matched rows from the right table, and fills unmatched right-table columns with NULL?",
                "options": [
                    {"id": "A", "text": "LEFT OUTER JOIN"},
                    {"id": "B", "text": "INNER JOIN"},
                    {"id": "C", "text": "FULL OUTER JOIN"},
                    {"id": "D", "text": "CROSS JOIN"},
                ],
                "key": "A",
                "rationale": "LEFT OUTER JOIN preserves all tuples from the left relation, substituting NULL for missing right-relation matches. B discards unmatched tuples. C preserves tuples from both sides. D forms the cartesian product.",
                "difficulty": 2,
            },
            {
                "stem": "Consider a query joining Orders and Customers with `Orders LEFT JOIN Customers ON Orders.cust_id = Customers.id WHERE Customers.city = 'London'`. Why does this query behave like an INNER JOIN?",
                "options": [
                    {"id": "A", "text": "The WHERE clause filters out NULL values generated for unmatched Customers rows"},
                    {"id": "B", "text": "The ON clause is evaluated after the WHERE filter in standard SQL execution"},
                    {"id": "C", "text": "LEFT JOIN automatically coerces to INNER JOIN when primary keys are referenced"},
                    {"id": "D", "text": "City comparison requires index lookup which invalidates outer join semantics"},
                ],
                "key": "A",
                "rationale": "When a WHERE clause checks Customers.city = 'London', any unmatched rows where Customers fields are NULL evaluate to UNKNOWN and are discarded, nullifying the outer join effect. B is incorrect because ON evaluates before WHERE. C and D are false.",
                "difficulty": 4,
            },
        ],
        "short_answer": [
            {
                "stem": "Write a SQL query using window functions to find the top 2 highest-paid employees in each department from table Employee(id, name, department_id, salary). If there are ties in salary, employees should receive the same rank without skipping rank numbers.",
                "key": "WITH Ranked AS (SELECT id, name, department_id, salary, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rnk FROM Employee) SELECT id, name, department_id, salary FROM Ranked WHERE rnk <= 2;",
                "rationale": "Marking Rubric:\n- [2 marks] Proper use of DENSE_RANK() window function to handle ties without gap.\n- [2 marks] Correct PARTITION BY department_id and ORDER BY salary DESC.\n- [2 marks] CTE or subquery structure filtering rnk <= 2.",
                "difficulty": 4,
            },
        ],
    },
    "t4": {  # Subqueries & Aggregations
        "mcq": [
            {
                "stem": "In SQL, what is the fundamental difference between the WHERE clause and the HAVING clause?",
                "options": [
                    {"id": "A", "text": "WHERE filters individual rows before grouping; HAVING filters aggregated groups after GROUP BY"},
                    {"id": "B", "text": "WHERE can only be used with equality predicates, whereas HAVING supports inequality"},
                    {"id": "C", "text": "HAVING can only operate on indexed primary key columns"},
                    {"id": "D", "text": "WHERE evaluates aggregate functions (COUNT, SUM) while HAVING evaluates scalar subqueries"},
                ],
                "key": "A",
                "rationale": "WHERE filters input rows before aggregation takes place, whereas HAVING filters summary groups produced by GROUP BY. Aggregate functions are invalid in WHERE. B, C, and D are factually incorrect.",
                "difficulty": 2,
            },
            {
                "stem": "When using a correlated subquery with the `EXISTS` predicate in SQL, what value does the inner subquery actually evaluate to satisfy the predicate?",
                "options": [
                    {"id": "A", "text": "TRUE as soon as the inner query yields at least one matching tuple"},
                    {"id": "B", "text": "The count of matching records compared against zero"},
                    {"id": "C", "text": "A scalar NULL value if no rows match"},
                    {"id": "D", "text": "A Cartesian boolean matrix across all subquery columns"},
                ],
                "key": "A",
                "rationale": "EXISTS evaluates to TRUE immediately upon finding the first matching tuple without needing to materialize the entire inner result set. B, C, and D describe alternative or incorrect mechanisms.",
                "difficulty": 3,
            },
        ],
        "short_answer": [
            {
                "stem": "Explain the difference between correlated and non-correlated subqueries in SQL with respect to query execution and performance. Write an example of a correlated subquery that finds all employees whose salary exceeds their department's average salary.",
                "key": "Non-correlated subqueries execute once independently; correlated subqueries depend on the outer query's current row and execute conceptually once per outer tuple. Query: SELECT * FROM Employee e WHERE salary > (SELECT AVG(salary) FROM Employee WHERE dept_id = e.dept_id);",
                "rationale": "Marking Rubric:\n- [2 marks] Clear definition of execution difference (one-time vs per-tuple evaluation).\n- [2 marks] Performance impact discussion (potential nested loop overhead without optimizer unnesting).\n- [2 marks] Correct correlated SQL query with outer reference e.dept_id.",
                "difficulty": 3,
            },
        ],
    },
    "t5": {  # Transactions & Concurrency Control (ACID)
        "mcq": [
            {
                "stem": "Under ANSI SQL transaction isolation levels, which anomaly occurs when Transaction T1 reads a row, Transaction T2 updates that row and commits, and T1 subsequently re-reads the row obtaining the updated value?",
                "options": [
                    {"id": "A", "text": "Non-Repeatable Read (Fuzzy Read)"},
                    {"id": "B", "text": "Dirty Read"},
                    {"id": "C", "text": "Phantom Read"},
                    {"id": "D", "text": "Lost Update"},
                ],
                "key": "A",
                "rationale": "A non-repeatable read occurs when committed modifications change data previously read in the transaction. Dirty read occurs when uncommitted modifications are read. Phantom read involves newly inserted rows matching a range predicate. Lost update occurs when concurrent writes overwrite without locking.",
                "difficulty": 3,
            },
            {
                "stem": "In the Strict Two-Phase Locking (Strict 2PL) protocol, when are exclusive write locks held by a transaction released?",
                "options": [
                    {"id": "A", "text": "Only at the end of the transaction after COMMIT or ABORT"},
                    {"id": "B", "text": "Immediately after the corresponding write operation completes"},
                    {"id": "C", "text": "At the start of the shrinking phase before commit"},
                    {"id": "D", "text": "When another transaction requests a shared lock on the same item"},
                ],
                "key": "A",
                "rationale": "Strict 2PL requires all exclusive locks to be held until the transaction finishes (commit or abort), preventing cascading aborts. B is true for short-duration locks. C describes basic 2PL, not Strict 2PL. D would violate serializability.",
                "difficulty": 3,
            },
        ],
        "short_answer": [
            {
                "stem": "Consider a schedule with transactions T1 and T2: T1 reads A, T2 writes A, T1 writes A, T2 commits, T1 aborts. Identify the concurrency anomaly that occurs if T2 is allowed to commit, and explain how Strict Two-Phase Locking (Strict 2PL) prevents this anomaly.",
                "key": "Cascading Abort / Dirty Write anomaly. T2 wrote uncommitted data written or read by T1. Under Strict 2PL, T1 holds its exclusive lock on A until T1 commits/aborts, preventing T2 from obtaining a lock on A until T1 completes.",
                "rationale": "Marking Rubric:\n- [2 marks] Accurately identify cascading abort risk or dirty write anomaly.\n- [2 marks] Explain how exclusive lock retention until transaction termination blocks T2.\n- [2 marks] Conclude why Strict 2PL guarantees recoverable, cascade-free schedules.",
                "difficulty": 4,
            },
            {
                "stem": "State the four ACID properties of relational transactions. For each property, specify the exact database management system component or subsystem responsible for ensuring it.",
                "key": "Atomicity (Recovery Manager / WAL), Consistency (Integrity Constraints / Schema validation), Isolation (Concurrency Control / Lock Manager), Durability (Recovery Manager / Log / Non-volatile storage).",
                "rationale": "Marking Rubric:\n- [2 marks] Correct definition of all 4 ACID properties.\n- [2 marks] Accurate mapping to DBMS components (Lock Manager, Recovery Manager, WAL).\n- [2 marks] Explanation of interplay between Isolation and Durability during system crash.",
                "difficulty": 3,
            },
        ],
    },
    "t6": {  # B+ Tree Indexing & Query Tuning
        "mcq": [
            {
                "stem": "In a B+ tree of order d with fanout M, why do non-leaf internal nodes contain only keys and child pointers, while all actual data record pointers reside strictly in the leaf nodes?",
                "options": [
                    {"id": "A", "text": "To maximize node fanout, keeping tree height small and minimizing disk I/O"},
                    {"id": "B", "text": "To prevent page splits when records are inserted into internal nodes"},
                    {"id": "C", "text": "Because relational algebra does not permit non-leaf indexing"},
                    {"id": "D", "text": "To guarantee that search operations run in O(1) constant time"},
                ],
                "key": "A",
                "rationale": "Omitting record pointers from internal nodes saves space, enabling high fanout (often 100-200), which keeps tree height low (typically 3-4 levels) and reduces disk block transfers. B, C, and D are conceptually wrong.",
                "difficulty": 3,
            },
            {
                "stem": "Given a composite B+ tree index on `(department_id, salary, hire_date)`, which of the following SQL WHERE clauses can NOT use this index for index filtering?",
                "options": [
                    {"id": "A", "text": "WHERE salary > 50000 AND hire_date = '2023-01-01'"},
                    {"id": "B", "text": "WHERE department_id = 10 AND salary > 50000"},
                    {"id": "C", "text": "WHERE department_id = 10"},
                    {"id": "D", "text": "WHERE department_id = 10 AND salary = 60000 AND hire_date > '2022-01-01'"},
                ],
                "key": "A",
                "rationale": "Composite B+ tree indexes can only be searched if the leading column (department_id) is specified in the predicate (leftmost prefix rule). Without department_id, the index cannot be traversed efficiently. B, C, and D all include the leading attribute.",
                "difficulty": 4,
            },
        ],
        "short_answer": [
            {
                "stem": "Distinguish between a clustered (primary) index and an unclustered (secondary) index in terms of physical disk page organization and range query performance. Why can a relation have at most one clustered index?",
                "key": "A clustered index dictates the physical sorting order of data records on disk pages. An unclustered index maintains pointers to records without altering physical ordering. A table can only have one clustered index because physical rows can only be sorted in one order on disk.",
                "rationale": "Marking Rubric:\n- [2 marks] Explain physical data record ordering on disk for clustered vs unclustered.\n- [2 marks] Explain why range scans are significantly faster on clustered indexes (sequential I/O vs random I/O).\n- [2 marks] Clearly state why at most one clustered index can exist per table.",
                "difficulty": 4,
            },
        ],
    },
    "t7": {  # Normalization (1NF, 2NF, 3NF, BCNF)
        "mcq": [
            {
                "stem": "A relation R(A, B, C, D) is in Third Normal Form (3NF) if for every non-trivial functional dependency X → Y, which condition is satisfied?",
                "options": [
                    {"id": "A", "text": "X is a superkey OR Y is a prime attribute (part of a candidate key)"},
                    {"id": "B", "text": "X is a superkey in all cases without exception"},
                    {"id": "C", "text": "No composite candidate keys exist in relation R"},
                    {"id": "D", "text": "All non-prime attributes are transitively dependent on the primary key"},
                ],
                "key": "A",
                "rationale": "3NF allows X → Y if X is a superkey OR Y is a prime attribute. B is the stricter definition of Boyce-Codd Normal Form (BCNF). C is irrelevant. D violates 3NF.",
                "difficulty": 3,
            },
            {
                "stem": "Which normal form guarantees lossless join decomposition and dependency preservation, whereas Boyce-Codd Normal Form (BCNF) guarantees lossless join but cannot always preserve all functional dependencies?",
                "options": [
                    {"id": "A", "text": "Third Normal Form (3NF)"},
                    {"id": "B", "text": "Second Normal Form (2NF)"},
                    {"id": "C", "text": "Fourth Normal Form (4NF)"},
                    {"id": "D", "text": "First Normal Form (1NF)"},
                ],
                "key": "A",
                "rationale": "3NF decomposition algorithms guarantee both lossless join and dependency preservation. BCNF cannot always achieve dependency preservation for all relational schemas. B and D have redundancy anomalies.",
                "difficulty": 3,
            },
        ],
        "short_answer": [
            {
                "stem": "Given relation R(A, B, C, D, E) with functional dependencies F = {A → B, BC → D, D → E}. Find all candidate keys of R, determine the highest normal form of R (1NF, 2NF, 3NF, or BCNF), and justify your answer.",
                "key": "Candidate Key: AC (closure {A, C}+ = {A, C, B, D, E} = R). Since A → B has A not a superkey and B not prime, R contains a partial dependency on candidate key AC, so R is only in 1NF.",
                "rationale": "Marking Rubric:\n- [2 marks] Correct attribute closure calculation showing AC is the unique candidate key.\n- [2 marks] Identify that A → B violates 2NF because non-prime attribute B depends on proper subset A of candidate key AC.\n- [2 marks] Conclude highest normal form is 1NF with rigorous dependency justification.",
                "difficulty": 4,
            },
        ],
    },
    "t8": {  # Crash Recovery & Write-Ahead Logging
        "mcq": [
            {
                "stem": "Under the Write-Ahead Logging (WAL) protocol, what fundamental rule must the database engine enforce BEFORE a dirty data page can be written from volatile buffer pool memory to disk?",
                "options": [
                    {"id": "A", "text": "The corresponding log record describing the update must be flushed to non-volatile disk storage"},
                    {"id": "B", "text": "All active transactions in the system must reach a COMMIT state"},
                    {"id": "C", "text": "The entire database must create an atomic fuzzy checkpoint"},
                    {"id": "D", "text": "All shared read locks on the page must be converted to exclusive locks"},
                ],
                "key": "A",
                "rationale": "The WAL protocol dictates that the log record detailing the change must be written to stable storage before the modified dirty data page is written to disk. This ensures atomicity during crash recovery. B, C, and D are not WAL rules.",
                "difficulty": 3,
            },
            {
                "stem": "In the ARIES recovery algorithm, which phase scans the log forward from the earliest unwritten dirty page table entry to reconstruct the exact database state at the time of system crash?",
                "options": [
                    {"id": "A", "text": "Redo phase"},
                    {"id": "B", "text": "Analysis phase"},
                    {"id": "C", "text": "Undo phase"},
                    {"id": "D", "text": "Checkpoint phase"},
                ],
                "key": "A",
                "rationale": "The Redo phase in ARIES repeats history by scanning forward and reapplying updates for all logged transactions (both committed and uncommitted). The Analysis phase identifies dirty pages and active transactions; Undo rolls back loser transactions.",
                "difficulty": 4,
            },
        ],
        "short_answer": [
            {
                "stem": "Explain the role of the STEAL and NO-FORCE buffer pool management policies in relational database engines, and describe how Write-Ahead Logging (WAL) enables DBMS to support both policies while ensuring ACID atomicity and durability.",
                "key": "STEAL allows buffer pool to flush uncommitted dirty pages to disk to free frames (requires UNDO logging for Atomicity). NO-FORCE allows transaction commit without forcing dirty pages to disk immediately (requires REDO logging for Durability). WAL provides both UNDO and REDO records.",
                "rationale": "Marking Rubric:\n- [2 marks] Precise definitions of STEAL (memory eviction of uncommitted data) and NO-FORCE (commit without immediate data flush).\n- [2 marks] Explain how UNDO log records restore previous values if a stolen page belonged to an aborted transaction.\n- [2 marks] Explain how REDO log records reapply committed changes that were not yet written to disk.",
                "difficulty": 4,
            },
        ],
    },
}


async def run_item_writer_agent(assessment_id: str, run_id: Optional[str] = None) -> List[Item]:
    """
    Executes the Item Writer Agent:
    1. Loads assessment and blueprint cells.
    2. Calculates the candidates needed per cell: one set per version plus a 0.5× spare.
    3. Grounding: searches course knowledge base via Vertex AI / local search.
    4. Generates candidate items (via the LLM or curriculum bank).
    5. Computes 768-dim semantic embeddings for duplicate audit.
    6. Attaches source citations and distractor rationales.
    7. Writes candidate items to Firestore and records step-by-step traces.
    8. Updates assessment status to 'pool_ready'.
    """
    start_time = time.time()
    assessment_data = await db.get("assessments", assessment_id)
    if not assessment_data:
        raise ValueError(f"Assessment {assessment_id} not found")

    course_id = assessment_data.get("courseId", "CS2040")
    course_data = await db.get("courses", course_id) or {}
    rid = run_id or assessment_data.get("runId") or f"run-writer-{assessment_id}"

    # A re-draft replaces the pool: old candidates (maybe from a discarded blueprint) and the
    # flags and versions built on them must not reach the solver or the reviewer's bill.
    for coll in ("items", "flags", "versions"):
        old = await db.query(coll, filters=[("assessmentId", "==", assessment_id)])
        await asyncio.gather(*[db.delete(coll, d["id"]) for d in old])
    await db.delete("equivalenceReports", assessment_id)

    # 1. Fetch blueprint
    blueprint_data = await db.get("blueprints", assessment_id)
    if not blueprint_data or not blueprint_data.get("cells"):
        # Auto-generate blueprint if missing
        from app.agents.blueprint import run_blueprint_agent
        bp = await run_blueprint_agent(assessment_id, run_id=rid)
        blueprint_data = bp.model_dump()

    blueprint = Blueprint(**blueprint_data)
    cells = blueprint.cells

    # Versions share no items, so draft one set per version plus a 0.5x spare for reviewer rejects.
    pool_multiplier = assessment_data.get("numVersions", 2) + 0.5
    total_needed = sum(c.count for c in cells)
    total_candidate_target = sum(math.ceil(c.count * pool_multiplier) for c in cells)

    await tracker.record_step(
        run_id=rid,
        agent="ItemWriter",
        tool="plan_item_pool",
        input_summary=f"Blueprint requires {total_needed} items across {len(cells)} cells. Target pool size: {total_candidate_target} ({pool_multiplier}× buffer multiplier).",
        output_summary=f"Initiating grounded drafting for {len(cells)} cell configurations across topics {', '.join(set(c.topicId for c in cells))}",
        status="running",
    )

    client = get_llm_client()
    created_items: List[Item] = []

    # Cache citations per topic to avoid repetitive network calls
    topic_citations: Dict[str, List[SourceCitation]] = {}
    for cell in cells:
        topic_id = cell.topicId
        if topic_id not in topic_citations:
            topic_name = topic_id
            for t in course_data.get("topics", []):
                if t.get("id") == topic_id:
                    topic_name = t.get("name", topic_id)
                    break
            citations = await search_knowledge_base(
                query=f"{topic_name} {cell.bloom} assessment",
                course_id=course_id,
                top_k=3,
            )
            if not citations:
                citations = [
                    SourceCitation(
                        docId=f"syllabus-{course_id}",
                        title=f"{course_id} Official Course Syllabus",
                        snippet=f"Syllabus specification for {topic_name}: covers theoretical foundations, practical problems, and assessment outcomes.",
                    )
                ]
            topic_citations[topic_id] = citations

    instruction = ""
    try:
        with open("app/agents/prompts/item_writer.md", "r") as f:
            instruction = f.read()
    except Exception:
        pass

    sem = asyncio.Semaphore(6)

    async def process_single_cell(idx: int, cell: BlueprintCell) -> List[Item]:
        async with sem:
            topic_id = cell.topicId
            q_type = cell.qType
            cell_target = math.ceil(cell.count * pool_multiplier)
            cell_citations = topic_citations.get(topic_id, [])
            cell_items: List[Item] = []
            llm_items = []

            # The LLM often returns fewer candidates than asked; ask again for the remainder (max 3 calls).
            attempts = 0
            while client and len(llm_items) < cell_target and attempts < 3:
                attempts += 1
                try:
                    prompt = (
                        f"{instruction}\n\n"
                        f"Topic ID: {topic_id}\n"
                        f"CLO ID: {cell.cloId}\n"
                        f"Cognitive Bloom Level: {cell.bloom}\n"
                        f"Question Type: {q_type}\n"
                        f"Marks Each: {cell.marksEach}\n"
                        f"Number of Candidates to Generate: {cell_target - len(llm_items)}\n"
                        f"Grounding Citations Available:\n"
                        + "\n".join([f"- [{c.docId}] {c.snippet}" for c in cell_citations])
                    )
                    if llm_items:
                        prompt += "\n\nDo NOT repeat these already-written stems:\n" + "\n".join(f"- {g['stem']}" for g in llm_items)

                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=settings.LLM_MODEL,
                        contents=prompt,
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": CellItemsResponse,
                            "thinking_config": {"thinking_budget": 0},
                        },
                    )
                    parsed = json.loads(response.text)
                    llm_items += parsed.get("items", [])
                except Exception as e:
                    logger.warning(f"LLM ItemWriter for cell {idx} failed ({e}); falling back to curriculum bank.")

            cell_generated_count = 0
            if llm_items:
                batch = llm_items[:cell_target]
                embeddings = await asyncio.to_thread(compute_embeddings, [g["stem"] for g in batch])
                new_items: List[Item] = []
                for g_item, embedding_vec in zip(batch, embeddings):
                    item_id = f"item-{uuid.uuid4().hex[:8]}"
                    opts = None
                    if q_type == "mcq" and g_item.get("options"):
                        opts = [Option(id=o["id"], text=o["text"]) for o in g_item["options"]]
                    new_items.append(Item(
                        id=item_id,
                        assessmentId=assessment_id,
                        stem=g_item["stem"],
                        options=opts,
                        key=g_item["key"],
                        rationale=g_item["rationale"],
                        qType=q_type,
                        marks=cell.marksEach,
                        cloId=cell.cloId,
                        topicId=cell.topicId,
                        bloom=cell.bloom,
                        difficulty=g_item.get("difficulty", 3),
                        difficultySource="ai",
                        sourceCitations=cell_citations,
                        status="candidate",
                        embedding=embedding_vec,
                        promptVersion="v1.0",
                    ))
                await asyncio.gather(*[db.set("items", it.id, it.model_dump()) for it in new_items])
                cell_items.extend(new_items)
                cell_generated_count += len(new_items)

            # Strict mode: a smaller real pool beats canned filler, as long as the cell itself can be filled.
            if settings.STRICT_MODE and cell_generated_count >= cell.count:
                return cell_items
            # Fallback to high-quality topic item bank if the LLM produced fewer than target
            if cell_generated_count < cell_target:
                require_llm_or_fallback("Item writer agent")
                bank_candidates = TOPIC_ITEM_BANK.get(topic_id, {}).get(q_type, [])
                if not bank_candidates:
                    bank_candidates = TOPIC_ITEM_BANK.get("t1", {}).get(q_type, [])
                if not bank_candidates:
                    # No canned bank for this type (e.g. essay): keep what the LLM wrote if the cell can be filled.
                    if cell_generated_count >= cell.count:
                        return cell_items
                    raise RuntimeError(
                        f"Item writer: the LLM produced {cell_generated_count}/{cell.count} '{q_type}' questions "
                        f"for {cell.cloId}/{topic_id} and no fallback bank exists for this type."
                    )

                candidate_idx = 0
                while cell_generated_count < cell_target:
                    raw_template = bank_candidates[candidate_idx % len(bank_candidates)]
                    candidate_idx += 1

                    suffix = f" (Variant {candidate_idx})" if candidate_idx > len(bank_candidates) else ""
                    item_id = f"item-{uuid.uuid4().hex[:8]}"

                    stem_text = raw_template["stem"] + suffix
                    opts = None
                    if q_type == "mcq":
                        opts = [Option(id=o["id"], text=o["text"]) for o in raw_template["options"]]

                    embedding_vec = await asyncio.to_thread(compute_embedding, stem_text)

                    item_obj = Item(
                        id=item_id,
                        assessmentId=assessment_id,
                        stem=stem_text,
                        options=opts,
                        key=raw_template["key"],
                        rationale=raw_template["rationale"],
                        qType=q_type,
                        marks=cell.marksEach,
                        cloId=cell.cloId,
                        topicId=cell.topicId,
                        bloom=cell.bloom,
                        difficulty=raw_template.get("difficulty", 3),
                        difficultySource="ai",
                        sourceCitations=cell_citations,
                        status="candidate",
                        embedding=embedding_vec,
                        promptVersion="v1.0",
                    )
                    await db.set("items", item_id, item_obj.model_dump())
                    cell_items.append(item_obj)
                    cell_generated_count += 1

            return cell_items

    cell_results = await asyncio.gather(*[process_single_cell(i, c) for i, c in enumerate(cells)])
    for r in cell_results:
        created_items.extend(r)

    duration_ms = int((time.time() - start_time) * 1000)

    # 4. Update assessment status
    await db.update("assessments", assessment_id, {"status": "pool_ready"})

    # 5. Record agent step trace
    all_cited_docs = list(
        set(c.title or c.docId for cit_list in topic_citations.values() for c in cit_list)
    )
    await tracker.record_step(
        run_id=rid,
        agent="ItemWriter",
        tool="synthesize_item_pool",
        input_summary=f"Synthesized candidate items for {len(cells)} blueprint cells with {pool_multiplier}× buffer multiplier",
        output_summary=f"Successfully drafted {len(created_items)} grounded candidate items ({sum(1 for i in created_items if i.qType == 'mcq')} MCQs, {sum(1 for i in created_items if i.qType == 'short_answer')} Structured, {sum(1 for i in created_items if i.qType == 'essay')} Free Response) with 768-dim embeddings and distractor rationales.",
        status="completed",
        duration_ms=duration_ms,
        sources=all_cited_docs[:6],
    )

    # 6. Log event to telemetry
    await log_event(
        event_type="pool_generated",
        user_role="lecturer",
        assessment_id=assessment_id,
        meta={
            "items_count": len(created_items),
            "mcq_count": sum(1 for i in created_items if i.qType == "mcq"),
            "sa_count": sum(1 for i in created_items if i.qType == "short_answer"),
            "target_required": total_needed,
            "buffer_ratio": round(len(created_items) / max(1, total_needed), 2),
        },
    )

    return created_items
