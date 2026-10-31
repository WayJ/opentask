# OpenTask CLI - AI Agent Interface

A production-ready command-line interface for the OpenTask platform, optimized for both human users and AI agents.

**Version**: v1.0.6 | **Status**: Production Ready | **Python**: 3.8+

## ✨ Key Features

- 🚀 **Project Management** - Full CRUD for projects with active context tracking
- 🎯 **Issue Tracking** - Complete issue lifecycle with workflow commands
- 📋 **Requirement Management** - Requirement tracking with status transitions
- 💬 **Comment System** - Three-tier comment command structure
- 🔍 **Smart Search** - Keyword search with advanced filtering
- 👥 **Batch Operations** - Bulk assign and status updates
- 🤖 **AI-Optimized** - Standardized JSON output for agent consumption
- 🔐 **Secure Auth** - System keyring integration for credential storage
- 📊 **Rich Terminal UI** - Beautiful output with tables and status blocks
- ⚡ **Non-Interactive** - Designed for automation (no hanging prompts)

## 📦 Installation

### From Source

```bash
cd agent-harness/opentask-cli
pip install -e .
```

### Verify Installation

```bash
opentask --version
# Output: opentask v1.0.6

opentask --help
```

## ⚙️ Configuration

### Quick Setup

```bash
# Set API endpoint
opentask config set-api http://localhost:7377

# Login (credentials stored in system keyring)
opentask login

# Or set token directly
opentask config set-token YOUR_JWT_TOKEN
```

### View Configuration

```bash
opentask config show
```

Configuration is stored in:
- **Credentials**: System keyring (secure)
- **Config file**: `~/.opentask/config.json`

## 🚀 Usage

### One-Shot Commands

```bash
# Project management
opentask project list
opentask project create -n "My Project" -d "Description"
opentask project use <project-id>

# Issue management
opentask issue list --status open --priority high
opentask issue create -t "Fix login bug" --type bug --priority high
opentask issue show ISSUE-123
opentask issue assign ISSUE-123 --assignee me
opentask issue resolve ISSUE-123 --reason "Fixed"

# Requirement management
opentask requirement list --status draft
opentask requirement find "API design" --in-title
opentask requirement start REQ-123
```

### JSON Output (for AI Agents)

All commands support `--json` flag with standardized format:

```bash
opentask --json issue list --status open
opentask --json issue create -t "New issue"
opentask --json project list
```

**Standard JSON Response**:
```json
{
  "success": true,
  "data": {
    "rows": [...],
    "total": 10
  },
  "error": null,
  "message": "Operation successful"
}
```

## 📚 Command Reference

### Project Commands

```bash
opentask project list                    # List all projects
opentask project show <project-id>       # Show project details
opentask project create -n NAME [-d DESC] # Create project
opentask project update <id> [-n NAME]    # Update project
opentask project use <project-id>         # Set active project
opentask project current                  # Show active project
opentask project delete <project-id>      # Delete project
```

### Issue Commands

#### Basic Operations
```bash
opentask issue list [--status STATUS] [--priority PRIORITY] [--search KEYWORD]
opentask issue show <issue-id>
opentask issue create -t TITLE [-d DESC] [--type TYPE] [--priority PRIORITY]
opentask issue update <issue-id> [-t TITLE] [-d DESC] [-s STATUS]
opentask issue delete <issue-id>
```

#### Search & Filter
```bash
opentask issue find "keyword" [--in-title] [--in-description] [--status STATUS]
opentask issue my                         # My assigned issues
opentask issue todo                       # My TODO (open + assigned)
opentask issue in-progress                # My in-progress issues
opentask issue blocking                   # Issues blocking me
```

#### Workflow Commands
```bash
opentask issue start <issue-id>           # Start working (open → in_progress)
opentask issue resolve <issue-id> [-r REASON] [-c COMMIT-ID]
opentask issue close <issue-id> [-r REASON]
opentask issue reopen <issue-id>          # Reopen (resolved/closed → open)
```

#### Assignment
```bash
opentask issue assign <issue-id> --assignee me
opentask issue assign <issue-id> --assignee <user-id>
opentask issue assign <issue-id> --assignee none  # Unassign
opentask issue batch-assign ID1 ID2 ID3 --assignee me  # Batch assign
```

#### Comments (Three-Tier Commands)
```bash
opentask issue comment add <issue-id> "Comment text"
opentask issue comment add <issue-id> -m "Another way"
opentask issue comment list <issue-id>
opentask issue comment delete <comment-id>
```

#### Batch Operations
```bash
opentask issue batch --ids "ID1,ID2,ID3"   # Batch get issues
```

### Requirement Commands

```bash
# Basic operations (same as issue)
opentask requirement list
opentask requirement show <req-id>
opentask requirement create -t TITLE
opentask requirement update <req-id>
opentask requirement delete <req-id>

# Search
opentask requirement find "keyword" [--in-title] [--in-description]

# Workflow
opentask requirement todo
opentask requirement in-progress
opentask requirement start <req-id>
opentask requirement resolve <req-id>
opentask requirement close <req-id>
opentask requirement reopen <req-id>

# Assignment
opentask requirement assign <req-id> --assignee me
opentask requirement batch-assign ID1 ID2 --assignee <user-id>

# Set project
opentask requirement set-project <req-id> <project-id>
```

### Collection Commands

