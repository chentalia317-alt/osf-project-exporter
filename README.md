# OSF Project Exporter
This is a CLI tool you can use for exporting reserach data and files from the OSF website. The idea is to prototype a way to export data from projects, files, etc., from the OSF website, to give users some way to do this until this functionality can be added to the main OSF project.

# Development Setup
For local development you can setup a Docker container with this tool installed as a Python package:
1. [Install and setup Docker and Docker Desktop on your local machine](https://docs.docker.com/desktop/).
2. Clone this repository onto your local machine.
3. On the OSF test server (test.osf.io), create an account and personal access token (PAT) by going into your account settings.
4. Create a `.env` file and add your personal access token to it (see `.env.template`.)
5. In the root of this repository, run `docker compose up --build -d` to setup a container.
6. Use `docker compose exec -it cli <commands>` to run CLI tool commands (e.g. `pull-projects`) or run unit tests (i.e. `python -m unittest`.)

You could also setup a Python virtual environment (e.g. using virtualenv) and run `pip install -e osfio-export-tool` to install the CLI tool inside it for dev purposes.

# Using the CLI
- Run `clirun` to get a list of basic commands you can use.
- To see what a command needs as input, type `--help` after the command name (e.g. `clirun pull-projects --help`; `clirun --help`)
- To pull your projects from the OSF into a PDF, run `clirun pull-projects`.
