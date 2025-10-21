"""
Internet Learning Module for AGI Codex
Enables real-time learning from internet resources and online documentation
"""
import asyncio
import aiohttp
import feedparser
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time

from ..security.manager import SecurityManager
from ..memory.episodic import EpisodicMemory
from ..memory.semantic import SemanticMemory
from ..config import AgentConfig


@dataclass
class LearningResource:
    """Represents a learning resource from the internet"""
    url: str
    title: str
    content: str
    source_type: str  # 'webpage', 'rss', 'api', 'documentation'
    tags: List[str]
    timestamp: datetime
    summary: Optional[str] = None
    relevance_score: float = 0.0


class InternetLearningEngine:
    """
    Engine for real-time learning from internet resources
    """
    def __init__(
        self,
        config: AgentConfig,
        security_manager: SecurityManager,
        episodic_memory: EpisodicMemory,
        semantic_memory: SemanticMemory
    ):
        self.config = config
        self.security_manager = security_manager
        self.episodic_memory = episodic_memory
        self.semantic_memory = semantic_memory
        self.logger = logging.getLogger(__name__)
        
        # Learning configuration from the config
        self.learning_config = config.learning
        self.system_integration_config = config.system_integration
        
        # Track learned resources to avoid duplicates
        self.learned_resources: Dict[str, datetime] = {}
        
        # RSS feeds to monitor
        self.rss_feeds = [
            "https://huggingface.co/blog/feed.xml",
            "https://openai.com/blog/rss/",
            "https://ai.googleblog.com/feeds/posts/default",
            "https://distill.pub/rss.xml"
        ]
        
        # Documentation sites to monitor
        self.documentation_sites = [
            "https://docs.python.org/3/",
            "https://pytorch.org/docs/stable/",
            "https://docs.anthropic.com/",
            "https://platform.openai.com/docs/"
        ]

    async def start_learning_cycle(self):
        """Start the continuous learning cycle"""
        self.logger.info("Starting internet learning cycle")
        
        while True:
            try:
                await self._perform_learning_cycle()
                # Wait before next cycle (configurable interval)
                await asyncio.sleep(self.learning_config.min_autonomous_interval_sec)
            except Exception as e:
                self.logger.error(f"Error in learning cycle: {e}")
                # Wait before retrying
                await asyncio.sleep(60)

    async def _perform_learning_cycle(self):
        """Perform a single learning cycle"""
        self.logger.info("Performing learning cycle")
        
        # Learn from RSS feeds
        await self._learn_from_rss_feeds()
        
        # Learn from documentation sites
        await self._learn_from_documentation()
        
        # Learn from custom sources if specified
        await self._learn_from_custom_sources()
        
        # Process learned resources and store in memory
        await self._process_learned_resources()

    async def _learn_from_rss_feeds(self):
        """Learn from RSS feeds"""
        for feed_url in self.rss_feeds:
            try:
                if not self.security_manager.validate_url(feed_url):
                    self.logger.warning(f"RSS feed URL blocked by security policy: {feed_url}")
                    continue
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(feed_url, timeout=30) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:  # Process latest 5 entries
                                if self._should_learn_resource(entry.link):
                                    resource = await self._extract_resource_from_feed_entry(entry)
                                    if resource:
                                        self.learned_resources[resource.url] = datetime.now()
                                        # Store in semantic memory for knowledge retention
                                        await self._store_resource_in_memory(resource)
            except Exception as e:
                self.logger.error(f"Error processing RSS feed {feed_url}: {e}")

    async def _learn_from_documentation(self):
        """Learn from documentation sites"""
        for doc_site in self.documentation_sites:
            try:
                if not self.security_manager.validate_url(doc_site):
                    self.logger.warning(f"Documentation site URL blocked by security policy: {doc_site}")
                    continue
                
                # Get the main page
                content = await self._fetch_webpage_content(doc_site)
                if content:
                    # Extract important sections from documentation
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Look for recent updates or new sections
                    recent_updates = soup.find_all(['div', 'section'], class_=['update', 'news', 'changelog'])
                    
                    for update in recent_updates:
                        title_elem = update.find(['h1', 'h2', 'h3'])
                        title = title_elem.get_text().strip() if title_elem else "Documentation Update"
                        
                        content_text = update.get_text().strip()[:2000]  # Limit content size
                        
                        resource = LearningResource(
                            url=doc_site,
                            title=title,
                            content=content_text,
                            source_type='documentation',
                            tags=['documentation', 'update'],
                            timestamp=datetime.now()
                        )
                        
                        if self._should_learn_resource(resource.url):
                            self.learned_resources[resource.url] = datetime.now()
                            await self._store_resource_in_memory(resource)
            except Exception as e:
                self.logger.error(f"Error processing documentation site {doc_site}: {e}")

    async def _learn_from_custom_sources(self):
        """Learn from custom sources specified in configuration"""
        # This could be extended to learn from user-specified sources
        pass

    def _should_learn_resource(self, url: str) -> bool:
        """Determine if a resource should be learned based on recency and relevance"""
        if url in self.learned_resources:
            # Don't re-learn resources within a certain time period
            last_learned = self.learned_resources[url]
            if datetime.now() - last_learned < timedelta(hours=24):
                return False
        return True

    async def _extract_resource_from_feed_entry(self, entry) -> Optional[LearningResource]:
        """Extract a learning resource from an RSS feed entry"""
        try:
            # Fetch the full content of the article
            full_content = await self._fetch_webpage_content(entry.link)
            if not full_content:
                return None
            
            # Create a summary of the content
            summary = self._create_summary(full_content)
            
            # Extract tags/keywords
            tags = self._extract_tags(entry.title + " " + entry.get('summary', ''))
            
            return LearningResource(
                url=entry.link,
                title=entry.title,
                content=full_content,
                source_type='webpage',
                tags=tags,
                timestamp=datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now(),
                summary=summary
            )
        except Exception as e:
            self.logger.error(f"Error extracting resource from feed entry: {e}")
            return None

    async def _fetch_webpage_content(self, url: str) -> Optional[str]:
        """Fetch content from a webpage"""
        try:
            if not self.security_manager.validate_url(url):
                self.logger.warning(f"Webpage URL blocked by security policy: {url}")
                return None
            
            # Use the API integration tool through the security manager
            headers = {'User-Agent': 'AGI-Codex-Learning-Agent/1.0'}
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                self.logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching webpage content from {url}: {e}")
            return None

    def _create_summary(self, content: str) -> str:
        """Create a summary of the content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Return first 500 characters as summary
            return text[:500] + "..." if len(text) > 500 else text
        except Exception as e:
            self.logger.error(f"Error creating summary: {e}")
            return content[:500] + "..." if len(content) > 500 else content

    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text"""
        # Simple keyword extraction - this could be enhanced with NLP
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        words = text.lower().split()
        tags = []
        
        for word in words:
            clean_word = word.strip('.,!?";:()[]{}')
            if len(clean_word) > 4 and clean_word not in common_words and clean_word.isalpha():
                if clean_word not in tags:
                    tags.append(clean_word)
        
        # Limit to top 5 tags
        return tags[:5]

    async def _store_resource_in_memory(self, resource: LearningResource):
        """Store the learned resource in memory systems"""
        try:
            # Store in semantic memory as knowledge
            semantic_entry = {
                "type": "learning_resource",
                "title": resource.title,
                "content": resource.content,
                "url": resource.url,
                "source_type": resource.source_type,
                "tags": resource.tags,
                "timestamp": resource.timestamp.isoformat(),
                "summary": resource.summary
            }
            
            await self.semantic_memory.store(f"internet_learning::{resource.url}", semantic_entry)
            
            # Store in episodic memory as a learning event
            episodic_entry = {
                "event_type": "internet_learning",
                "resource_url": resource.url,
                "resource_title": resource.title,
                "learned_at": datetime.now().isoformat(),
                "tags": resource.tags
            }
            
            await self.episodic_memory.store(episodic_entry)
            
            self.logger.info(f"Learned and stored resource: {resource.title}")
        except Exception as e:
            self.logger.error(f"Error storing resource in memory: {e}")

    async def _process_learned_resources(self):
        """Process and consolidate learned resources"""
        # This method could implement more advanced processing like:
        # - Identifying patterns across resources
        # - Creating knowledge graphs
        # - Updating learning models
        # - Generating insights
        pass

    async def query_internet_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Query the learned internet knowledge"""
        try:
            # Search in semantic memory for relevant resources
            results = await self.semantic_memory.search(query, namespace="internet_learning")
            
            # Format results
            formatted_results = []
            for result in results:
                if isinstance(result, dict) and 'content' in result:
                    formatted_results.append({
                        "title": result.get("title", "Unknown"),
                        "url": result.get("url", ""),
                        "content": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"],
                        "timestamp": result.get("timestamp", ""),
                        "relevance": result.get("_relevance", 1.0)
                    })
            
            return formatted_results
        except Exception as e:
            self.logger.error(f"Error querying internet knowledge: {e}")
            return []


class RealTimeLearningManager:
    """
    Manager for real-time learning from internet resources
    """
    def __init__(
        self,
        config: AgentConfig,
        security_manager: SecurityManager,
        episodic_memory: EpisodicMemory,
        semantic_memory: SemanticMemory
    ):
        self.learning_engine = InternetLearningEngine(
            config=config,
            security_manager=security_manager,
            episodic_memory=episodic_memory,
            semantic_memory=semantic_memory
        )
        self.logger = logging.getLogger(__name__)

    async def start_learning(self):
        """Start the real-time learning process"""
        self.logger.info("Starting real-time internet learning")
        await self.learning_engine.start_learning_cycle()

    async def query_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Query the accumulated internet knowledge"""
        return await self.learning_engine.query_internet_knowledge(query)

    def add_custom_source(self, url: str, source_type: str = "webpage"):
        """Add a custom source for learning"""
        if source_type == "rss":
            self.learning_engine.rss_feeds.append(url)
        elif source_type == "documentation":
            self.learning_engine.documentation_sites.append(url)
        else:
            # Could implement other source types
            pass