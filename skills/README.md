# Skills & MCP Setup Guide

## Overview
This directory contains custom skills and MCP (Model Context Protocol) server configurations for the Item Management System.

## Skills

Skills are specialized workflows for common development tasks. Each skill file provides detailed instructions, triggers, and best practices.

### Available Skills

| Skill | Trigger | Description |
|--------|----------|-------------|
| `/frontend-test` | "test frontend", "frontend tests" | Frontend testing with Jest, Cypress, or Playwright |
| `/db-migrate` | "migrate", "database migration" | Database schema migration for PostgreSQL/MongoDB |
| `/api-docs` | "generate api docs", "swagger" | Generate OpenAPI/Swagger documentation from Flask routes |
| `/docker-dev` | "docker setup", "container dev" | Docker development environment setup and management |
| `/profile` | "profile", "performance", "optimize" | Python/Flask performance profiling and optimization |
| `/security-audit` | "security scan", "vulnerability" | Security vulnerability scanning and remediation |
| `/backup` | "backup", "database backup" | Database backup and restore procedures |
| `/monitor` | "setup logging", "monitoring" | Application logging setup and monitoring |
| `/email-test` | "test email", "email notification" | Email notification testing and debugging |
| `/pwa-dev` | "pwa", "offline", "service worker" | Progressive Web App development and testing |

### Using Skills

To use a skill, mention it in your request:

```
"Test the frontend with /frontend-test skill"
```

The skill will provide:
- Detailed workflow instructions
- Tool requirements
- MUST DO / MUST NOT DO guidelines
- Context and examples
- Checklist for completion

## MCP Servers

MCP (Model Context Protocol) servers provide enhanced capabilities to the AI assistant.

### Configured MCP Servers

| Server | Command | Purpose |
|---------|----------|---------|
| **PostgreSQL** | `npx -y @modelcontextprotocol/server-postgres` | Direct PostgreSQL database queries |
| **MongoDB** | `npx -y @modelcontextprotocol/server-mongodb` | Direct MongoDB database queries |
| **Git** | `npx -y @modelcontextprotocol/server-git` | Git operations and version control |
| **Docker** | `npx -y @modelcontextprotocol/server-docker` | Docker container and image management |
| **Brave Search** | `npx -y @modelcontextprotocol/server-brave-search` | Web search capabilities |
| **Puppeteer** | `npx -y @modelcontextprotocol/server-puppeteer` | Browser automation and testing |

### MCP Configuration

MCP servers are configured in: `~/.config/claude/mcp_servers.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:password@localhost:5432/itemman"]
    },
    "mongodb": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-mongodb", "mongodb://user:password@localhost:27017/myDB"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "/Users/guantou/Desktop/Item-Manage-System"]
    },
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"]
    },
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

### Installing MCP Servers

1. Ensure Node.js is installed:
```bash
node --version  # Should be v18+
```

2. MCP servers are automatically installed via npx when first used

3. Verify configuration:
```bash
cat ~/.config/claude/mcp_servers.json
```

### Updating Connection Strings

Update the MCP configuration with your actual database credentials:

**PostgreSQL:**
```json
"postgresql://user:password@localhost:5432/itemman"
```

Replace with:
- `user` - Your PostgreSQL username
- `password` - Your PostgreSQL password
- `localhost:5432` - Your PostgreSQL host and port
- `itemman` - Your database name

**MongoDB:**
```json
"mongodb://user:password@localhost:27017/myDB"
```

Replace with:
- `user` - Your MongoDB username (if auth enabled)
- `password` - Your MongoDB password (if auth enabled)
- `localhost:27017` - Your MongoDB host and port
- `myDB` - Your database name

### Using MCP Servers

Once configured, you can use MCP servers in your requests:

```
"Query the PostgreSQL database for all items"
"Check the MongoDB logs for errors"
"List recent Git commits"
"Show running Docker containers"
```

## Getting Started

### 1. Skills
```
"Use /db-migrate to add a new field to the Item model"
"Generate API docs with /api-docs skill"
"Run security audit with /security-audit skill"
```

### 2. MCP Servers
```
"Connect to PostgreSQL and show all users"
"Query MongoDB for items expiring soon"
"Check Docker container status"
"Search the web for Flask best practices"
```

## Troubleshooting

### MCP Server Not Connecting

**Issue:** "PostgreSQL MCP server not responding"

**Solutions:**
1. Check database is running:
```bash
docker compose ps db
```

2. Verify connection string in `~/.config/claude/mcp_servers.json`
3. Check database credentials
4. Ensure firewall allows connection

### Skill Not Working

**Issue:** "Skill not triggering"

**Solutions:**
1. Use exact trigger phrase from skill file
2. Check skill file exists in `skills/` directory
3. Verify skill syntax is correct

### NPM Installation Issues

**Issue:** "npx command not found"

**Solutions:**
1. Install Node.js:
```bash
# macOS with Homebrew
brew install node

# Or download from nodejs.org
```

2. Verify installation:
```bash
node --version
npm --version
```

## Security Notes

⚠️ **Important:**

- Never commit `mcp_servers.json` to version control
- Never commit actual database credentials
- Use environment variables for sensitive data
- Update connection strings for different environments (dev/staging/prod)

## Customization

### Adding New Skills

1. Create new skill file: `skills/your-skill-name.md`
2. Follow the skill template structure
3. Update this README with new skill

### Adding New MCP Servers

1. Update `~/.config/claude/mcp_servers.json`
2. Add new server configuration
3. Test connection

### Skill Template

```markdown
# Your Skill Name

## Description
Brief description of what this skill does.

## Trigger Phrases
- "trigger phrase 1"
- "trigger phrase 2"

## When to Use
When you need to:
- Task 1
- Task 2

## Available Tools
- Tool 1
- Tool 2

## MUST DO
1. Requirement 1
2. Requirement 2

## MUST NOT DO
1. Prohibition 1
2. Prohibition 2

## Context
Context about the project.

## Workflow
Step-by-step workflow.

## Examples
Example code or commands.

## Checklist
- [ ] Item 1
- [ ] Item 2
```

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [Skills Documentation](https://github.com/opencode-protocol/skills)
- [PostgreSQL MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [MongoDB MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/mongodb)
- [Git MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/git)
- [Docker MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/docker)

## Support

For issues or questions:
1. Check the specific skill file for detailed instructions
2. Review MCP server configuration
3. Consult project documentation
4. Check system logs for error messages

---

**Last Updated:** 2024-01-08
