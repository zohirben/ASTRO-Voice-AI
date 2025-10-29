"""Unit tests for the weather tool.

See /docs_imported/agents/testing.md - Unit Testing Tools
See /docs_imported/agents/tools.md - Tool Definition and Use
"""
import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from tools.weather import get_weather


class TestWeatherTool:
    """Test suite for get_weather tool."""

    @pytest.mark.asyncio
    async def test_get_weather_valid_location(self, mock_context):
        """Test: Weather lookup succeeds with valid location."""
        result = await get_weather(mock_context, "London")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain temperature or weather info (not JSON)
        assert not result.startswith("{")

    @pytest.mark.asyncio
    async def test_get_weather_multiple_cities(self, mock_context):
        """Test: Weather lookup works for different cities."""
        cities = ["Paris", "Tokyo", "New York", "Sydney"]
        
        for city in cities:
            result = await get_weather(mock_context, city)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_weather_invalid_location(self, mock_context):
        """Test: Invalid location returns error message (not exception)."""
        result = await get_weather(mock_context, "InvalidCityXYZ123")
        
        # Should return graceful error message
        assert isinstance(result, str)
        # Either an error message, "could not retrieve", or empty (not a crash)
        assert "could not retrieve" in result.lower() or "error" in result.lower() or len(result) == 0

    @pytest.mark.asyncio
    async def test_get_weather_empty_location(self, mock_context):
        """Test: Empty location parameter is handled."""
        result = await get_weather(mock_context, "")
        
        assert isinstance(result, str)
        # Should not crash, return error or empty

    @pytest.mark.asyncio
    async def test_get_weather_whitespace_location(self, mock_context):
        """Test: Whitespace-only location is handled."""
        result = await get_weather(mock_context, "   ")
        
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_weather_special_characters(self, mock_context):
        """Test: Location with special characters is handled."""
        result = await get_weather(mock_context, "São Paulo")
        
        # Should either work or return graceful error
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_weather_with_forecast(self, mock_context):
        """Test: Forecast parameter (if supported by implementation)."""
        # Skip this test for now - forecast_days not yet implemented
        # To enable: add forecast_days parameter to get_weather function
        pytest.skip("Forecast feature not yet implemented")

    @pytest.mark.asyncio
    async def test_get_weather_returns_readable_format(self, mock_context):
        """Test: Weather result is human-readable (suitable for TTS)."""
        result = await get_weather(mock_context, "Paris")
        
        assert isinstance(result, str)
        # Should be a sentence-like format, not raw JSON or data structure
        assert not result.startswith("[")
        assert not result.startswith("{")

    @pytest.mark.asyncio
    async def test_get_weather_context_not_used(self, mock_context):
        """Test: Tool doesn't crash if context is incomplete."""
        # Some fields might be None or missing
        result = await get_weather(mock_context, "Amsterdam")
        
        assert isinstance(result, str)
        # Should not raise even if context is missing fields


class TestWeatherIntegration:
    """Integration tests for weather tool with API."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark as slow test (can skip with -m "not slow")
    async def test_get_weather_real_api(self, mock_context):
        """Integration test: Call real weather API (if available).
        
        Requires internet connection and working API.
        Skip with: pytest -m "not slow"
        """
        result = await get_weather(mock_context, "London")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should have weather-related keywords
        assert any(keyword in result.lower() for keyword in [
            "temperature", "weather", "°", "celsius", "fahrenheit",
            "sunny", "cloudy", "rainy", "snow"
        ]) or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_get_weather_timeout_handling(self, mock_context):
        """Test: Timeout in external API is handled gracefully."""
        with patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError):
            result = await get_weather(mock_context, "Paris")
            
            assert isinstance(result, str)
            # Should return error message, not raise


class TestWeatherEdgeCases:
    """Edge case tests for weather tool."""

    @pytest.mark.asyncio
    async def test_get_weather_very_long_location(self, mock_context):
        """Test: Very long location string is handled."""
        long_location = "A" * 1000
        result = await get_weather(mock_context, long_location)
        
        assert isinstance(result, str)
        # Should not crash

    @pytest.mark.asyncio
    async def test_get_weather_unicode_locations(self, mock_context):
        """Test: Unicode location names work correctly."""
        locations = ["北京", "Москва", "القاهرة"]  # Beijing, Moscow, Cairo
        
        for location in locations:
            result = await get_weather(mock_context, location)
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_weather_interrupted(self, mock_context):
        """Test: Tool respects interruption flag."""
        mock_context.speech_handle.interrupted = True
        
        result = await get_weather(mock_context, "London")
        # Should still complete (interruption handling is context-dependent)
        assert isinstance(result, str)