```bash
opentask collection list                  # List collections
opentask collection show <collection-id>
opentask collection create -n NAME
opentask collection update <collection-id>
opentask collection parse <collection-id>
opentask collection stats <collection-id>
opentask collection delete <collection-id>
```

### Auth Commands

```bash
opentask login                            # Login and store credentials
opentask logout                           # Logout and clear token
opentask auth me                          # Get current user info
```

### Config Commands

```bash
opentask config show                      # Show configuration
opentask config set-api <url>             # Set API URL
opentask config set-token <token>         # Set auth token
```

### Update Commands

```bash
opentask update check                     # Check for updates
opentask update install                   # Install updates
opentask update version                   # Show version
```

## 🤖 AI Agent Integration

### Agent Workflow

```bash
# 1. Configure
opentask config set-api http://localhost:7377
opentask config set-token $TOKEN

# 2. Get project ID
PROJECT_ID=$(opentask --json project list | jq -r '.data.rows[0].id')

# 3. Set active project
opentask project use $PROJECT_ID

# 4. Create issue
ISSUE=$(opentask --json issue create -t "Fix bug" | jq -r '.data.id')

# 5. Start working
opentask issue start $ISSUE

# 6. Add comment
opentask issue comment add $ISSUE "In progress"

# 7. Resolve
opentask issue resolve $ISSUE -r "Fixed the bug"

# 8. Close
opentask issue close $ISSUE -r "Verified"
```

### Standardized JSON Format

All commands return consistent JSON structure:

**Success Response**:
```json
{
  "success": true,
  "data": { /* actual data */ },
  "error": null,
  "message": "Operation successful"
}
```

**Error Response**:
```json
{
  "success": false,
  "data": null,
  "error": "Error message",
  "message": "Operation failed"
}
```

### Batch Operations

```json
{
  "success": true,
  "data": {
    "results": [
      {"issue_id": "ISSUE-1", "success": true},
      {"issue_id": "ISSUE-2", "success": false, "error": "Not found"}
    ],
    "total": 2,
    "successful": 1,
    "failed": 1
  },
  "message": "Resolved 1/2 issue(s)"
}
```

## 🏗️ Project Structure

```
agent-harness/opentask-cli/
├── opentask/                      # Main package
│   ├── __init__.py
│   ├── opentask_cli.py           # CLI entry point
│   ├── core/                      # Command modules
│   │   ├── project.py             # Project commands
│   │   ├── issue.py               # Issue commands
│   │   ├── requirement.py         # Requirement commands
│   │   ├── collection.py          # Collection commands
│   │   └── update.py              # Update commands
│   ├── utils/                     # Utilities
│   │   ├── api_client.py          # HTTP client
│   │   ├── config.py              # Config management
│   │   ├── helpers.py             # Helper functions
│   │   ├── password_store.py      # Keyring storage
│   │   ├── crypto_helper.py       # Crypto utilities
│   │   └── repl_skin.py           # Terminal UI
│   └── tests/                     # Tests
│       ├── test_core.py
│       └── test_*.py
├── setup.py                        # Package setup
├── pyproject.toml                  # Modern Python config
└── CLI_ANALYSIS_REPORT.md          # Code analysis
```

## 🔐 Security Features

- **System Keyring Integration**: Passwords stored securely in OS keyring
  - Windows: Credential Manager
  - macOS: Keychain
  - Linux: Secret Service
- **No Interactive Prompts**: All operations are non-interactive (safe for AI)
- **Token-Based Auth**: JWT tokens with configurable expiration
- **Config Validation**: Automatic corruption detection and backup

## 📊 Exit Codes

- `0`: Success (or partial success with details in output)
- `1`: Error (check JSON output or error message)

## 🧪 Development

### Running Tests

```bash
cd agent-harness/opentask-cli
pytest tests/ -v
```

### Code Coverage

```bash
pytest tests/ --cov=opentask --cov-report=html
```

## 📋 Requirements

### Python Version

- **Minimum**: Python 3.8
- **Recommended**: Python 3.11+

### Dependencies

```
click>=8.0.0
httpx>=0.24.0
python-dotenv>=1.0.0
pycryptodome>=3.19.0
keyring>=23.0.0  # Optional, for secure credential storage
```

### Backend

- OpenTask backend running on configured port
- JWT authentication support

## 📖 Documentation

- **Full Analysis**: [CLI_ANALYSIS_REPORT.md](../CLI_ANALYSIS_REPORT.md)
- **Command Structure**: [CLI_COMMAND_STRUCTURE_ANALYSIS.md](../CLI_COMMAND_STRUCTURE_ANALYSIS.md)
- **Requirements**: [REQUIREMENT_COMMANDS.md](../REQUIREMENT_COMMANDS.md)

## 🔄 Changelog

### v1.0.6 (2025-03-27)
- ✨ Added batch-assign command for bulk operations
- 🔧 Improved three-tier comment command structure
- 🔍 Added find command with advanced filtering
- 🗑️ Removed redundant search command (use find instead)
- 🔐 Added system keyring integration
- 📦 Renamed package: opentask → opentask
- 🐛 Fixed API error handling for multiple response formats
- ⚡ Standardized JSON output format

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please ensure:
- Code follows existing style conventions
- All tests pass
- New features include tests
- Documentation is updated

## 📧 Support

For issues and questions:
- GitHub Issues: [opentask/agent-harness](https://github.com/opentask/agent-harness)
- Documentation: [docs.opentask.com](https://docs.opentask.com)
