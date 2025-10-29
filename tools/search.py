# See /docs_imported/agents/tools.md - Function tool patterns for real-time search
from livekit.agents import function_tool, RunContext
import logging
import asyncio

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str
) -> str:
    """
    Search the web using DuckDuckGo.
    
    For Realtime/Voice agents, this tool RETURNS error strings instead of raising
    exceptions. This allows Gemini to see the actual error and voice it correctly.
    
    See /docs_imported/agents/tools.md - Voice agent error handling patterns
    
    Fast, reliable search optimized for voice agents.
    Returns concise, relevant results for quick LLM processing.
    
    Args:
        context: RunContext for session access
        query: Search query string
        
    Returns:
        Success: Formatted search results
        Error: "error: [reason]" (allows Gemini to detect and voice the error)
    """
    try:
        from ddgs import DDGS
        
        logging.info(f"search_web: starting search for '{query}'")
        
        # Run search with reasonable timeout
        loop = asyncio.get_event_loop()
        
        def _run_search():
            # Use DDGS with specific backend for faster, more reliable results
            # backend='duckduckgo' uses DuckDuckGo HTML API directly
            # region='wt-wt' ensures we get English/international results
            results = []
            with DDGS() as ddgs:
                # Get up to 5 results (we'll use top 3)
                # Using backend='duckduckgo' avoids slow fallback to Yahoo/Yandex
                for result in ddgs.text(
                    query, 
                    region='wt-wt',  # World-wide results
                    safesearch='moderate',
                    backend='duckduckgo',  # Use DuckDuckGo HTML directly (faster)
                    max_results=5
                ):
                    results.append(result)
            return results
        
        search_results = await asyncio.wait_for(
            loop.run_in_executor(None, _run_search),
            timeout=20.0  # Increased from 15s to 20s for complex queries
        )
        
        if search_results and len(search_results) > 0:
            # Format results nicely - use top 3
            formatted = []
            for result in search_results[:3]:
                # Validate result is dict before accessing
                if not isinstance(result, dict):
                    logging.warning(f"search_web: skipping non-dict result: {type(result).__name__}")
                    continue
                
                title = result.get('title', '')
                body = result.get('body', '')
                
                # Combine title and body
                if title and body:
                    formatted.append(f"{title}: {body}")
                elif title:
                    formatted.append(title)
                elif body:
                    formatted.append(body)
            
            if formatted:
                combined = " | ".join(formatted)
                
                # Limit result length to keep LLM processing fast
                if len(combined) > 800:
                    combined = combined[:800] + "..."
                
                logging.info(f"search_web: returning {len(formatted)} results ({len(combined)} chars)")
                return combined
        
        logging.warning(f"search_web: no results found for '{query}'")
        return "error: no search results found for this query."
        
    except asyncio.TimeoutError:
        logging.error(f"search_web: timeout after 20s for '{query}'")
        return "error: search timed out. please try a different query."
    except Exception as e:
        logging.error(f"search_web: error for '{query}': {type(e).__name__} - {e}")
        return "error: search temporarily unavailable."    