#!/usr/bin/env python3
"""
MCP Server for qualityb2bpackage.com
Provides tools for package extraction and expense registration via MCP protocol

Usage:
  python qb2b_mcp_server.py

This server exposes the following tools:
  - login: Login to qualityb2bpackage.com
  - extract_packages: Extract tour packages from the website
  - get_package_details: Get detailed info for a specific package
  - create_expense: Create an expense record
  - find_program_code: Find program code from tour code
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP library not installed. Install with: pip install mcp", file=sys.stderr)

# Import our client
from mcp_server import QualityB2BClient, CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('qb2b_mcp_server')

# Global client instance
client: Optional[QualityB2BClient] = None


async def get_client() -> QualityB2BClient:
    """Get or create the client instance"""
    global client
    if client is None:
        client = QualityB2BClient()
        await client.initialize(headless=True)
    return client


async def handle_login() -> Dict[str, Any]:
    """Handle login tool"""
    c = await get_client()
    success = await c.login()
    return {
        "success": success,
        "message": "Login successful" if success else "Login failed"
    }


async def handle_extract_packages(limit: int = 50) -> Dict[str, Any]:
    """Handle package extraction tool"""
    c = await get_client()
    packages = await c.extract_packages(limit=limit)
    return {
        "success": True,
        "count": len(packages),
        "packages": packages
    }


async def handle_get_package_details(package_id: str) -> Dict[str, Any]:
    """Handle get package details tool"""
    c = await get_client()
    details = await c.get_package_details(package_id)
    return {
        "success": True,
        "package": details
    }


async def handle_find_program_code(tour_code: str) -> Dict[str, Any]:
    """Handle find program code tool"""
    c = await get_client()
    program_code = await c.find_program_code(tour_code)
    return {
        "success": program_code is not None,
        "tour_code": tour_code,
        "program_code": program_code
    }


async def handle_create_expense(
    tour_code: str,
    program_code: str,
    amount: int,
    pax: int,
    description: str = "ค่าอุปกรณ์ออกทัวร์",
    add_company_expense: bool = True
) -> Dict[str, Any]:
    """Handle create expense tool"""
    c = await get_client()
    result = await c.create_expense(
        tour_code=tour_code,
        program_code=program_code,
        amount=amount,
        pax=pax,
        description=description,
        add_company_expense=add_company_expense
    )
    return result


# Tool definitions
TOOLS = [
    {
        "name": "login",
        "description": "Login to qualityb2bpackage.com with configured credentials",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "extract_packages",
        "description": "Extract tour packages from qualityb2bpackage.com",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of packages to extract",
                    "default": 50
                }
            },
            "required": []
        }
    },
    {
        "name": "get_package_details",
        "description": "Get detailed information for a specific tour package",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_id": {
                    "type": "string",
                    "description": "The package ID to get details for"
                }
            },
            "required": ["package_id"]
        }
    },
    {
        "name": "find_program_code",
        "description": "Find the program code for a given tour code",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tour_code": {
                    "type": "string",
                    "description": "The tour code to search for"
                }
            },
            "required": ["tour_code"]
        }
    },
    {
        "name": "create_expense",
        "description": "Create an expense record in qualityb2bpackage.com",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tour_code": {
                    "type": "string",
                    "description": "The tour code for the expense"
                },
                "program_code": {
                    "type": "string",
                    "description": "The program code for the expense"
                },
                "amount": {
                    "type": "integer",
                    "description": "The expense amount in THB"
                },
                "pax": {
                    "type": "integer",
                    "description": "Number of passengers"
                },
                "description": {
                    "type": "string",
                    "description": "Description of the expense",
                    "default": "ค่าอุปกรณ์ออกทัวร์"
                },
                "add_company_expense": {
                    "type": "boolean",
                    "description": "Whether to add company expense record",
                    "default": True
                }
            },
            "required": ["tour_code", "program_code", "amount", "pax"]
        }
    }
]


if MCP_AVAILABLE:
    # Create MCP server
    server = Server("qb2b-automation")
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools"""
        return [
            Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"]
            )
            for tool in TOOLS
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls"""
        try:
            if name == "login":
                result = await handle_login()
            elif name == "extract_packages":
                result = await handle_extract_packages(
                    limit=arguments.get("limit", 50)
                )
            elif name == "get_package_details":
                result = await handle_get_package_details(
                    package_id=arguments["package_id"]
                )
            elif name == "find_program_code":
                result = await handle_find_program_code(
                    tour_code=arguments["tour_code"]
                )
            elif name == "create_expense":
                result = await handle_create_expense(
                    tour_code=arguments["tour_code"],
                    program_code=arguments["program_code"],
                    amount=arguments["amount"],
                    pax=arguments["pax"],
                    description=arguments.get("description", "ค่าอุปกรณ์ออกทัวร์"),
                    add_company_expense=arguments.get("add_company_expense", True)
                )
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            return [TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )]


async def cleanup():
    """Cleanup resources"""
    global client
    if client:
        await client.close()
        client = None


async def main():
    """Main entry point"""
    if not MCP_AVAILABLE:
        print("Running in standalone mode (MCP not available)")
        print("\nAvailable tools:")
        for tool in TOOLS:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Run a simple test
        print("\nRunning test...")
        await handle_login()
        result = await handle_extract_packages(limit=3)
        print(f"Extracted {result['count']} packages")
        for pkg in result['packages']:
            print(f"  - {pkg.get('code')}: {pkg.get('name', '')[:50]}...")
        
        await cleanup()
        return
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
