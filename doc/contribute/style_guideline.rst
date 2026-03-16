Style guideline
===============

By following these style guidelines, you can create a consistent and readable
codebase that is easy to maintain and collaborate on with others.

**Use consistent naming conventions**

Use descriptive variable and function names that follow `PEP 8 style guidelines
<https://peps.python.org/pep-0008/>`_. Use CamelCase for class names and
lowercase_with_underscores for function and variable names. Avoid using
single-character variable names.

**Follow PEP 8 style guidelines**

Use four spaces for indentation. Limit line length to 79 characters. Use
spaces around operators and after commas, but not directly inside parentheses
or brackets.

**Use docstrings to document code**

Use triple quotes to document functions, classes, and modules. Include
information about inputs, outputs, and what the code does.  Use `google format
<https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_
for documentation.

**Use version control**

Use Git and GitLab to keep track of changes to your code. Use short and precise
`commit messages
<https://github.com/RomuloOliveira/commit-messages-guide/blob/master/README_de-DE.md>`_.
Use branches and pull requests to collaborate with others and review changes
before merging into the main branch.

.. **Use type hints to specify types**
..
.. Use type hints to specify the expected types of function inputs and outputs.
.. Use the typing module to specify types of more complex objects.

**Use xarray, pandas, and geopandas best practices**

Use xarray to handle multi-dimensional data and coordinate metadata. Use
pandas to handle tabular data and time series. Use geopandas to handle
geographic data.  Use the built-in functionality of these libraries to optimize
code for performance and readability.

**Use virtual environments**

Use virtual environments to isolate project dependencies from other Python
packages on your system. Use a package manager like pip or conda to install
and manage dependencies.

**Write tests**

Write unit tests to ensure that code is correct and functional. Use testing
frameworks like pytest to automate testing. Include tests in continuous
integration and deployment pipelines to catch errors early.

