"""FastAPI route handlers."""
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
from loguru import logger

from tools import TOOLS, TOOL_DESCRIPTIONS


def register_routes(app: FastAPI) -> None:
    """Register all routes with the FastAPI app."""
    
    @app.post("/call-tool")
    async def call_tool(request: Request) -> Dict[str, Any]:
        """
        Call a tool by name with provided parameters.
        
        Request body:
        {
            "tool": "tool_name",
            "parameters": {...}
        }
        """
        try:
            body = await request.json()
            logger.info(f"call_tool request body: {body}")
            
            # Extract tool name and parameters (support multiple formats)
            tool_name = body.get("tool") or body.get("params", {}).get("tool")
            parameters = (
                body.get("parameters", {}) or 
                body.get("params", {}).get("parameters", {})
            )
            
            logger.info(f"Calling tool: {tool_name} with parameters: {parameters}")
            
            if not tool_name:
                return {"success": False, "error": "Tool name is required"}
            
            if tool_name not in TOOLS:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found. Available tools: {list(TOOLS.keys())}"
                }
            
            tool_func = TOOLS[tool_name]
            result = tool_func(**parameters)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Error calling tool: {err_msg}")
            return {"success": False, "error": err_msg}
    
    @app.get("/tools")
    async def list_tools() -> Dict[str, Any]:
        """
        List all available tools and their descriptions.
        """
        return {
            "tools": list(TOOLS.keys()),
            "descriptions": TOOL_DESCRIPTIONS
        }
    
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint.
        """
        return {"status": "healthy", "service": "Namma Yatri MCP Server"}

