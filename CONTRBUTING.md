# Contributing

`osfexport` is an open-source project. Contributions to report bugs, suggest new features or improvements, ask questions, develop the code/documentation, and any other kind of contribution are more than welcome.

By contributing, you are agreeing that we may redistribute your work under [this license](https://github.com/CenterForOpenScience/osf-project-exporter?tab=Apache-2.0-1-ov-file).

## Guidelines

### GitHub Flow

Contrbutions to code and documentation should follow the [GitHub flow model](https://docs.github.com/en/get-started/using-github/github-flow) in general. Key points are:
- Feature branches should be branched off of develop or a release branch
- All changes to be merged must have a Pull Request opened first.
- Before submitting a pull request re-merge the source branch and resolve any merge conflicts
- A branch should not be merged until it passes all checks and has been approved by one person.
  - Checks for linting quality and if tests pass automatically runs when pull requests are made and updated.
- Do not merge develop if you are working of a release branch and visa versa
- Use -'s for spaces not _'s
- Hotfixes are to be branched off main
  - Hotfix PR should be names hotfix/brief-description
  - A hotfix for an issue involving figshare metadata when empty lists are returned would behotfix/figshare-metadata-empty
  - When hotfixes are merged a new branch will be created bumping the minor version ie hotfix/0.1.3 and the other PR will be merged into it

The naming convention for branches is: <issue-number>-<brief-issue-description>. For example, a branch for issue 5 `Make tests run faster` would be named `5-make-tests-run-faster`.

### Library Versioning

`osfexport` uses semantic versioning `<major>.<minor>.<patch>`
- Patches are reserved for hotfixes and bugfixes only
- Minor versions are for adding new functionality
- Minor versions: any changes must be backwards compatible
- Major versions can contain breaking changes

### Pull Request Guidelines

All code must pass [flake8 linting](https://peps.python.org/pep-0008/)
- Max line length is set 100 characters

Imports are should be ordered in pep8 style.

Keep commit histories as clean and simple as possible, with meanigful commit messages.

Add docstrings and comments to document what your functions, classes and code does.

Add tests for new features or checking for bugs, to help verify the correctness of your changes.

Make a PR to resolve one issue only. Keep changes made to only those needed to resolve the issue.


## Development Setup

### Virtual Environment

1. Clone this repository onto your local machine.
2. Create a virtual environment to install dependencies. For `virtualenv` this is done with ``virtualenv <myenvname>``. Make sure your virtual environment is setup to use Python 3.12 or above (e.g., ``virtualenv <myenvname> --python="/usr/bin/python3.12"`` on Linux.)
3. From local Git repo: Activate your virtual environment and run ``pip install -e osfexport`` to install this repository as a modifiable package.
4. On the OSF website, create or log in to your account.  Set up a personal access token (PAT) by going into your account settings, select `Personal access tokens` in the left side menu, and clicking `Create token`. You should give the token a name that helps you remember why you made it, like "PDF export", and choose the `osf.full_read` scope - this allows this token to read all public and private projects on your account.
