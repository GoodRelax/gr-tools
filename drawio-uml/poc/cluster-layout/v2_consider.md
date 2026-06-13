#### Nodes

| cluster | name | description | remark |
| --- | --- | --- | --- |
|  | Conception | The agent's current working hypothesis for a turn: bundles the world model, the goal, and the plan. | Stereotype 'answer'. Lifecycle via status: active -> committed -> retired; score ranks competing conceptions. |
| world | WorldModel | Models the game's dynamics: a set of interaction rules plus the state-abstraction function. | impl may be Symbolic, Learned, or Graph; predict() drives look-ahead during planning. |
| goal | GoalPredicate | Expresses a win or sub-goal condition as a composable predicate over objects and relations. | Composable via kind (Atom/AND/OR/SEQUENCE); children are ordered only for SEQUENCE. |
| plan | GamePlan | An ordered sequence of steps toward the goal, bounded by a planning horizon. | Re-planned when the world model or goal changes. |
| plan | Step | One planned move plus its expected resulting state and the sub-goal it serves. | Value object: a step is compared by content, not identity. |
| world | PiStateAbstraction | The abstraction function (pi) that projects a raw Frame into an abstract MarkovState. | Selects only salient objects/features/relations, discarding pixel-level detail. |
| world | InteractionRule | A learned rule mapping a triggering configuration and move to the resulting state change. | confidence weights the rule during prediction; refined from TurnRecords. |
| world | MarkovState | An abstracted, hashable game state: salient objects keyed by role plus the relations that hold. | Hashability lets the planner memoise look-ahead over states. |
| goal | GoalPatterns | Prior templates over object roles and relations, instantiated into concrete GoalPredicates. | A baked-in prior: not learned per game, it seeds goal hypotheses. |

#### Edges

| arrow | source | target | label | description | remark |
| --- | --- | --- | --- | --- | --- |
| composition | Conception | WorldModel | world | The conception owns the world model it reasons with. |  |
| composition | Conception | GoalPredicate | goal | The conception owns the goal it is trying to satisfy. |  |
| composition | Conception | GamePlan | plan | The conception owns the plan it intends to execute. |  |
| composition | WorldModel | InteractionRule | rules  1..* | The world model is composed of its learned interaction rules. |  |
| composition | WorldModel | PiStateAbstraction | abstraction  1 | The world model owns the abstraction function it uses to form states. |  |
| composition | GamePlan | Step | ordered steps  1..* | A plan is composed of an ordered list of steps. |  |
| directed_association | GamePlan | GoalPredicate | aims at | The plan is directed at satisfying the goal predicate. |  |
| directed_association | Step | GameMove | move | A step references the concrete move it will play. |  |
| dependency | GoalPatterns | GoalPredicate | instantiated into (bind roles to objects) | Goal patterns are instantiated into concrete goal predicates by binding roles to objects. |  |
| dependency | Step | MarkovState | expect (predicted) | A step depends on the predicted Markov state it expects to reach. |  |
| dependency | PiStateAbstraction | MarkovState | maps Frame to MarkovState | The abstraction depends on MarkovState as the type it produces. |  |
| dependency | InteractionRule | MarkovState | (MarkovState, GameMove) to next | An interaction rule maps a state and move to the next state. |  |
| dependency | InteractionRule | Relation | triggers on / sets relations | Rules trigger on, and assert, relations between objects. |  |
| dependency | GoalPredicate | MarkovState | tests (win?) | A goal predicate is tested against a Markov state to decide a win. |  |
| dependency | GoalPredicate | GameObject | conditions over objects | Goal conditions are quantified over game objects. |  |
| dependency | GoalPredicate | Relation | tests relations | Goal conditions test relations among objects. |  |
| dependency | WorldModel | GameObject | models object dynamics | The world model depends on game objects whose dynamics it models. |  |
| dependency | PiStateAbstraction | GameObject | abstracts salient objects | The abstraction selects and abstracts the salient game objects. |  |
