Basic Flow of Exporting
=======================

1. Users may need to give a string GUID to export a particular project. The easiest way to do this for them is to give the URL to their project. `osfexport` provides a way to project IDs from OSF project URLs with the `exporter.extract_project_id` method.
2. If the user wants to export all projects where they are contributors, or a single private project, they will need to provide a Personal Access Token. In the CLI this is done via the cli.prompt_pat method.
3. Get data for projects for rendering via the OSF API using `exporter.get_nodes`. This will return a dictionary of projects with their attributes (including child projects AKA components), and a list of indexes for the positions of the projects to make PDFs for.
4. Output the project data obtained to a PDF by passing the project dictionary to `formatter.write_pdf`

Example:

.. code-block:: python

  import osfexport

  # Need PAT for private projects or exporting all projects, otherwise can be left blank
  # pat = <some-way-to-get-pat>
  pat = ''

  # Need this part for single projects
  project_id = osfexport.exporter.extract_project_id(url)

  projects, indexes_of_main_projects = osfexport.exporter.get_nodes(pat=pat, project_id=project_id)
  for project in indexes_of_main_projects:
    file, file_path = osfexport.formatter.write_pdf(projects, project, folder='')
