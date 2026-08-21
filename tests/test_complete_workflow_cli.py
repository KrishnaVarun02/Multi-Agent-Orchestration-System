"""Tests for the complete workflow CLI's display helpers."""

from dataclasses import dataclass
from importlib import import_module

get_review_payload = import_module(
    "lessons.17_complete_workflow_cli"
).get_review_payload


@dataclass
class FakeInterrupt:
    """Match the small part of LangGraph's Interrupt used by the CLI."""

    value: dict


def test_get_review_payload_returns_interrupt_value() -> None:
    review = {"issue": "Fix checkout", "test_status": "passed"}
    state = {"__interrupt__": [FakeInterrupt(review)]}

    assert get_review_payload(state) == review


def test_get_review_payload_returns_none_without_interrupt() -> None:
    assert get_review_payload({"test_status": "failed"}) is None
