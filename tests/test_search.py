"""Unit tests for the search tool.

See /docs_imported/agents/testing.md - Unit Testing Tools
See /docs_imported/agents/tools.md - Tool Definition and Use
"""
import pytest
from unittest.mock import AsyncMock, patch

from tools.search import search_web


class TestSearchTool:
    """Test suite for search_web tool."""

    @pytest.mark.asyncio
    async def test_search_valid_query(self, mock_context):
        """Test: Search succeeds with valid English query."""
        result = await search_web(mock_context, "machine learning")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should not return raw JSON
        assert not result.startswith("{")

    @pytest.mark.asyncio
    async def test_search_empty_query(self, mock_context):
        """Test: Empty query is handled gracefully."""
        result = await search_web(mock_context, "")
        
        assert isinstance(result, str)
        # Should either skip or return error message

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self, mock_context):
        """Test: Whitespace-only query is handled."""
        result = await search_web(mock_context, "   ")
        
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_short_query(self, mock_context):
        """Test: Single word query works."""
        result = await search_web(mock_context, "Python")
        
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_long_query(self, mock_context):
        """Test: Long query phrase is handled."""
        result = await search_web(
            mock_context, 
            "What are the latest developments in artificial intelligence and machine learning?"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, mock_context):
        """Test: Query with special characters is handled."""
        result = await search_web(mock_context, "C++ programming & best practices")
        
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_question_format(self, mock_context):
        """Test: Question-format query works."""
        result = await search_web(mock_context, "How do I learn Python?")
        
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_returns_readable_format(self, mock_context):
        """Test: Search results are human-readable (TTS-friendly)."""
        result = await search_web(mock_context, "Python tips")
        
        assert isinstance(result, str)
        # Should be formatted text, not raw JSON
        assert not result.startswith("[")

    @pytest.mark.asyncio
    async def test_search_multiple_queries(self, mock_context):
        """Test: Multiple searches in sequence work."""
        queries = [
            "latest AI news",
            "Python libraries",
            "cloud computing",
        ]
        
        for query in queries:
            result = await search_web(mock_context, query)
            assert isinstance(result, str)
            assert len(result) > 0


class TestSearchMultilingual:
    """Test multilingual search capabilities."""

    @pytest.mark.asyncio
    async def test_search_arabic_query(self, mock_context):
        """Test: Arabic query is handled (may be enhanced/translated)."""
        result = await search_web(mock_context, "تعلم البرمجة")  # "Learn programming" in Arabic
        
        assert isinstance(result, str)
        # Should either translate or use the original

    @pytest.mark.asyncio
    async def test_search_spanish_query(self, mock_context):
        """Test: Spanish query works."""
        result = await search_web(mock_context, "Inteligencia artificial")
        
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_mixed_language_query(self, mock_context):
        """Test: Mixed English/other language query."""
        result = await search_web(mock_context, "Python en español")
        
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_sports_arabic(self, mock_context):
        """Test: Sports query in Arabic (known challenge)."""
        # "Spanish football" in Arabic
        result = await search_web(mock_context, "كرة القدم الإسبانية")
        
        assert isinstance(result, str)
        # Should return results (ideally sports-related)


class TestSearchSports:
    """Test sports-related queries (known edge case)."""

    @pytest.mark.asyncio
    async def test_search_football_scores(self, mock_context):
        """Test: Sports scores query."""
        result = await search_web(mock_context, "Premier League scores today")
        
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_sports_news(self, mock_context):
        """Test: Sports news query."""
        result = await search_web(mock_context, "latest tennis news")
        
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_sports_player_info(self, mock_context):
        """Test: Athlete/player info query."""
        result = await search_web(mock_context, "Cristiano Ronaldo stats 2025")
        
        assert isinstance(result, str)


class TestSearchErrorHandling:
    """Test error handling in search tool."""

    @pytest.mark.asyncio
    async def test_search_api_error(self, mock_context):
        """Test: API errors are handled gracefully."""
        with patch('duckduckgo_search.DDGS.text', side_effect=Exception("API Error")):
            result = await search_web(mock_context, "test query")
            
            assert isinstance(result, str)
            # Should return error message, not crash

    @pytest.mark.asyncio
    async def test_search_timeout_handling(self, mock_context):
        """Test: Timeout is handled gracefully."""
        with patch('duckduckgo_search.DDGS.text', side_effect=TimeoutError("Request timeout")):
            result = await search_web(mock_context, "test query")
            
            assert isinstance(result, str)
            # Should return error message, not crash

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_context):
        """Test: Query with no results is handled."""
        with patch('duckduckgo_search.DDGS.text', return_value=[]):
            result = await search_web(mock_context, "random query")
            
            assert isinstance(result, str)
            # Should return message or empty, not crash


class TestSearchIntegration:
    """Integration tests with real search API."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_real_api(self, mock_context):
        """Integration test: Real API call (requires internet).
        
        Skip with: pytest -m "not slow"
        """
        result = await search_web(mock_context, "Python 3.13 release date")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should have some result

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_real_news_query(self, mock_context):
        """Integration test: Real API with time-sensitive query."""
        result = await search_web(mock_context, "latest technology news")
        
        assert isinstance(result, str)
        assert len(result) > 0
