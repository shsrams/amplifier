# Amazon Q Migration Plan: Porting security-guardian Agent

## Overview
Port Amplifier's `security-guardian` agent to work with Amazon Q Developer using `.amazonq/` directory structure with self-contained MCP server configuration.

## Directory Structure
```
amplifier/
├── .claude/                    # Existing Claude Code setup
├── .amazonq/                   # New Amazon Q setup
│   ├── agents/                 # Q agent JSON configurations
│   ├── tools/                  # Q-specific automation scripts
│   └── README.md               # Q usage guide
├── ai_context/                 # Shared philosophy files
└── shared resources...
```

## Phase 1: Setup .amazonq Structure

### 1.1 Create Base Structure
```bash
mkdir -p .amazonq/{agents,tools}
```

### 1.2 Q Agent Configuration Format
**Key Finding**: Q agents use JSON configuration with built-in MCP server definitions - completely self-contained!

## Phase 2: Port security-guardian Agent

### 2.1 Q Agent Configuration Template
```json
{
  "name": "security-guardian",
  "description": "Specialized security analysis agent for defensive security tasks only",
  "prompt": "[Extracted security-guardian methodology]",
  "mcpServers": {
    "fetch": {
      "command": "fetch-mcp-server",
      "args": ["--timeout", "10"],
      "timeout": 30000
    },
    "brave": {
      "command": "brave-search-mcp-server", 
      "args": [],
      "timeout": 30000
    }
  },
  "tools": [
    "fs_read", "fs_write", "execute_bash", "use_aws", "todo_list",
    "@fetch/fetch", "@brave/brave_web_search"
  ],
  "allowedTools": ["fs_read", "todo_list", "use_aws"],
  "toolsSettings": {
    "use_aws": {
      "allowedServices": ["iam", "s3", "ec2", "cloudtrail", "guardduty", "securityhub"]
    }
  },
  "resources": [
    "file://ai_context/IMPLEMENTATION_PHILOSOPHY.md",
    "file://ai_context/MODULAR_DESIGN_PHILOSOPHY.md"
  ]
}
```

### 2.2 Tool Mapping Strategy
- **WebFetch → @fetch/fetch** (via MCP server)
- **TodoWrite → todo_list** (built-in Q tool)
- **Web research → @brave/brave_web_search** (via MCP server)
- **AWS security → use_aws** (built-in with service restrictions)
- **Philosophy context → resources** (auto-loaded files)

### 2.3 Advantages of Q's Approach
- **Self-contained**: Agent defines its own MCP dependencies
- **Portable**: No external MCP configuration needed
- **Secure**: Tool permissions and service restrictions built-in
- **Context-aware**: Automatic philosophy file loading

## Phase 3: Implementation Steps

### 3.1 Extract security-guardian Core
1. **Source**: `.claude/agents/security-guardian.md`
2. **Extract system prompt** - Remove Claude Code metadata
3. **Preserve methodology** - Keep security analysis framework
4. **Add AWS enhancements** - Leverage native AWS security tools

### 3.2 Create Q Configuration
1. **File**: `.amazonq/agents/security-guardian.json`
2. **Include MCP servers** - Self-contained tool dependencies
3. **Set permissions** - AWS security services only
4. **Auto-load context** - Philosophy files via resources

### 3.3 Test Security Analysis
1. **Code security review** - Test on vulnerable code samples
2. **AWS security analysis** - Test with AWS configurations
3. **MCP tool integration** - Verify fetch and search capabilities
4. **Permission validation** - Ensure security-only operations

## Phase 4: Benefits of This Approach

### 4.1 Enhanced Capabilities
- **AWS-native security**: Direct integration with AWS security services
- **Self-configuring**: No manual MCP server setup required
- **Comprehensive tooling**: Web research + AWS analysis + file operations
- **Context preservation**: Automatic philosophy loading

### 4.2 Shared Resources Strategy
- **Philosophy files**: Single source in `ai_context/` (auto-loaded)
- **Project context**: AGENTS.md works for both environments
- **Security methodology**: Consistent across Claude and Q versions

## Phase 5: Scaling Pattern

### 5.1 Template for Other Agents
The security-guardian configuration provides a template for porting other agents:
- JSON configuration with MCP servers
- Tool mapping and permissions
- Resource auto-loading
- AWS service integration

### 5.2 Next Agents to Port
1. **bug-hunter** - Debugging with AWS CloudWatch integration
2. **zen-architect** - Architecture design with AWS Well-Architected
3. **modular-builder** - Implementation with AWS deployment tools

## Success Criteria
- [ ] security-guardian works effectively in Q environment
- [ ] Self-contained with MCP server configuration
- [ ] Maintains defensive security focus
- [ ] Integrates seamlessly with AWS security services
- [ ] Provides scalable pattern for other agent ports
- [ ] Auto-loads shared philosophy context
