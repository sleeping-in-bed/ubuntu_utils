#!/usr/bin/env python3
import shutil
import subprocess
import time
from pathlib import Path

import click
from commands import (
    create_swap,
    install_anaconda,
    install_chrome,
    install_cursor,
    install_docker,
    install_minikube,
    install_python_dev_env,
    install_remote_ide,
    install_sougoupinyin,
    install_vscode,
    login_docker,
    post_settings,
    pre_settings,
)

CONFIG_PATH = Path(__file__).parent / "configs.py"
TEMPLATE_PATH = Path(__file__).parent / "configs.template.py"

# Define allowed commands
ALLOWED_COMMANDS = [
    "basic",
    "docker",
    "vscode",
    "anaconda",
    "python",
]


def py_code(commands: list[str]) -> str:
    code = ""
    if not commands:
        click.echo("No commands provided. Running full setup...")
        return (
            f"{pre_settings.__name__}();"
            f"{create_swap.__name__}();"
            f"{install_python_dev_env.__name__}();"
            f"{install_docker.__name__}();"
            f"{login_docker.__name__}();"
            f"{install_anaconda.__name__}();"
            f"{install_chrome.__name__}();"
            f"{install_sougoupinyin.__name__}();"
            f"{install_vscode.__name__}();"
            f"{install_cursor.__name__}();"
            f"{install_remote_ide.__name__}();"
            f"{install_minikube.__name__}();"
            f"{post_settings.__name__}();"
        )
    for command in commands:
        if command not in ALLOWED_COMMANDS + list(globals().keys()):
            click.echo(f"[Error] Unknown command: '{command}'")
            raise SystemExit(1)
        elif command == "basic":
            code += f"{pre_settings.__name__}();{post_settings.__name__}();"
        elif command == "docker":
            code += f"{install_docker.__name__}();{login_docker.__name__}();"
        elif command == "vscode":
            code += f"{install_vscode.__name__}();"
        elif command == "anaconda":
            code += f"{install_anaconda.__name__}();"
        elif command == "python":
            code += f"{install_python_dev_env.__name__}();"
        else:
            code += f"{command}();"
    return code


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.option("--config", is_flag=True, help="Edit the config file.")
@click.argument("commands", nargs=-1)
def main(config, commands):
    """
    CLI tool to manage system setup using predefined commands.

    \b
    Examples:
        ubuntu_utils                   # Run full setup
        ubuntu_utils basic create_swap     # Run selected steps
        ubuntu_utils --config          # Edit config file

    \b
    Available commands:
        basic       => Basic system settings and software installation
        docker      => Install and log in to Docker
        vscode      => Install VS Code
        anaconda    => Install Anaconda
        python      => Install Python development environment
        (others)    => Any function name from commands.py
    """
    if config:
        if not CONFIG_PATH.exists():
            if not TEMPLATE_PATH.exists():
                click.echo(
                    f"Template file {TEMPLATE_PATH} does not exist. Cannot create config."
                )
                raise SystemExit(1)
            shutil.copy(TEMPLATE_PATH, CONFIG_PATH)
            click.echo(f"Copied template to {CONFIG_PATH}. Opening for editing...")
            time.sleep(2)
        subprocess.call(["nano", str(CONFIG_PATH)])
        raise SystemExit(0)

    if not CONFIG_PATH.exists():
        click.echo(
            "Missing config file. Please run with --config to create and edit it first."
        )
        raise SystemExit(1)

    click.echo("Config file found. Continuing execution...")
    subprocess.call([str(Path(__file__).parent / "run.sh"), py_code(list(commands))])


if __name__ == "__main__":
    main()
