---
name: rst-formatter
description: >-
  Enforce consistent reStructuredText (reST) heading hierarchy and exact
  underline length matching.
---

# reST Heading Formatter Skill

## Heading rules

Use underline-only adornments. Do not put an adornment above the title, and
do not indent heading text.

Use these adornments in this exact hierarchy:

- Level 1 (document title): `#`
- Level 2 (section): `=`
- Level 3 (subsection): `-`
- Level 4 (sub-subsection): `^`

Each heading must be plain text, with no leading or trailing spaces or inline
markup. Put it at the start of the line, followed immediately by an underline
made only from its assigned punctuation character. Leave a blank line after
the underline.

The underline must have exactly the same number of characters as the heading
text. Count internal spaces; leading and trailing spaces are not allowed.

Use a marker only for its assigned level. Do not replace structural section
headings with `.. rubric::`; rubrics do not establish document hierarchy.

## Examples

Each heading below is followed by an underline with the exact matching length:

- Level 1: `Document Title` followed by `##############` (14 characters).
- Level 2: `Section` followed by `=======` (7 characters).
- Level 3: `Subsection` followed by `----------` (10 characters).
- Level 4: `Details` followed by `^^^^^^^` (7 characters).

This overline form is invalid for this project, even though reStructuredText
allows it:

```rst
##############
Document Title
##############
```

## Final check

Before finishing an `.rst` edit, verify that every heading:

- starts at column 1 and has no inline markup;
- uses the marker assigned to its hierarchy level;
- has an underline with an exact character-for-character length match;
- has a blank line after the underline.
