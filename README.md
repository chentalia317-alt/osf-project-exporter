# OSF Project Exporter

`osfexport` is a proof-of-concept Python library and command-line tool for exporting research project data and files from the [OSF website](https://osf.io/). It enables researchers to export project data into a PDF for archiving and backup of OSF projects.
The project data exported includes:

- Project metadata: title, description, funding sources, subjects, tags, date created, date modified, etc.
- A list of project files stored on OSF Storage. Files stored on the OSF can be downloaded directly from the website, you can use this list to check what files should be present.
- A list of contributors for the project: name, if they are bibliographic (appear on citations and public list of contributors), profile link
- Wiki page contents - includes formatted markdown and images
- Any components added as a sub-project

Currently this project is a proof-of-concept for data backup for the OSF focused on exporting project data which doesn't have a way to do so on the OSF website. It could be extended to include preprints, registrations, and other data types.

## Installation

Install this library via pip:
`python -m pip install osfexport`

## Usage

`osfexport` can be used as either a Python library or a command-line tool.

To use as a command-line tool:

- On the OSF website, create or log in to your account and set up a personal access token (PAT)
  - Go to your account settings, select `Personal access tokens` in the left side menu
  - Click `Create token`. You should give the token a name that helps you remember why you made it, like "PDF export"
  - Give your token the `osf.full_read` scope. This allows the token to access private projects you are a contributor to.
- Run `osfexport` to get a list of basic commands you can use.
- To see what a command needs as input, type `--help` after the command name (e.g. `osfexport welcome --help`; `osfexport --help`)
- To export all your projects from the OSF into a PDF, run `osfexport projects`.

## Development Setup

### Virtual Environment

1. Clone this repository onto your local machine.
2. Create a virtual environment to install dependencies. For `virtualenv` this is done with ``virtualenv <myenvname>``. Make sure your virtual environment is setup to use Python 3.12 or above (e.g., ``virtualenv <myenvname> --python="/usr/bin/python3.12"`` on Linux.)
3. From local Git repo: Activate your virtual environment and run ``pip install -e osfexport`` to install this repository as a modifiable package.
4. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, select `Personal access tokens` in the left side menu, and clicking `Create token`. You should give the token a name that helps you remember why you made it, like "PDF export", and choose the `osf.full_read` scope - this allows this token to read all public and private projects on your account.

## Acknowledgements

Work for v1.0.0 of `osfexport` was kindly funded by the Advance Open-Source Infrastructure for Research grant, as part of the The Open Source Awardee Program by the [Center for Open Science](https://www.cos.io/), and a collaboration between Center for Open Science and the [University of Manchester Research IT department](https://research-it.manchester.ac.uk/).
