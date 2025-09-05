# Standard library imports
import os
import json
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Third-party imports
import httpx
from dotenv import load_dotenv
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Load environment variables
load_dotenv()

class GongMCPServer:
    def __init__(self):
        self.server = Server("gong-server")
        self.access_key = os.getenv("GONG_ACCESS_KEY")
        self.access_key_secret = os.getenv("GONG_ACCESS_KEY_SECRET")
        self.base_url = "https://api.gong.io/v2"
        
        if not self.access_key or not self.access_key_secret:
            raise ValueError("Please set GONG_ACCESS_KEY and GONG_ACCESS_KEY_SECRET environment variables")
        
        # Setup tool handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List all available Gong tools"""
            return [
                types.Tool(
                    name="search_calls",
                    description="Search for Gong calls with filters. Returns call recordings and metadata.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days back to search (default: 7)",
                                "default": 7
                            },
                            "owner_email": {
                                "type": "string",
                                "description": "Filter by call owner email (optional)"
                            },
                            "min_duration": {
                                "type": "integer",
                                "description": "Minimum call duration in seconds (optional)"
                            },
                            "keyword": {
                                "type": "string",
                                "description": "Keyword to search in transcripts (optional)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_call_transcript",
                    description="Get the full transcript of a specific Gong call",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "call_id": {
                                "type": "string",
                                "description": "The Gong call ID"
                            }
                        },
                        "required": ["call_id"]
                    }
                ),
                types.Tool(
                    name="get_call_stats",
                    description="Get statistics about a specific call (talk ratio, questions asked, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "call_id": {
                                "type": "string",
                                "description": "The Gong call ID"
                            }
                        },
                        "required": ["call_id"]
                    }
                ),
                types.Tool(
                    name="list_scorecards",
                    description="List all available Gong scorecards and their results",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days back to check scores (default: 30)",
                                "default": 30
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Optional[Dict]
        ) -> list[types.TextContent]:
            """Handle tool execution"""
            try:
                if name == "search_calls":
                    result = await self.search_calls(arguments or {})
                elif name == "get_call_transcript":
                    if not arguments or "call_id" not in arguments:
                        raise ValueError("call_id is required for get_call_transcript")
                    result = await self.get_call_transcript(arguments["call_id"])
                elif name == "get_call_stats":
                    if not arguments or "call_id" not in arguments:
                        raise ValueError("call_id is required for get_call_stats")
                    result = await self.get_call_stats(arguments["call_id"])
                elif name == "list_scorecards":
                    result = await self.list_scorecards(arguments or {})
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    async def make_gong_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make authenticated request to Gong API"""
        # Create Basic Auth header
        credentials = f"{self.access_key}:{self.access_key_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=f"{self.base_url}{endpoint}",
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Gong API error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ValueError(f"Request failed: {str(e)}")
    
    async def search_calls(self, params: Dict) -> Dict:
        """Search for Gong calls"""
        days_back = params.get("days_back", 7)
        from_date = (datetime.now() - timedelta(days=days_back)).isoformat() + "Z"
        to_date = datetime.now().isoformat() + "Z" 
        
        request_body = {
            "filter": {
                "fromDateTime": from_date,
                "toDateTime": to_date
            }
        }
        
        # Add optional filters
        if params.get("owner_email"):
            request_body["filter"]["ownerEmails"] = [params["owner_email"]]
        
        if params.get("min_duration"):
            request_body["filter"]["minDuration"] = params["min_duration"]
        
        # Make API call
        result = await self.make_gong_request(
            "GET",
            "/calls",
            params={
                "fromDateTime": from_date,
                "toDateTime": to_date
        }
        )
        
        # Format the response
        calls = []
        for call in result.get("calls", [])[:10]:  # Limit to 10 calls
            calls.append({
                "id": call["id"],
                "title": call.get("title", "Untitled"),
                "date": call.get("started"),
                "duration": call.get("duration"),
                "owner": call.get("owner", {}).get("emailAddress"),
                "participants": [p.get("emailAddress") for p in call.get("participants", [])],
                "url": call.get("url")
            })
        
        return {
            "found": len(calls),
            "calls": calls
        }
    
    async def get_call_transcript(self, call_id: str) -> Dict:
        """Get transcript for a specific call"""
        result = await self.make_gong_request(
            "POST",
            f"/calls/transcript",
            json={"filter": {"callIds": [call_id]}}
        )
        
        # Parse the transcript
        transcripts = result.get("callTranscripts", [])
        if not transcripts:
            return {"error": "No transcript found for this call"}
        
        sentences = transcripts[0].get("sentences", [])
        
        # Format into readable conversation
        conversation = []
        for sentence in sentences[:50]:  # Limit for readability
            conversation.append({
                "speaker": sentence.get("speakerName", "Unknown"),
                "text": sentence.get("text", ""),
                "time": sentence.get("start", 0)
            })
        
        return {
            "call_id": call_id,
            "conversation": conversation,
            "total_sentences": len(sentences),
            "showing": min(50, len(sentences))
        }
    
    async def get_call_stats(self, call_id: str) -> Dict:
        """Get statistics for a specific call"""
        result = await self.make_gong_request(
            "GET",
            f"/calls/{call_id}"
        )
        
        call = result.get("call", {})
        stats = call.get("stats", {})
        
        return {
            "call_id": call_id,
            "title": call.get("title"),
            "duration_seconds": call.get("duration"),
            "talk_ratio": stats.get("talkRatio"),
            "longest_monologue": stats.get("longestMonologue"),
            "questions_asked": stats.get("questionsAsked"),
            "engagement_score": stats.get("engagementScore"),
            "sentiment": call.get("sentiment")
        }
    
    async def list_scorecards(self, params: Dict) -> Dict:
        """List scorecard results"""
        days_back = params.get("days_back", 30)
        from_date = (datetime.now() - timedelta(days=days_back)).isoformat() + "Z"
        
        result = await self.make_gong_request(
            "POST",
            "/stats/scorecards",
            json={
                "filter": {
                    "fromDateTime": from_date,
                    "toDateTime": datetime.now().isoformat() + "Z"
                }
            }
        )
        
        return {
            "period": f"Last {days_back} days",
            "scorecards": result.get("scorecards", [])
        }
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="gong-mcp",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

if __name__ == "__main__":
    server = GongMCPServer()
    asyncio.run(server.run())