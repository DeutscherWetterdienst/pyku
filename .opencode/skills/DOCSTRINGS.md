## Docstring Guidelines (NumPy Style)

Adhere to these rules when writing, updating, or reviewing Python docstrings.

### Execution Modes
- **Plan / Read-Only:** Output complete docstring drafts directly in the
  response for review. Do not edit files.
- **Write / Edit:** Update target files directly.

### Core Rules
1. **Format:** Strict NumPy style (`Parameters`, `Returns`, `Yields`, `Raises`,
   `See Also`, `Notes`, `Examples`). Convert Google-style docstrings to NumPy
   format automatically.
2. **Line Length:** Maximum 80 characters per line across all docstring text,
   types, and code blocks.
3. **Accuracy:** Verify all parameter names, types, default values, return
   types, and raised exceptions against actual function signatures.
4. **Preservation:** Keep existing domain documentation intact while
   restructuring to NumPy format.
5. **Interactive Examples:** Use standard Sphinx/IPython syntax (`..
   ipython::`). When using `@savefig`, always include `scale=70`.

### Section Layout Reference
```python

def example_function(param1: int, param2: str = "default") -> bool:
    """Short summary line ending with a period.

    Extended description providing necessary context or domain logic.

    Parameters
    ----------
    param1 : int
        Description of param1.
    param2 : str, default "default"
        Description of param2.

    Returns
    -------
    bool
        Description of return value.
    """
```
