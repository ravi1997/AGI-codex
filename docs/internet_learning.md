# Internet Learning System for AGI Codex

This document provides an overview of the internet learning capabilities of the AGI Codex project, enabling real-time learning from internet resources and online documentation.

## Overview

The Internet Learning System enables the AGI to continuously learn from internet resources including RSS feeds, documentation sites, and other web content. This allows the system to stay current with developments in AI, technology, and other relevant fields.

## Components

### 1. InternetLearningEngine

The core engine that performs continuous learning from internet resources.

**Features:**
- Monitors RSS feeds for new content
- Scans documentation sites for updates
- Processes and summarizes learned content
- Stores knowledge in memory systems
- Implements security validation for all resources

### 2. RealTimeLearningManager

The manager that orchestrates the learning process and provides interfaces for querying learned knowledge.

**Features:**
- Starts and manages the learning cycle
- Provides query interface for learned knowledge
- Allows adding custom learning sources
- Implements learning configuration

## Learning Sources

### RSS Feeds
The system monitors the following RSS feeds by default:
- Hugging Face Blog
- OpenAI Blog
- Google AI Blog
- Distill Publication
- Stability AI News
- Anthropic News

### Documentation Sites
The system scans the following documentation sites:
- Python Documentation
- PyTorch Documentation
- Anthropic Documentation
- OpenAI API Documentation
- Mistral AI Documentation
- Cohere Documentation

## Configuration

The internet learning system is configured through `config/internet_learning.yaml`. Key configuration options include:

### General Settings
- `enabled`: Whether internet learning is enabled
- `learning_cycle_interval`: How often to perform learning cycles (in seconds)
- `max_content_size_kb`: Maximum content size to process
- `request_timeout_seconds`: Timeout for web requests
- `max_concurrent_requests`: Maximum concurrent web requests

### Security Settings
- `allowed_domains`: Domains the AGI is allowed to access
- `blocked_domains`: Domains that are blocked
- `content_filters`: Keywords that trigger content filtering

### Learning Settings
- `relevance_threshold`: Minimum relevance score for content
- `content_summary_enabled`: Whether to create content summaries
- `content_summary_length`: Length of content summaries
- `duplicate_detection_window_hours`: Time window for detecting duplicate content
- `knowledge_retention_days`: How long to retain learned knowledge

### Storage Settings
- `max_entries`: Maximum number of learned entries to store
- `cleanup_enabled`: Whether to automatically clean up old entries
- `cleanup_interval_hours`: How often to perform cleanup

## Security Model

The internet learning system implements multiple layers of security:

1. **Domain Validation**: Only allows access to pre-approved domains
2. **Content Filtering**: Filters out content containing prohibited keywords
3. **Size Limiting**: Limits content size to prevent resource exhaustion
4. **Request Timeout**: Prevents hanging requests
5. **Rate Limiting**: Limits concurrent requests to prevent server overload

## Usage Examples

### Starting the Learning Process
```python
from src.agi_core.learning.internet_learning import RealTimeLearningManager

learning_manager = RealTimeLearningManager(
    config=agent_config,
    security_manager=security_manager,
    episodic_memory=episodic_memory,
    semantic_memory=semantic_memory
)

# Start continuous learning
await learning_manager.start_learning()
```

### Querying Learned Knowledge
```python
# Query learned knowledge
results = await learning_manager.query_knowledge("machine learning advancements")
for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"Content: {result['content']}")
```

### Adding Custom Learning Sources
```python
# Add a custom RSS feed
learning_manager.add_custom_source("https://example.com/feed.xml", "rss")

# Add a custom documentation site
learning_manager.add_custom_source("https://docs.example.com/", "documentation")
```

## Best Practices

1. **Curated Sources**: Only add trusted and relevant sources to the learning system
2. **Security First**: Regularly review and update security configurations
3. **Resource Management**: Monitor resource usage and adjust limits as needed
4. **Privacy Protection**: Ensure that learned content doesn't contain sensitive information
5. **Relevance Filtering**: Adjust relevance thresholds to focus on high-value content

## Troubleshooting

### Learning Not Happening
- Verify that internet learning is enabled in the configuration
- Check that the security manager allows web access
- Verify network connectivity and domain access

### Performance Issues
- Reduce the number of monitored sources
- Increase the learning cycle interval
- Adjust content size limits

### Security Blocks
- Review the allowed domains list
- Check for overly restrictive content filters
- Verify URL validation settings

## Extending the System

The internet learning system can be extended by:
1. Adding new source types (e.g., social media, academic papers)
2. Implementing more sophisticated content analysis
3. Adding domain-specific learning modules
4. Enhancing the knowledge representation and storage