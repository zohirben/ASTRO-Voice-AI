"""Pytest configuration and shared fixtures for JARVIS tests.

See /docs_imported/agents/testing.md - Testing patterns and fixtures
"""
import pytest
from unittest.mock import AsyncMock
from livekit.agents import RunContext


@pytest.fixture
def mock_context():
    """Create a mock RunContext for testing tools.
    
    Provides:
    - session: mocked AgentSession
    - speech_handle: mocked speech handle for interruption checks
    - userdata: dict for storing session-specific data
    """
    context = AsyncMock(spec=RunContext)
    context.session = AsyncMock()
    context.session.generate_reply = AsyncMock()
    context.speech_handle = AsyncMock()
    context.speech_handle.interrupted = False
    context.userdata = {}
    return context


@pytest.fixture
def mock_job_context():
    """Create a mock JobContext for integration tests."""
    from unittest.mock import MagicMock
    
    context = MagicMock()
    context.room = AsyncMock()
    context.room.name = "test-room"
    context.connect = AsyncMock()
    context.job = MagicMock()
    context.job.id = "test-job-123"
    return context
