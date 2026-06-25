# GR-ARC-3 Domain Model

## Nodes

| cluster | name | description | remark |
| --- | --- | --- | --- |
| consider | Conception |  |  |
| consider / world | WorldModel |  |  |
| consider / goal | GoalPredicate |  |  |
| consider / plan | GamePlan |  |  |
| consider / plan | Step |  |  |
| consider / world | PiStateAbstraction |  |  |
| consider / world | InteractionRule |  |  |
| consider / world | MarkovState |  |  |
| consider / goal | GoalPatterns |  |  |
| input | TurnRecord |  |  |
| input | Probe |  |  |
| output | GameMove |  |  |
| output | Action |  |  |
| vocabulary | GameObject |  |  |
| vocabulary | Profile |  |  |
| vocabulary | Lexicon |  |  |
| vocabulary | Dimension |  |  |
| vocabulary | Relation |  |  |

## Edges

| arrow | source | target | label | description | remark |
| --- | --- | --- | --- | --- | --- |
| composition | Conception | WorldModel | world |  |  |
| composition | Conception | GoalPredicate | goal |  |  |
| composition | Conception | GamePlan | plan |  |  |
| composition | WorldModel | InteractionRule | rules  1..* |  |  |
| composition | WorldModel | PiStateAbstraction | abstraction  1 |  |  |
| composition | GamePlan | Step | ordered steps  1..* |  |  |
| composition | GameObject | Profile | has  1 |  |  |
| composition | Lexicon | Dimension | defines (unary)  * |  |  |
| composition | Lexicon | Relation | defines (n-ary)  * |  |  |
| aggregation | Probe | GameMove | trial moves (to LEARN)  1..* |  |  |
| directed_association | GamePlan | GoalPredicate | aims at |  |  |
| directed_association | Step | GameMove | move |  |  |
| directed_association | TurnRecord | GameMove | records played |  |  |
| directed_association | Profile | Dimension | value per Dimension |  |  |
| directed_association | Relation | GameObject | over (n) objects |  |  |
| dependency | GoalPatterns | GoalPredicate | instantiated into (bind roles to objects) |  |  |
| dependency | Step | MarkovState | expect (predicted) |  |  |
| dependency | Action | GameMove | external encoding; GameIO translates |  |  |
| dependency | PiStateAbstraction | MarkovState | maps Frame to MarkovState |  |  |
| dependency | InteractionRule | MarkovState | (MarkovState, GameMove) to next |  |  |
| dependency | InteractionRule | Relation | triggers on / sets relations |  |  |
| dependency | GoalPredicate | MarkovState | tests (win?) |  |  |
| dependency | GoalPredicate | GameObject | conditions over objects |  |  |
| dependency | GoalPredicate | Relation | tests relations |  |  |
| dependency | WorldModel | GameObject | models object dynamics |  |  |
| dependency | PiStateAbstraction | GameObject | abstracts salient objects |  |  |

## Clusters

| cluster | label | description | remark |
| --- | --- | --- | --- |
| input | Input port — perception (perceive) |  |  |
| consider | Consider — the Conception (decide) |  |  |
| consider / world | world — model the world |  |  |
| consider / goal | goal — decide the goal |  |  |
| consider / plan | plan — plan toward the goal |  |  |
| output | Output port — action (act) |  |  |
| vocabulary | Vocabulary — Lexicon (Dimensions + Relations) |  |  |
