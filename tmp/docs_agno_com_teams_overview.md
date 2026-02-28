A Team is a collection of agents (or sub-teams) that work together. The team leader delegates tasks to members based on their roles.
Copy
Ask AI
```
from agno.team import Team
from agno.agent import Agent

team = Team(members=[
    Agent(name="English Agent", role="You answer questions in English"),
    Agent(name="Chinese Agent", role="You answer questions in Chinese"),
    Team(
        name="Germanic Team",
        role="You coordinate the team members to answer questions in German and Dutch",
        members=[
            Agent(name="German Agent", role="You answer questions in German"),
            Agent(name="Dutch Agent", role="You answer questions in Dutch"),

```

##  Why Teams?
Single agents hit limits fast. Context windows fill up, decision-making gets muddy, debugging becomes impossible. Teams distribute work across specialized agents:
Benefit | Description
---|---
Specialization | Each agent masters one domain instead of being mediocre at everything
Parallel processing | Multiple agents work simultaneously on independent subtasks
Maintainability | When something breaks, you know exactly which agent to fix
Scalability | Add capabilities by adding agents, not rewriting everything
The tradeoff: coordination overhead. Agents need to communicate and share state. Get this wrong and you’ve built a more expensive failure mode.

##  When to Use Teams
**Use a team when:**
  * A task requires multiple specialized agents with different tools or expertise
  * A single agent’s context window gets exceeded
  * You want each agent focused on a narrow scope

**Use a single agent when:**
  * The task fits one domain of expertise
  * Minimizing token costs matters
  * You’re not sure yet (start simple, add agents when you hit limits)

##  What’s New?
Team execution is modular. Message building, session handling, storage, and background managers are separated into dedicated components so coordination logic can evolve without changing the Team API. Additional Team 2.0 updates include approvals for human-in-the-loop workflows, cron-based scheduling for teams, improved HITL requirements, and LearningMachine support for persistent learning.

##  Team Modes
Team 2.0 introduces `TeamMode` to make collaboration styles explicit. Prefer `mode=` instead of toggling `respond_directly` or `delegate_to_all_members` directly.
Copy
Ask AI
```
from agno.team import Team, TeamMode

team = Team(
    name="Research Team",
    members=[...],
    mode=TeamMode.broadcast,

Mode | Configuration | Use case
---|---|---
**Coordinate** |  `mode=TeamMode.coordinate` (default) | Decompose work, delegate to members, synthesize results
**Route** | `mode=TeamMode.route` | Route to a single specialist and return their response directly
**Broadcast** | `mode=TeamMode.broadcast` | Delegate the same task to all members and synthesize
**Tasks** | `mode=TeamMode.tasks` | Manage a shared task list and loop until the goal is complete
See [Delegation](https://docs.agno.com/teams/delegation) for details.

##  Guides

## [Build Teams Define members, roles, and structure. ](https://docs.agno.com/teams/building-teams)## [Run Teams Execute teams and handle responses. ](https://docs.agno.com/teams/running-teams)## [Debug Teams Inspect and troubleshoot team behavior. ](https://docs.agno.com/teams/debugging-teams)

##  Resources

## [Build Teams Define members, roles, and structure. ](https://docs.agno.com/teams/building-teams)## [Run Teams Execute teams and handle responses. ](https://docs.agno.com/teams/running-teams)## [Debug Teams Inspect and troubleshoot team behavior. ](https://docs.agno.com/teams/debugging-teams)
Define members, roles, and structure.
Execute teams and handle responses.
Inspect and troubleshoot team behavior.
A Team is a collection of agents (or sub-teams) that work together. The team leader delegates tasks to members based on their roles.
Copy
Ask AI
```
from agno.team import Team
from agno.agent import Agent

Was this page helpful?
[Suggest edits](https://github.com/agno-agi/docs/edit/main/teams/overview.mdx)[Raise issue](https://github.com/agno-agi/docs/issues/new?title=Issue%20on%20docs&body=Path:%20/teams/overview)
[Agent with Knowledge](https://docs.agno.com/agents/usage/agent-with-knowledge)[Building Teams](https://docs.agno.com/teams/building-teams)
Ctrl+I