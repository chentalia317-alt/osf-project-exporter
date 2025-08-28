# OSF Project Exporter

This is a CLI tool for exporting research project data and files from the [OSF website](https://osf.io/). This is to prototype tool to export projects from the OSF website to a PDF, allowing users to back up, share or document their OSF projects in an offline medium.

## Development Setup

### Virtual Environment

1. Clone this repository onto your local machine.
2. Create a virtual environment to install dependencies. For virtualenv this is done with ``virtualenv <myenvname>``. Make sure your virtual environment is setup to use Python 3.12 or above (e.g., ``virtualenv <myenvname> --python="/usr/bin/python3.12"`` on Linux.)
3. From local Git repo: Activate your virtual environment and run ``pip install -e osfexport`` to install this repository as a modifiable package. Then install other requirements separately via `pip install -r requirements.txt`.
4. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, select `Personal access tokens` in the left side menu, and clicking `Create token`. You should give the token a name that helps you remember why you made it, like "PDF export", and choose the `osf.full_read` scope - this allows this token to read all public and private projects on your account. You can delete this token once you have finished exporting your projects.

### Docker

You can setup a Docker container with this tool installed as a Python package:

1. [Install and setup Docker and Docker Desktop on your local machine](https://docs.docker.com/desktop/).
2. Clone this repository onto your local machine.
3. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, select `Personal access tokens` in the left side menu, and clicking `Create token`. You should give the token a name that helps you remember why you made it, like "PDF export", and choose the `osf.full_read` scope - this allows this token to read all public and private projects on your account. You can delete this token once you have finished exporting your projects.
4. Create a `.env` file and add your personal access token to it (see `.env.template`.)
5. In the root of this repository, run `docker compose up --build -d` to setup a container.
6. Use `docker compose exec -it cli <commands>` to run CLI tool commands (e.g. `export-projects`) or run unit tests (i.e. `python -m unittest`.)

## Installation

### From PyPI: releases 0.1.4 and onwards

Activate your virtual environment, for virtualenv this is done by:

- `source <myenvname>/bin/activate` on Linux
- `<myenvname>\Scripts\activate` on Windows/Mac

Next, run `python -m pip install osfexport`. This will download and install this package and other dependencies from the PyPI index.

### From TestPyPi: releases before 0.1.4

Activate your virtual environment and run `python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple osfexport`. This will download the packages needed from the PyPI index and the packaged version of this CLI tool on the TestPyPI index.

## Usage

- Run `osfget` to get a list of basic commands you can use.
- To see what a command needs as input, type `--help` after the command name (e.g. `osfget show-welcome --help`; `osfget --help`)
- To export all your projects from the OSF into a PDF, run `osfget export-projects`.
