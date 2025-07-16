# OSF Project Exporter

This is a CLI tool for exporting research project data and files from the [OSF website](https://osf.io/). This is to prototype tool to export projects from the OSF website to a PDF, allowing users to back up, share or document their OSF projects in an offline medium.

## Installation

You can setup a Docker container with this tool installed as a Python package:

1. [Install and setup Docker and Docker Desktop on your local machine](https://docs.docker.com/desktop/).
2. Clone this repository onto your local machine.
3. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, selecting "Personal access tokens" in the left side menu, and clicking "Create token". You should give the token a name that helps you remember why you made it, like "PDF export", and choose the "osf.nodes.full_read" scope - this allows this token to read all public and private projects on your account. You can delete this token once you have finished exporting your projects.
4. Create a `.env` file and add your personal access token to it (see `.env.template`.)
5. In the root of this repository, run `docker compose up --build -d` to setup a container.
6. Use `docker compose exec -it cli <commands>` to run CLI tool commands (e.g. `pull-projects`) or run unit tests (i.e. `python -m unittest`.)

You could also setup a Python virtual environment (e.g. using virtualenv) and run `pip install -e osfio-export-tool` to install the CLI tool inside the environment. You will still need to create a personal access token following the instructions in step 3 above.

## Usage

- Run `clirun` to get a list of basic commands you can use.
- To see what a command needs as input, type `--help` after the command name (e.g. `clirun pull-projects --help`; `clirun --help`)
- To export all your projects from the OSF into a PDF, run `clirun pull-projects`.
