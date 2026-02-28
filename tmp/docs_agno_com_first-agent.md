In this guide, you’ll build an agent that:
  * Connects to an MCP server
  * Stores and retrieves past conversations
  * Runs as a production API

All in about 20 lines of code.

##  1. Define the Agent
Save the following code as `agno_assist.py`:
agno_assist.py
Copy
Ask AI
```
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.os import AgentOS
from agno.tools.mcp import MCPTools

agno_assist = Agent(
    name="Agno Assist",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"# session storage
    tools=[MCPTools(url="https://docs.agno.com/mcp")],  # Agno docs via MCP
    add_datetime_to_context=True,
    add_history_to_context=True# include past runs
    num_history_runs=3# last 3 conversations
    markdown=True,

# Serve via AgentOS → streaming, auth, session isolation, API endpoints
agent_os = AgentOS(agents=[agno_assist], tracing=True)
app = agent_os.get_app()

```

You now have:
  * A stateful agent
  * Streaming responses
  * Per-user session isolation
  * A production-ready API
  * Tracing enabled out of the box

No 3rd-party services required

##  2. Run Your AgentOS
Set up your virtual environment
Windows
Copy
Ask AI
```
uv venv --python 3.12
source .venv/bin/activate

Install dependencies
Copy
Ask AI
```
uv pip install -U 'agno[os]' anthropic mcp

Export your Anthropic API key
Windows
Copy
Ask AI
```
export ANTHROPIC_API_KEY=sk-***

Run your AgentOS
Copy
Ask AI
```
fastapi dev agno_assist.py

Your AgentOS is now running at:`http://localhost:8000`API documentation is automatically available at:`http://localhost:8000/docs`
You can add your own routes, middleware, or any FastAPI feature on top.

##  3. Connect to the AgentOS UI
The [AgentOS UI](https://os.agno.com) connects directly from your browser to your runtime. It lets you test, monitor, and manage your agents in real time.
  1. Open [os.agno.com](https://os.agno.com) and sign in.
  2. Click **“Add new OS”** in the top navigation.
  3. Select **“Local”** to connect to a local AgentOS.
  4. Enter your endpoint URL (default: `http://localhost:8000`).
  5. Name it something like “Development OS”.
  6. Click **“Connect”**.

You’ll see your OS with a live status indicator once connected.

##  Chat with your Agent
Open Chat, select your agent, and ask:
> What is Agno?
The agent retrieves context from the Agno MCP server and responds with grounded answers.
Click Sessions in the sidebar to inspect stored conversations.All session data is stored in your local database. No third-party tracing or hosted memory service is required.

##  What You Just Built
In 20 lines, you built:
  * A stateful agent
  * Tool-augmented retrieval via MCP
  * A streaming API
  * Session isolation
  * A production-ready runtime

You can use this exact same architecture for running multi-agent systems in production.

##  Next
  * [Deploy AgentOS to your cloud →](https://docs.agno.com/deploy/introduction)
  * [Browse 2000+ code examples →](https://docs.agno.com/examples/introduction)

No 3rd-party services required
Set up your virtual environment
Windows
Copy
Ask AI
```
uv venv --python 3.12
source .venv/bin/activate

Your AgentOS is now running at:`http://localhost:8000`API documentation is automatically available at:`http://localhost:8000/docs`
Click Sessions in the sidebar to inspect stored conversations.All session data is stored in your local database. No third-party tracing or hosted memory service is required.
In this guide, you’ll build an agent that:
  * Connects to an MCP server
  * Stores and retrieves past conversations
  * Runs as a production API

Was this page helpful?
[Suggest edits](https://github.com/agno-agi/docs/edit/main/first-agent.mdx)[Raise issue](https://github.com/agno-agi/docs/issues/new?title=Issue%20on%20docs&body=Path:%20/first-agent)
[Introduction](https://docs.agno.com/introduction)[What are Agents?](https://docs.agno.com/agents/overview)
Ctrl+I