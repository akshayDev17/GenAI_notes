- check how metadata is given
    - <font color="red">PK-FK relationship, whether this is explicitly specified</font>
- test and train set DBs are kept different
    - to force the model to learn to write SQL on unknown DBs
- program-based splitting method of model-evaluation: train and test don't have the exact same SQLs.
    - they would've had the same queries if some of the paraphrases were put in the train set and some in the test set.
    - this method of evaluation basically means that for a given Y(SQL) all paraphrases(prompts) will either be in the train or the test set exclusively.
- column name renaming
    - columns such as `stu_id` were formatted to `student_id` for ease of column name-interpretation by the model.
- for keeping the prompts natural, no template was used to generate them, against the SQLs written for them.
- prompt-SQL pairs across the train and test sets were created such that each table in each DB used will be mentioned in at least 1 pair.
- consistency of SQL labels(SQL is the label in this ML problem)
    - SQL queries to similar questions should themselves be similar
    - totally different SQL labels will hinder semantic-parser's training
    - for instance:
        - Q1: Whats the population of France? S1: SELECT population from COUNTRIES where country='France'
        - Q2: How many people live in France? S1: SELECT count(*) from population_data where country='France'
        - this is unacceptable. the answer for both questions will rather be the first SQL.
- <font color="orange">Drawback Alert!!</font> no cross-DB sample seem to exist in any dataset
    - all samples seemingly have tables belonging to the same database(`db_id`).
- <font color="orange">Drawback Alert!!</font>vague/ambiguous questions are excluded from train/test sets
    - *which lanes are the most popular?*
        - no clear definition of popularity
        - a better question: which lanes *ship the highest no. of shipments*?
        - <font color="magenta">Idea!!</font>: this is good for training, but at real time inference, the questions could be ambiguous.
            - you could rather have an intermediate LLM(agent) functioning as ambiguity resolver.
            - it would be instructed to create a disambiguous prompt out of the ambiguous one entered by the user.
    - to resolve ambiguity, need to build a chat history of the Text-to-SQL model with the questioner.
- <font color="orange">Drawback Alert!!</font>questions that require knowledge outside of that mentioned in the DB(schema description) are excluded from train/test datasets
    - yield, OR as concepts, unless otherwise mentioned in the prompt's metadata
    - no. of employees working under John Doe.
        - <font color="magenta">Idea!!</font>: a clear mention in the metadata of the employee-manager relationship, preferrably with an example, might tackle this.
- different complex SQLs based on different databases belonging to different domains
    - domains: successfactors + PnD + LNH + Pricing
    - databases: (attrition rate/labor workforce planning/management restructuring), (SCO/PUR), (PLT/HSS utilization), (RFP/Tariff/Dynamic Prc)
