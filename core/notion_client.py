from typing import List, Dict, Any, Optional
import httpx
from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)

class NotionClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.notion.api_key
        self.database_id = settings.notion.database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        logger.debug(f"NotionClient initialized with DB ID: {self.database_id}")

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for pages in the Notion database.
        """
        logger.info(f"Searching Notion for query: '{query}'")
        if not self.api_key or not self.database_id:
            logger.warning("Notion API Key or Database ID missing. Skipping search.")
            return []

        async with httpx.AsyncClient() as client:
            try:
                # We use the search endpoint, but filter by database if provided
                payload = {
                    "query": query,
                    "filter": {
                        "value": "database",
                        "property": "object"
                    },
                    "sort": {
                        "direction": "descending",
                        "timestamp": "last_edited_time"
                    }
                }
                
                # If database_id is specific, we might want to query the database directly or filter search
                # Notion search API searches globally, so we can't strict filter by database_id in the search payload easily 
                # unless we use the 'db' filter which is not fully supported in search
                # Instead, we will search and then filter results if needed, or query database directly.
                # However, for general "Notion Search", the search endpoint is best.
                
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                     # Simple extraction of title and url
                    title = "Untitled"
                    if "properties" in item:
                        # Try to find a title property
                        for prop in item["properties"].values():
                            if prop["id"] == "title":
                                title_list = prop.get("title", [])
                                if title_list:
                                    title = title_list[0].get("plain_text", "Untitled")
                                break
                    
                    results.append({
                        "id": item["id"],
                        "title": title,
                        "url": item.get("url"),
                        "last_edited_time": item.get("last_edited_time")
                    })
                logger.info(f"Notion search returned {len(results)} results")
                return results

            except Exception as e:
                logger.error(f"Error searching Notion: {e}", exc_info=True)
                return []

    async def create_page(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """
        Create a new page in the Notion database.
        """
        logger.info(f"Attempting to create Notion page. Title: '{title}'")
        if not self.api_key or not self.database_id:
            logger.error("Notion API Key or Database ID missing.")
            return None

        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "parent": {"database_id": self.database_id},
                    "properties": {
                        "title": { # Adjust property name if your DB uses something else, usually "Name" or "title"
                            "title": [{"text": {"content": title}}]
                        }
                    },
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": content}}]
                            }
                        }
                    ]
                }
                
                response = await client.post(
                    f"{self.base_url}/pages",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully created Notion page. URL: {data.get('url')}")
                return data

            except Exception as e:
                logger.error(f"Error creating Notion page: {e}", exc_info=True)
                return None
    async def update_page(self, page_id: str, title: Optional[str] = None, content: Optional[str] = None) -> bool:
        """
        Update a Notion page.
        - title: Updates the page title.
        - content: Appends content to the page body.
        """
        logger.info(f"Attempting to update Notion page {page_id}. Title: {title}, Content: {content}")
        if not self.api_key:
            logger.error("Notion API Key missing.")
            return False

        async with httpx.AsyncClient() as client:
            try:
                # 1. Update Properties (Title)
                if title:
                    payload = {
                        "properties": {
                            "title": { 
                                "title": [{"text": {"content": title}}]
                            }
                        }
                    }
                    response = await client.patch(
                        f"{self.base_url}/pages/{page_id}",
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully updated title for page {page_id}")

                # 2. Append Content (Children)
                if content:
                    # Notion API for appending children: PATCH https://api.notion.com/v1/blocks/{block_id}/children
                    children_payload = {
                        "children": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": content}}]
                                }
                            }
                        ]
                    }
                    response = await client.patch(
                        f"{self.base_url}/blocks/{page_id}/children",
                        headers=self.headers,
                        json=children_payload
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully appended content to page {page_id}")

                return True

            except Exception as e:
                logger.error(f"Error updating Notion page: {e}", exc_info=True)
                return False
