# Semantic Parsing vs Semantic Matching(SP vs SM)
- datasets before spider: largely based on SM
    - result of query(target and inference) should be the same
    - example:\
        Target: `SELECT * FROM EMPLOYEE WHERE JOIN_DT > '2023-04-01'`
        Inference: `SELECT * FROM EMPLOYEE WHERE '2023-04-01' < JOIN_DT`
    - advantages:
        - leeway to model in terms of query generation
        - easier to evaluate model accuracy when this is used as the accuracy/evaluation metric
- datasets before spider that were based on SP
    - single-DS(dataset) based, i.e. same DB used in train and test
        - model doesn't develop intelligence to understand given metadata(schema-description w.r.t. dataset), it'll simply memorise it.
        - Testing on the same schema used for training --> overly optimistic performance metrics.
    - 4-10 textually varying *prompts*(input) had the same SQL as their output(target).
    - simple SQLs if multiple DSs were involved, such as WikiSQL

# Task Definition
- generated SQL needs to have correct structure + correct columns used/selected(excludes criterion for correct value(output) generation in generated SQL)
    - due to the low performance of the then SOTA Text-to-SQL models, this exclusion was factored in.
    - ideally, values should also have been correct.
    - For example, given the question “What is the population of Paris?”, the model needs to output a query like `SELECT population FROM cities WHERE name = 'Paris'`.
    - In this query, generating 'Paris' (a value) is difficult because it requires the model to precisely understand the user input and map it to a database entry.

# Providing metadata to model
- for a given set of samples belonging to the same DB
    - a big column list(containing all columns across all tables of the DB) is supplied

# Evaluation Metrics

## Component Matching
- all clauses = components
    - SELECT, FROM, ORDER BY, WHERE, GROUPBY, other KEYWORDS
- components split into further *sets* of sub-components
    - SELECT avg(col1), min(col1), avg(col2) --->  (avg, min, col1), (avg, col2)
- the component-sets of predicted SQL and the gold SQL are compared to see how many match
    - the order isn't matched , just the content.
    - SELECT avg(col1), min(col1), avg(col2) $\cong$ SELECT avg(col1), avg(col2), min(col1)
    - all sets should be sorted based on column name, within a set all elements should be sorted by the function name
- **Inadequacy:** order isn't taken into account
    - final schema of the output changes when column order is considered, hence creating a different table altogether.

## Exact Matching
- the sets should also entirely match
- this 
<font color="Red">READ CODE</font>

## Input-output pairs used while evaluating
- since spider is pretty old(early 2019), most models used are sequence-to-sequence non-transformer/non-LLM models.
- hence input has to be tokenized before being passed to the model, and the gold SQL also has to be tokenized for carrying out evaluation.
- this paper should only be referred to
    - know what spider is, 
    - how it was created, 
    - how is it better/more complex than other text-to-sql datasets
    - 

# Appendix

## Research Papers
- [Spider](https://arxiv.org/pdf/1809.08887v5)
- [Improving Text-to-SQL methodology](https://arxiv.org/pdf/1806.09029)