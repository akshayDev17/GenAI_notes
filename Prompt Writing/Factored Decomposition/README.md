# Factored Decomposition: Process, Problems, and Alternatives

## 1. Factored Decomposition Process

### 1.1 The Three-Stage Process
* Factored decomposition splits reasoning into three separate, sequential stages [17].
* These stages are decomposition, subquestion-answering, and final recomposition [17].
* It isolates contexts to block implicit prompt-level biases [11, 18].

### 1.2 Detailed Walkthrough of the Flow
* We evaluate: "What is the maiden name of the scoring record holder's wife?" [114, 122].
* **Step A: Initial Decomposition**
    * The planner receives the target question and options [17, 114].
    * It drafts a sequential list of dependent subquestions [17, 114].
    * The initial plan contains reference tags to future answers [17, 114].
    * Output: Q1 (Who holds record?), Q2 (Wife of A1?), Q3 (Maiden name of A2?) [114].
* **Step B: Isolated Answering (Turn 1)**
    * Subquestion 1 is routed to a fresh context [17].
    * The answering agent cannot see the parent prompt [11, 17].
    * Answer 1: LeBron James [114].
* **Step C: Re-Decomposition (Turn 2)**
    * Answer 1 is fed back to the planner [17, 114].
    * The planner resolves the first dependency placeholder [17, 114].
    * Output: Q2 (Who is LeBron's wife?), Q3 (Maiden name of A2?) [114].
* **Step D: Isolated Answering (Turn 2)**
    * Subquestion 2 is routed to another isolated context [17].
    * Answer 2: Savannah James [115].
* **Step E: Final Re-Decomposition (Turn 3)**
    * Answer 2 is fed back to the planner [17, 115].
    * The planner resolves the second dependency placeholder [17, 115].
    * Output: Q3 (What is Savannah's maiden name?) [115].
* **Step F: Isolated Answering (Turn 3)**
    * Subquestion 3 is answered in a fresh context [17].
    * Answer 3: Brinson [115].
* **Step G: Loop Termination**
    * The final subanswer is passed to the planner [17, 115].
    * The planner generates the exit token `<FIN></FIN>` [17, 115].
* **Step H: Recomposition**
    * All clean subanswers are passed to the recomposer [17, 122].
    * The model selects choice (C) Brinson [122, 123].

---

## 2. Problems with the Conversational Approach

### 2.1 Cost and Latency Limitations
* The conversational loop scales token usage quadratically with each iteration.
* We send the massive instructions and history back in every turn.
* Multiple sequential API calls make parallel processing impossible.
* This slow loop increases system latency and operational costs.

### 2.2 Logical and Linguistic Issues
* Models often make spelling or casing errors in structural XML tags.
* A single missing bracket crashes strict programmatic parser scripts.
* Raw string replacement of placeholders causes severe grammatical misalignment.
* Linguistic clutter in subquestions degrades isolated answering accuracy.
* Autocompletions frequently generate forward-reference logic errors due to sequential generation.

---

## 3. Alternative Architectures

### 3.1 Programmatic JSON DAG Architecture
* The model generates a structured JSON dependency graph upfront.
* Python parses the graph, substituting answers programmatically in memory.
* **Limitations:**
    * Generating valid JSON dependency keys is highly prone to model errors.
    * Models struggle to map abstract dependencies in a single generation step.
    * The entire plan is locked in at turn one.
    * It cannot adapt if an early subanswer returns "Unknown".

### 3.2 Hybrid Lazy-Decomposition Architecture
* The heavy planner runs once to output the initial text list.
* We execute and resolve ready nodes programmatically using local Python.
* We trigger heavy planner context repairs only on dynamic pivots.
* **Limitations:**
    * Needs a cheap helper model to fix grammatically misaligned stitched questions.
    * Complex regex parsing is still vulnerable to tag-bracket mutations.
    * Slightly higher code complexity than simple conversational loops.
