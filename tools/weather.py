# See /docs_imported/agents/tools.md - Function tool patterns with external APIs
from livekit.agents import function_tool, RunContext
import requests
import logging
import asyncio

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    
    For Realtime/Voice agents, this tool RETURNS error strings instead of raising
    exceptions. This allows Gemini to see the actual error and voice it correctly.
    
    See /docs_imported/agents/tools.md - Voice agent error handling patterns
    
    Retrieves weather with an 8-second timeout to ensure responsive interactions.
    
    Returns:
        Success: Weather information string
        Error: "error: [reason]" (allows Gemini to detect and voice the error)
    """
    try:
        # Run blocking request in executor with timeout
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                requests.get,
                f"https://wttr.in/{city}?format=3"
            ),
            timeout=8.0
        )
        
        if response.status_code == 200:
            weather_text = response.text.strip()
            logging.info(f"Weather for {city}: {weather_text}")
            return weather_text
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"error: could not retrieve weather for {city}."
    except asyncio.TimeoutError:
        logging.warning(f"Weather API timeout for {city} after 8 seconds")
        return f"error: weather lookup timed out for {city}."
    except Exception as e:
        logging.error(f"error: retrieving weather for {city}: {e}")
        return f"error: could not retrieve weather for {city}."
