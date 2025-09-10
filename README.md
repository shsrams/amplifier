# Amplifier: Supercharged AI Development Environment

> "I have more ideas than time to try them out" — The problem we're solving

> [!CAUTION]
> This project is a research demonstrator. It is in early development and may change significantly. Using permissive AI tools in your repository requires careful attention to security considerations and careful human supervision, and even then things can still go wrong. Use it with caution, and at your own risk.

## The Real Power

**Amplifier isn't just another AI tool - it's a complete environment built on top of the plumbing of Claude Code that turns an already helpful assistant into a force multiplier that can actually deliver complex solutions with minimal hand-holding.**

Most developers using vanilla Claude Code hit the same walls:

- AI lacks context about your specific domain and preferences
- You repeat the same instructions over and over
- Complex tasks require constant guidance and correction
- AI doesn't learn from previous interactions
- Parallel exploration is manual and slow

**Amplifier changes this entirely.** By combining knowledge extraction, specialized sub-agents, custom hooks, and parallel worktrees, we've created an environment where Amplifier can:

- Draw from your curated knowledge base instantly
- Deploy specialized agents for specific tasks
- Work on multiple approaches simultaneously
- Learn from your patterns and preferences
- Execute complex workflows with minimal guidance

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js (for Claude CLI)
- VS Code (recommended)

NOTE: The development of this work has been done in a Windows WSL2 environment. While it should work on macOS and Linux, Windows WSL2 is the primary supported platform at this time and you may encounter issues on other OSes.

### Installation

```bash
# Clone and setup
git clone https://github.com/microsoft/amplifier.git
cd amplifier
make install

# Configure data directories (optional - has sensible defaults)
cp .env.example .env
# Edit .env to customize data locations if needed

# Now use Amplifier in this supercharged environment
# It has access to:
# - Our opinionated best-practice patterns and philosophies
# - 20+ specialized sub-agents
# - Custom automation hooks
# - Parallel experimentation tools
```

## How to Actually Use This

### Use Amplifier in This Environment

Now when you work with Amplifier in this repo, it automatically has:

- **Contextual Knowledge**: All extracted insights from your articles
- **Specialized Agents**: Call on experts for specific tasks
- **Automation**: Hooks that enforce quality and patterns
- **Memory**: System learns from interactions (coming soon)

### Using Amplifier with External Repositories

To use Amplifier's capabilities with a different repository:

```bash
# Start Amplifier with your external repo
claude --add-dir /path/to/your/repo

# In your initial message, tell Claude:
"I'm working in /path/to/your/repo which doesn't have Amplifier files.
Please cd to that directory and work there.
Do NOT update any issues or PRs in the Amplifier repo."

# Claude will have access to Amplifier's knowledge and agents
# while working in your external repository
```

This lets you leverage Amplifier's AI enhancements on any codebase without mixing the files.

### Parallel Development with Worktrees

```bash
# Spin up parallel development branches
make worktree feature-auth    # Creates isolated environment for auth work
make worktree feature-api     # Separate environment for API development

# Each worktree gets its own:
# - Git branch
# - VS Code instance
# - Amplifier context
# - Independent experiments
```

Now you can have multiple Amplifier instances working on different features simultaneously, each with full access to your knowledge base.

### Enhanced Status Line (Optional)

Amplifier includes an enhanced status line for Claude Code that shows model info, git status, costs, and session duration:

![Status Line Example: ~/repos/amplifier (main → origin) Opus 4.1 💰$4.67 ⏱18m]

To enable it, run `/statusline` in Amplifier and reference the example script:

```
/statusline use the script at .claude/tools/statusline-example.sh
```

Amplifier will customize the script for your OS and environment. The status line displays:

- Current directory and git branch/status
- Model name with cost-tier coloring (red=high, yellow=medium, blue=low)
- Running session cost and duration

See `.claude/tools/statusline-example.sh` for the full implementation.

## What Makes This Different

### Supercharged Claude Code

- **Leverages the Power of Claude Code**: Built on top of the features of Claude Code, with a focus on extending the capabilities specifically for developers, from our learnings, opinionated patterns, philosophies, and systems we've developed over years of building with LLM-based AI tools.
- **Pre-loaded Context**: Amplifier starts with the provided content and configuration
- **Specialized Sub-Agents**: 20+ experts for different tasks (architecture, debugging, synthesis, etc.)
- **Smart Defaults**: Hooks and automation enforce your patterns
- **Parallel Work**: Multiple Amplifier instances working simultaneously

### Your Knowledge, Amplified (optional: not recommended at this time, to be replaced with multi-source)

- **Content Integration**: Extracts knowledge from your content files
- **Concept Mining**: Identifies key ideas and their relationships
- **Pattern Recognition**: Finds trends across sources
- **Contradiction Detection**: Identifies conflicting advice

#### Knowledge Base Setup (Optional)

NOTE: This is an experimental feature that builds a knowledge base from your content files. It is recommended only for advanced users willing to roll up their sleeves.

