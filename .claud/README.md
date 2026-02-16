# Claude Documentation Directory

This directory contains documentation files that help Claude (and developers) understand the project context, common tasks, and workflows.

## Files in This Directory

### `quiz-generation-guide.md`
Task-specific guide for quiz generation workflows. Helps Claude understand:
- Common user requests and how to handle them
- Step-by-step workflows for different scenarios
- Troubleshooting common issues
- Quick command reference
- Decision trees for choosing modes

## Other Documentation Files

### `/quiz/backend/CLAUDE.md`
Comprehensive developer guide covering:
- Architecture overview
- All quiz generation modes (default, file, spreadsheet)
- Configuration details
- Testing procedures
- Function reference
- Performance characteristics

### `/quiz/backend/TESTING_DEFAULT_MODE.md`
Step-by-step testing guide for the new default mode:
- Prerequisites checklist
- Document preparation
- Configuration examples
- Test scenarios with expected outputs
- Common issues and solutions
- Success criteria

### `/README.md` (project root)
User-facing README with:
- Project overview
- Features
- Setup instructions
- Usage examples
- Tech stack

## How to Use These Files

### For Claude
When a user asks about quiz generation:
1. Read `.claud/quiz-generation-guide.md` for task-specific workflows
2. Reference `quiz/backend/CLAUDE.md` for architectural details
3. Use `quiz/backend/TESTING_DEFAULT_MODE.md` for testing procedures
4. Check main `README.md` for user-facing features

### For Developers
1. Start with `README.md` for project overview
2. Read `quiz/backend/CLAUDE.md` for comprehensive technical details
3. Follow `quiz/backend/TESTING_DEFAULT_MODE.md` for testing new features
4. Reference `.claud/quiz-generation-guide.md` for common workflows

## Documentation Philosophy

- **README.md**: User-facing, focuses on features and usage
- **CLAUDE.md**: Developer-facing, comprehensive technical guide
- **TESTING_DEFAULT_MODE.md**: Testing-specific, step-by-step procedures
- **.claud/quiz-generation-guide.md**: Task-specific, workflow-oriented

## Keeping Documentation Updated

When making changes to the codebase:
1. Update relevant documentation files
2. Add new sections for new features
3. Mark deprecated features clearly
4. Update "Last Updated" dates
5. Update examples and commands

## Recent Changes

### 2026-02-07
- Added default quiz generation mode
- Created comprehensive testing guide
- Added task-specific workflow documentation
- Updated main README with new mode examples

---

**Maintained by**: Gurukula Team
**Contact**: @mambabhi on GitHub
**Last Updated**: 2026-02-07
