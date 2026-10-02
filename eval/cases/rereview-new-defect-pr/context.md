Ticket: let staff export a monthly order report and download it as a gzip archive.

Prior review of an earlier head of this pull request:

    [HIGH] app/reports/export.py:9 - SQL built by string concatenation
      What: the month parameter is concatenated into the order query.
      Class: 2.5
    VERDICT: BLOCK - SQL injection in the order export query.

A follow-up commit parameterizes the order query in app/reports/export.py.