To build a knowledge base from your content collection:

1. Place content files in configured directories (see AMPLIFIER_CONTENT_DIRS in .env)
   This opens a browser to log in and authorize access.
2. Update the knowledge base:
   ```bash
   make knowledge-update
   ```

This processes all articles in your reading list, extracting concepts, relationships, and patterns.

This can take some time depending on the number of articles.

#### Querying the Knowledge Base

```bash
# Query your knowledge base directly
make knowledge-query Q="authentication patterns"

# Amplifier can reference this instantly:
# - Concepts with importance scores
# - Relationships between ideas
# - Contradictions to navigate
# - Emerging patterns
```

### Not Locked to Any AI

**Important**: We're not married to Claude Code. It's just the current best tool. When something better comes along (or we build it), we'll switch. The knowledge base, patterns, and workflows are portable.

## Current Capabilities

### AI Enhancement

- **Sub-Agents** (`.claude/agents/`):
  - `zen-code-architect` - Implements with ruthless simplicity
  - `bug-hunter` - Systematic debugging
  - `synthesis-master` - Combines analyses
  - `insight-synthesizer` - Finds revolutionary connections
  - [20+ more specialized agents]

### Development Amplification

- **Parallel Worktrees**: Multiple independent development streams
- **Automated Quality**: Hooks enforce patterns and standards

## 🔮 Vision

We're building toward a future where:

1. **You describe, AI builds** - Natural language to working systems
2. **Parallel exploration** - Test 10 approaches simultaneously
3. **Knowledge compounds** - Every project makes the next one easier
4. **AI handles the tedious** - You focus on creative decisions

See [AMPLIFIER_VISION.md](AMPLIFIER_VISION.md) for the complete vision.

## ⚠️ Important Notice

**This is an experimental system. _We break things frequently_.**

- Not accepting contributions (fork and experiment)
- No stability guarantees
- Pin commits if you need consistency
- This is a learning resource, not production software

## Technical Setup

### External Data Directories

Amplifier now supports external data directories for better organization and sharing across projects. Configure these in your `.env` file or as environment variables:

```bash
# Where to store processed/generated data (knowledge graphs, indexes, etc.)
AMPLIFIER_DATA_DIR=~/amplifier/data           # Default: .data

# Where to find content files to process
# Comma-separated list of directories to scan for content
AMPLIFIER_CONTENT_DIRS=ai_context, ~/amplifier/content  # Default: ai_context
```

**Benefits of external directories:**

- Can mount cloud storage for cross-device sync (e.g., OneDrive)
- Alternatively, store in a private repository
- Keep data separate from code repositories
- Share knowledge base across multiple projects
- Centralize content from various sources
- Avoid checking large data files into git

### Data Structure

The directory layout separates content from processed data:

```
~/amplifier/                  # Your configured AMPLIFIER_DATA_DIR parent
├── data/                       # Processed/generated data
│   ├── knowledge/              # Knowledge extraction results
│   │   ├── concepts.json       # Extracted concepts
│   │   ├── relationships.json  # Concept relationships
│   │   └── spo_graph.json      # Subject-predicate-object graph
│   └── indexes/                # Search indexes
└── content/                    # Raw content sources
    └── content/                # Content files from configured directories
        ├── articles/           # Downloaded articles
        └── lists/              # Reading lists

Your project directory:
├── .env                        # Your environment configuration
├── CLAUDE.md                   # Local project instructions
└── ... (your code)             # Separate from data
```

**Note:** The system remains backward compatible. If no `.env` file exists, it defaults to using `.data` in the current directory.

## Typical Workflow

1. **(Optional, to be replaced with an improved version soon, not recommended yet) Build your knowledge base**

   If you have a curated set of content files (suppoorts _.md, _.txt, \*.json located within AMPLIFIER_CONTENT_DIRS):

   ```bash
   make knowledge-update    # Extract concepts and patterns
   ```

   This populates the knowledge base Amplifier can reference.

2. **Start Amplifier in this environment**

   - It now has access to all your extracted knowledge
   - Can deploy specialized sub-agents
   - Follows your established patterns

3. **Give high-level instructions**

   ```
   "Build an authentication system using patterns from our knowledge base"
   ```

   Amplifier will:

   - Query relevant patterns from your articles
   - Deploy appropriate sub-agents
   - Build solution following your philosophies
   - Handle details with minimal guidance

4. **Run parallel experiments** (optional)
   ```bash
   make worktree auth-jwt
   make worktree auth-oauth
   ```
   Test multiple approaches simultaneously

## Current Limitations

- Knowledge extraction processes content from configured directories
- Some extraction features require Claude Code environment
- ~10-30 seconds per article processing
- Memory system still in development

_"The best AI system isn't the smartest - it's the one that makes YOU most effective."_

---

## Contributing

> [!NOTE]
> This project is not currently accepting contributions and suggestions - stay tuned though, as we are actively exploring ways to open this up in the future. In the meantime, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
