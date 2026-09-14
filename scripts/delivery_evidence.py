#!/usr/bin/env python3
"""Validate evidence attached to repository delivery claims."""
import re


COMMIT_RE = re.compile(r"\A[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?\Z")
COMMAND_RESULTS = frozenset(("succeeded", "failed", "not_run"))
CLAIM_TYPES = frozenset(("push", "pull_request"))
REQUIRED_FIELDS = (
    "checkout_path", "current_branch", "commit", "remote_ref",
    "command_result", "pr_number", "is_draft", "remote_ref_verified",
    "pr_verified", "draft_status_verified",
)


def _is_nonempty_string(value) -> bool:
    """Return whether `value` is a non-empty string."""
    return isinstance(value, str) and bool(value.strip())


def validate_evidence(evidence: dict) -> list[str]:
    """Return structural errors in a delivery evidence record."""
    if not isinstance(evidence, dict):
        return ["evidence must be an object"]
    errors = [
        f"missing evidence field: {field}"
        for field in REQUIRED_FIELDS
        if field not in evidence
    ]
    if errors:
        return errors
    for field in ("checkout_path", "current_branch", "remote_ref"):
        if not _is_nonempty_string(evidence[field]):
            errors.append(f"{field} must be a non-empty string")
    if not isinstance(evidence["commit"], str) or not COMMIT_RE.fullmatch(
            evidence["commit"]):
        errors.append("commit must be a 40 or 64 character hexadecimal ID")
    if evidence["command_result"] not in COMMAND_RESULTS:
        errors.append("command_result is not recognized")
    if evidence["pr_number"] is not None and (
            not isinstance(evidence["pr_number"], int)
            or isinstance(evidence["pr_number"], bool)
            or evidence["pr_number"] < 1):
        errors.append("pr_number must be a positive integer or null")
    if evidence["is_draft"] is not None and not isinstance(
            evidence["is_draft"], bool):
        errors.append("is_draft must be a boolean or null")
    for field in ("remote_ref_verified", "pr_verified", "draft_status_verified"):
        if not isinstance(evidence[field], bool):
            errors.append(f"{field} must be a boolean")
    return errors


def claim_errors(evidence: dict, claim_type: str) -> list[str]:
    """Return reasons a delivery claim cannot be reported as verified."""
    errors = validate_evidence(evidence)
    if claim_type not in CLAIM_TYPES:
        errors.append("claim_type is not recognized")
    if errors:
        return errors
    if evidence["command_result"] != "succeeded":
        errors.append("command result is not succeeded")
    if not evidence["remote_ref_verified"]:
        errors.append("remote ref has not been read back")
    if claim_type == "pull_request":
        if evidence["pr_number"] is None or not evidence["pr_verified"]:
            errors.append("pull request has not been read back")
        if not evidence["draft_status_verified"]:
            errors.append("draft status has not been read back")
        if evidence["is_draft"] is not True:
            errors.append("pull request is not confirmed as a draft")
    return errors


def verification_status(evidence: dict, claim_type: str) -> str:
    """Return `verified`, `failed`, or `unverified` for a delivery claim."""
    errors = validate_evidence(evidence)
    if errors:
        return "unverified"
    if evidence["command_result"] == "failed":
        return "failed"
    if claim_errors(evidence, claim_type):
        return "unverified"
    return "verified"
