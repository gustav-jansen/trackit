# Playbook: CLI layer (Click)

Governing ADRs: ADR-0001

## When to read
Read this before adding/modifying commands in `src/trackit/cli/commands/` or changing CLI UX in `src/trackit/cli/main.py`.

## Directory conventions
- Commands live in `src/trackit/cli/commands/`.
- Each command module defines `register_commands(cli)`.

## Dependency injection
- Command handlers must get the database via: `ctx.obj["db"]`.

## Error handling
- Print errors to stderr: `click.echo("message", err=True)`
- Exit non-zero on failures: `ctx.exit(1)`

## Adding a command checklist
- [ ] Add new command file under `src/trackit/cli/commands/` (or extend an existing one)
- [ ] Register it in the relevant `register_commands(cli)`
- [ ] Keep option/argument naming consistent with existing commands
- [ ] Update `README.md` to document the command/options
- [ ] Add/adjust tests covering the new behavior

## Testing CLI behavior
Prefer testing the domain/service layer directly when possible.
When CLI-level tests are needed:
- Use Click testing patterns (CliRunner) if present in the repo, otherwise add minimal coverage for parsing/dispatching.
