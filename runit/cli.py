import sys

import click

from runit.config import (
    CommandConfig,
    find_config,
    global_config_path,
    load_config,
    load_merged_config,
    save_config,
)
from runit.exceptions import RunitError
from runit.runner import execute


class RunitGroup(click.Group):
    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["run"] + args
        return super().parse_args(ctx, args)


@click.group(cls=RunitGroup)
def cli():
    """runit - run project commands defined per project."""


@cli.command(hidden=True)
@click.argument("name")
def run(name):
    try:
        commands = load_merged_config()
    except RunitError as e:
        click.secho(str(e), fg="red", err=True)
        sys.exit(1)

    if not commands:
        click.secho(
            "No commands defined yet. Use 'runit add' to create one.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    if name not in commands:
        click.secho(
            f"Unknown command '{name}'. Run 'runit list' to see available commands.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    exit_code = execute(commands[name])
    sys.exit(exit_code)


@cli.command("list")
@click.option("--global", "-g", "is_global", is_flag=True, help="Show only global commands.")
def list_commands(is_global):
    try:
        if is_global:
            commands = load_config(global_config_path())
            label = f"Global commands ({global_config_path()})"
        else:
            project_cmds = load_config()
            global_cmds = load_config(global_config_path())
            label = None
    except RunitError as e:
        click.secho(str(e), fg="red", err=True)
        sys.exit(1)

    if is_global:
        if not commands:
            click.echo("No global commands defined. Use 'runit add -g' to create one.")
            return
        click.secho(f"{label}:\n", bold=True)
        _print_commands(commands)
        return

    if not project_cmds and not global_cmds:
        click.echo("No commands defined yet. Use 'runit add' to create one.")
        return

    if global_cmds:
        click.secho(f"Global commands ({global_config_path()}):\n", bold=True)
        _print_commands(global_cmds)
        click.echo()

    if project_cmds:
        click.secho(f"Project commands ({find_config()}):\n", bold=True)
        _print_commands(project_cmds)
    elif global_cmds:
        click.echo("No project commands defined.")


def _print_commands(commands: dict[str, CommandConfig]) -> None:
    for name, cmd in commands.items():
        mode_tag = f"  [{cmd.mode}]" if cmd.mode != "sequential" else ""
        if len(cmd.steps) == 1:
            click.echo(f"  {name:<16} {cmd.steps[0]}{mode_tag}")
        else:
            click.echo(f"  {name:<16} ({len(cmd.steps)} steps){mode_tag}")


@cli.command()
@click.argument("name")
@click.argument("steps", nargs=-1, required=True)
@click.option("--mode", "-m", type=click.Choice(["sequential", "random"]), default="sequential")
@click.option("--global", "-g", "is_global", is_flag=True, help="Add as a global command.")
def add(name, steps, mode, is_global):
    """Add a command. Usage: runit add <name> "cmd1" "cmd2" ..."""
    try:
        path = global_config_path() if is_global else find_config()
        commands = load_config(path)
    except RunitError as e:
        click.secho(str(e), fg="red", err=True)
        sys.exit(1)

    if name in commands:
        click.secho(f"Command '{name}' already exists. Remove it first to replace.", fg="yellow", err=True)
        sys.exit(1)

    commands[name] = CommandConfig(name=name, steps=list(steps), mode=mode)
    save_config(commands, path)
    scope = "global" if is_global else "project"
    click.secho(f"Added {scope} command '{name}'", fg="green")


@cli.command()
@click.argument("name")
@click.option("--global", "-g", "is_global", is_flag=True, help="Remove a global command.")
def remove(name, is_global):
    """Remove a command."""
    try:
        path = global_config_path() if is_global else find_config()
        commands = load_config(path)
    except RunitError as e:
        click.secho(str(e), fg="red", err=True)
        sys.exit(1)

    if name not in commands:
        scope = "global" if is_global else "project"
        click.secho(f"Command '{name}' not found in {scope} commands.", fg="red", err=True)
        sys.exit(1)

    del commands[name]
    save_config(commands, path)
    scope = "global" if is_global else "project"
    click.secho(f"Removed {scope} command '{name}'", fg="green")
