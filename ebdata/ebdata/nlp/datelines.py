import re

dateline_re = re.compile(ur"""
    (?:
        (?:                                                     # Either a newline, or a
            ^                                                   # <p> / <div>, followed by tags/space
            |
            </?\s*(?:[Pp]|[Dd][Ii][Vv])[^>]*>
        )
        (?:<[^>]*>|\s)*                                         # The start of a line
    )
    (?:\(\d\d?-\d\d?\)\s+\d\d?:\d\d\s+[PMCE][SD]T\s+)?          # Optional timestamp -- e.g., "(07-17) 13:09 PDT"
    ([A-Z][A-Z.]*[A-Z.,](?:\s+[A-Z][A-Za-z.]*[A-Za-z.,]){0,4})  # The dateline itself
    (?:                                                         # Optional parenthetical news outlet
        \s+
        \(
            [-A-Za-z0-9]{1,15}
            (?:\s+[-A-Za-z0-9]{1,15}){0,4}
        \)
    )?
    \s*                                                         # Optional space before dash
    (?:\xa0--\xa0|--|\x97|\u2015|&\#8213;|&\#151;|&\#x97;|)     # Dash (or emdash)
    """, re.MULTILINE | re.VERBOSE)

def guess_datelines(text):
    """
    Given some text (with or without HTML), returns a list of the dateline(s)
    in it. Returns an empty list if none are found.
    """
    return dateline_re.findall(text)
