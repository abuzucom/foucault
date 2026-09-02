def post_review(pr, model_report):
    """Publish the model's security report as a PR comment."""
    github.issues.create_comment(
        owner=pr.owner, repo=pr.repo, issue_number=pr.number,
        body=model_report,
    )
