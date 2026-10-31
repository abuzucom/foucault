Ticket: Add a monthly order export as a gzip archive.

Prior review of an earlier pull request revision:

    [HIGH] app/reports/export.py:9 - SQL built by string concatenation
      What: The month parameter is concatenated into the order query.
      Class: 2.5
    VERDICT: BLOCK - SQL injection in the order export query.

A follow-up commit parameterizes the order query in app/reports/export.py.

The prior review is context. Review the complete current diff. Report the
prior SQL finding as resolved or still open. Review every new path.
