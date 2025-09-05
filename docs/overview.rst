Overview
========

The main source code for osfexport is kept in src/osfexport and is structured as such:

* exporter.py: This handles the main logic for exporting data through the API.
* formatter.py: This handles how to write project data obtained from the API to an output PDF.
* cli.py: This handles the command-line interface, defining what commands and help text are shown to a CLI user.

Tests are written using the `unittest` framework and are kept in tests/test_clitool.py:

* TestFormatter: tests the code in formatter.py
* TestCLI: tests code in cli.py
* TestExporter: tests code in exporter.py
* TestAPI: API tests to check we can use the OSF v2 API as expected
