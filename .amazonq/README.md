# Amazon Q Developer Agent Configuration

This directory contains Amplifier agents ported to work with Amazon Q Developer using self-contained MCP server configurations.

## Directory Structure

```
.amazonq/
├── agents/                     # Q agent configurations
│   ├── security-guardian.json  # Security analysis agent
│   └── security-guardian.md    # Agent prompt definition
├── tools/                      # Q-specific automation scripts
└── README.md                   # This file
```

## Available Agents

### security-guardian

**Purpose**: Specialized security analysis agent for defensive security tasks only

**Use Cases**:
- Security reviews and vulnerability assessments
- Pre-deployment security checks
- Authentication/authorization implementation reviews
- OWASP Top 10 analysis
- Secret detection and validation
- Input/output security validation
- Data protection measures verification

**Enhanced Capabilities**:
- **AWS Security Integration**: Direct access to AWS security services (IAM, GuardDuty, Security Hub, etc.)
- **Web Research**: Integrated Brave search for security intelligence
- **File Operations**: Comprehensive file system access for code analysis
- **Security Tools**: Built-in support for security scanning tools

**Tool Mapping from Claude Code**:
- `WebFetch` → `fetch/fetch` (via MCP server)
- `TodoWrite` → `todo_list` (built-in Q tool)
- `WebSearch` → `brave_web_search/brave_web_search` (via MCP server)
- `Bash` → `execute_bash` (with security tool restrictions)
- New: `use_aws` (AWS security services integration)

## Usage with Amazon Q

### Prerequisites

1. **MCP Servers**: The agents use self-contained MCP server definitions
   - `@modelcontextprotocol/server-fetch` for web fetching
   - `@modelcontextprotocol/server-brave-search` for web search

2. **AWS Configuration**: Ensure AWS credentials are configured for security service access

### Using from Your Project

**Option 1: Copy agent to your project**
```bash
# Copy the agent configuration to your project
cp /path/to/amplifier/.amazonq/agents/security-guardian.* .amazonq/agents/
cp /path/to/amplifier/ai_context/*.md .amazonq/context/

# Use the agent
q chat --agent security-guardian "Review this authentication implementation"
```

**Option 2: Reference Amplifier directly**
```bash
# From your project directory, reference Amplifier's agents
q chat --agent-config /path/to/amplifier/.amazonq/agents/security-guardian.json "Analyze our IAM policies"

# Or set environment variable
export Q_AGENT_PATH="/path/to/amplifier/.amazonq/agents"
q chat --agent security-guardian "Review this code for vulnerabilities"
```

**Option 3: Symlink approach**
```bash
# From your project directory, create symlink to Amplifier's Q agents
mkdir -p .amazonq
ln -s /home/ec2-user/amplifier/.amazonq/agents .amazonq/cli-agents

# Use the agent directly
q chat --agent security-guardian "Security review"

# Or within q chat with delegate feature enabled
# Run security-guardian agent
```

**Option 4: Launch with tmux**
```bash
# For background execution or session management
tmux new-window -n "security-guardian" 'q chat --agent security-guardian "Perform security review on the code in the current working directory"; exec bash'
```

### Agent Configuration Format

Q agents use JSON configuration with these key features:

- **Self-contained MCP servers**: No external MCP configuration needed
- **Tool permissions**: Granular control over allowed operations
- **Resource auto-loading**: Automatic philosophy file loading
- **AWS service restrictions**: Security-focused service access only

### Shared Resources

All agents automatically load shared philosophy files:
- `ai_context/IMPLEMENTATION_PHILOSOPHY.md` - Core development philosophy
- `ai_context/MODULAR_DESIGN_PHILOSOPHY.md` - Modular design principles

## Benefits of Q Integration

### Enhanced Security Analysis
- **AWS-native security**: Direct integration with AWS security services
- **Comprehensive tooling**: Web research + AWS analysis + file operations
- **Self-configuring**: No manual MCP server setup required

### Consistent Methodology
- **Philosophy preservation**: Same core principles as Claude version
- **Enhanced capabilities**: Additional AWS security tools
- **Portable configuration**: Self-contained agent definitions

## Migration Pattern

This security-guardian configuration provides a template for porting other Amplifier agents:

1. **Extract core prompt** from Claude agent
2. **Map tools** to Q equivalents with MCP servers
3. **Set permissions** appropriate for agent purpose
4. **Configure resources** for auto-loading context files
5. **Test functionality** with real use cases

## Security Considerations

The security-guardian agent is configured with:
- **Read-only AWS operations**: Only describe, list, get, scan, check operations allowed
- **Security tool restrictions**: Limited bash commands for security scanning only
- **Defensive focus**: Explicitly refuses malicious code assistance

## Next Steps

Future agent ports following this pattern:
- **bug-hunter**: Debugging with AWS CloudWatch integration
- **zen-architect**: Architecture design with AWS Well-Architected
- **modular-builder**: Implementation with AWS deployment tools

## Support

This is an experimental migration. The configuration format may evolve as Amazon Q Developer's agent system matures.
