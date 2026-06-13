#### Nodes

| cluster | name | description | remark |
| --- | --- | --- | --- |
|  | Conception | The agent's current working hypothesis for a turn: bundles the world model, the goal, and the plan. | Stereotype 'answer'. Lifecycle via status: active -> committed -> retired; score ranks competing conceptions. |
| world | WorldModel | Models the game's dynamics: a set of interaction rules plus the state-abstraction function. | impl may be Symbolic, Learned, or Graph; predict() drives look-ahead during planning. |
| goal | GoalPredicate | Expresses a win or sub-goal condition as a composable predicate over objects and relations. | Composable via kind (Atom/AND/OR/SEQUENCE); children are ordered only for SEQUENCE. |
| plan | GamePlan | An ordered sequence of steps toward the goal, bounded by a planning horizon. | Re-planned when the world model or goal changes. |
| plan | Step | One planned move plus its expected resulting state and the sub-goal it serves. | Value object: a step is compared by content, not identity. |

#### Edges

| arrow | source | target | label | description | remark |
| --- | --- | --- | --- | --- | --- |
| composition | Conception | WorldModel | world | The conception owns the world model it reasons with. |  |
| composition | Conception | GoalPredicate | goal | The conception owns the goal it is trying to satisfy. |  |
| composition | Conception | GamePlan | plan | The conception owns the plan it intends to execute. |  |
| composition | GamePlan | Step | ordered steps  1..* | A plan is composed of an ordered list of steps. |  |
| directed_association | GamePlan | GoalPredicate | aims at | The plan is directed at satisfying the goal predicate. |  |
