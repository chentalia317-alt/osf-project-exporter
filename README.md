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

Here are some tips to using it as a command-line tool:

- Run `osfexport` to get a list of basic commands you can use.
- To see what a command needs as input, type `--help` after the command name (e.g. `osfexport welcome --help`; `osfexport --help`)
- To export all your projects from the OSF into a PDF, run `osfexport projects`.
