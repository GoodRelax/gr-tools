#### Nodes

| cluster | name | description | remark |
| --- | --- | --- | --- |
| consider | Conception | The agent's current working hypothesis for a turn: bundles the world model, the goal, and the plan. | Stereotype 'answer'. Lifecycle via status: active -> committed -> retired; score ranks competing conceptions. |
| consider / world | WorldModel | Models the game's dynamics: a set of interaction rules plus the state-abstraction function. | impl may be Symbolic, Learned, or Graph; predict() drives look-ahead during planning. |
| consider / goal | GoalPredicate | Expresses a win or sub-goal condition as a composable predicate over objects and relations. | Composable via kind (Atom/AND/OR/SEQUENCE); children are ordered only for SEQUENCE. |
| consider / plan | GamePlan | An ordered sequence of steps toward the goal, bounded by a planning horizon. | Re-planned when the world model or goal changes. |
| consider / plan | Step | One planned move plus its expected resulting state and the sub-goal it serves. | Value object: a step is compared by content, not identity. |
| consider / world | PiStateAbstraction | The abstraction function (pi) that projects a raw Frame into an abstract MarkovState. | Selects only salient objects/features/relations, discarding pixel-level detail. |
| consider / world | InteractionRule | A learned rule mapping a triggering configuration and move to the resulting state change. | confidence weights the rule during prediction; refined from TurnRecords. |
| consider / world | MarkovState | An abstracted, hashable game state: salient objects keyed by role plus the relations that hold. | Hashability lets the planner memoise look-ahead over states. |
| consider / goal | GoalPatterns | Prior templates over object roles and relations, instantiated into concrete GoalPredicates. | A baked-in prior: not learned per game, it seeds goal hypotheses. |
| input | TurnRecord | Record of one played turn: the move that was issued and the frames observed in response. | The raw evidence the world model and rules learn from. |
| input | Probe | A trial set of moves issued specifically to learn the environment's response. | Exploration device; its expected_observation is compared against what actually happened. |
| output | GameMove | A single intended game action with its kind and optional parameters (e.g. coordinates). | Internal representation; translated to a raw Action at the API boundary. |
| output | Action | The raw ARC action at the external API boundary (an enum, or an x,y coordinate). | Boundary type. GameIO translates a GameMove into this external encoding. |
| vocabulary | GameObject | A game-world object: its cells, optional sub-part composition, and its feature profile. | Composite: parts are themselves GameObjects. |
| vocabulary | Profile | A per-object feature profile: a map from dimension id to a (value, confidence) pair. | render() turns the profile into a human-readable name via the Lexicon. |
| vocabulary | Lexicon | The vocabulary of dimensions and relations, split into a base (long-term) and an overlay (working memory). | extend() adds game-specific features to the overlay without touching the base. |
| vocabulary | Dimension | A unary feature: a detector mapping a single object to a value over a domain. | rank orders dimensions by salience/usefulness. |
| vocabulary | Relation | An n-ary feature: a detector over several objects yielding a value or boolean. | arity n generalises Dimension (the unary case). |

#### Edges

| arrow | source | target | label | description | remark |
| --- | --- | --- | --- | --- | --- |
| composition | Conception | WorldModel | world | The conception owns the world model it reasons with. |  |
| composition | Conception | GoalPredicate | goal | The conception owns the goal it is trying to satisfy. |  |
| composition | Conception | GamePlan | plan | The conception owns the plan it intends to execute. |  |
| composition | WorldModel | InteractionRule | rules  1..* | The world model is composed of its learned interaction rules. |  |
| composition | WorldModel | PiStateAbstraction | abstraction  1 | The world model owns the abstraction function it uses to form states. |  |
| composition | GamePlan | Step | ordered steps  1..* | A plan is composed of an ordered list of steps. |  |
| composition | GameObject | Profile | has  1 | Each game object owns exactly one feature profile. |  |
| composition | Lexicon | Dimension | defines (unary)  * | The lexicon defines the available unary dimensions. |  |
| composition | Lexicon | Relation | defines (n-ary)  * | The lexicon defines the available n-ary relations. |  |
| aggregation | Probe | GameMove | trial moves (to LEARN)  1..* | A probe aggregates the trial moves it issues to learn. |  |
| directed_association | GamePlan | GoalPredicate | aims at | The plan is directed at satisfying the goal predicate. |  |
| directed_association | Step | GameMove | move | A step references the concrete move it will play. |  |
| directed_association | TurnRecord | GameMove | records played | A turn record references the move that was actually played. |  |
| directed_association | Profile | Dimension | value per Dimension | A profile holds one value per dimension it is measured on. |  |
| directed_association | Relation | GameObject | over (n) objects | A relation is evaluated over the game objects it relates. |  |
| dependency | GoalPatterns | GoalPredicate | instantiated into (bind roles to objects) | Goal patterns are instantiated into concrete goal predicates by binding roles to objects. |  |
| dependency | Step | MarkovState | expect (predicted) | A step depends on the predicted Markov state it expects to reach. |  |
| dependency | Action | GameMove | external encoding; GameIO translates | An action is the external encoding a game move is translated into. |  |
| dependency | PiStateAbstraction | MarkovState | maps Frame to MarkovState | The abstraction depends on MarkovState as the type it produces. |  |
| dependency | InteractionRule | MarkovState | (MarkovState, GameMove) to next | An interaction rule maps a state and move to the next state. |  |
| dependency | InteractionRule | Relation | triggers on / sets relations | Rules trigger on, and assert, relations between objects. |  |
| dependency | GoalPredicate | MarkovState | tests (win?) | A goal predicate is tested against a Markov state to decide a win. |  |
| dependency | GoalPredicate | GameObject | conditions over objects | Goal conditions are quantified over game objects. |  |
| dependency | GoalPredicate | Relation | tests relations | Goal conditions test relations among objects. |  |
| dependency | WorldModel | GameObject | models object dynamics | The world model depends on game objects whose dynamics it models. |  |
| dependency | PiStateAbstraction | GameObject | abstracts salient objects | The abstraction selects and abstracts the salient game objects. |  |
