# GR-ARC-3 Agent Lifecycle (state machine)

## Nodes

| cluster | name | description | remark |
| --- | --- | --- | --- |
|  | boot |  |  |
|  | Loading | AssetLoader loads the baked deck (LTM: Lexicon.base / GoalPatterns / role priors), read-only. WM empty. |  |
|  | NewGame | Receive the first frame; init working memory (cleared per game). |  |
|  | s_init |  |  |
|  | Explore | perceive: probing actions, collect TurnRecord/Probe, segment objects. |  |
| consider | c_init |  |  |
| consider | ModelWorld | induce/refine WorldModel (InteractionRule, StateAbstraction); verified free on the in-house sim. |  |
| consider | ModelGoal | infer GoalPredicate (GoalPatterns instantiate + first-win bootstrap). |  |
| consider / plan | p_init |  |  |
| consider / plan | Simulate | predict one step via WorldModel.predict (in-house sim) -- RHAE-free look-ahead. |  |
| consider / plan | Evaluate | goal-test + heuristic; expand the search, or stop when a winning line is found. |  |
|  | Execute | act: MPC -- commit ONE GameMove -> Action (the only RHAE cost); observe. |  |
|  | Diagnose | check prediction vs observation at the first divergence; route back to the wrong layer (re-explore / re-model / re-plan). |  |
|  | LevelCleared | Outcome=win; carry-forward the WorldModel to the next level. |  |
|  | GameOver | Outcome=over (lives out). |  |
|  | Done | is_done: scorecard exhausted / wall-clock out. (next game -> NewGame, omitted.) |  |
|  | end |  |  |

## Edges

| arrow | source | target | label | description | remark |
| --- | --- | --- | --- | --- | --- |
| transition | boot | Loading |  |  |  |
| transition | Loading | NewGame | loaded |  |  |
| transition | NewGame | solving | first frame |  |  |
| transition | s_init | Explore |  |  |  |
| transition | Explore | consider | enough signal |  |  |
| transition | c_init | ModelWorld |  |  |  |
| transition | ModelWorld | ModelGoal |  |  |  |
| transition | ModelGoal | plan | goal set |  |  |
| transition | p_init | Simulate |  |  |  |
| transition | Simulate | Evaluate | predict |  |  |
| transition | Evaluate | Simulate |  |  |  |
| transition | plan | Execute | plan found |  |  |
| transition | Execute | Diagnose | observe |  |  |
| transition | Diagnose | consider | re-model / re-plan |  |  |
| transition | solving | LevelCleared | win |  |  |
| transition | solving | GameOver | over |  |  |
| transition | LevelCleared | solving | next level (carry WM) |  |  |
| transition | LevelCleared | Done | all cleared |  |  |
| transition | GameOver | Done | no lives |  |  |
| transition | Done | end |  |  |  |

## Clusters

| cluster | label | description | remark |
| --- | --- | --- | --- |
| solving | Solving - gated solve loop (per level; Execute = the only RHAE cost) |  |  |
| solving / consider | Consider - build the Conception (multi-solution) |  |  |
| solving / consider / plan | Plan - look-ahead on in-house sim (RHAE-free) |  |  |
