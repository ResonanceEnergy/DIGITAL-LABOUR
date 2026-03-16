#!/usr/bin/env python3
"""
Azure Chatbot integration for Matrix Maximizer (the monitor).
Provides a simple wrapper around Azure OpenAI Chat completions so that the
dashboard can surface a conversational interface.  The actual model and
endpoint are configured via environment variables or passed parameters.

This module is optional; if the Azure OpenAI Python SDK isn't installed the
class is still defined but will raise ImportError when used.  It is mainly a
placeholder that can be expanded later with telemetry, message history, etc.
"""

import os
import logging

logger = logging.getLogger(__name__)

try:
    from azure.ai.openai import OpenAIClient
    from azure.identity import DefaultAzureCredential
    AZURE_AVAILABLE = True
except ImportError:  # pragma: no cover
    AZURE_AVAILABLE = False


class AzureChatbot:
    """Simple chat interface to Azure OpenAI

    Example usage:

        bot = AzureChatbot()
        resp = bot.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello from Matrix Maximizer"}
        ])
        print(resp)
    """

    def __init__(self, endpoint: str = None, model: str = "gpt-35-turbo"):
        """Initialize."""
        if not AZURE_AVAILABLE:
            raise ImportError("azure.ai.openai SDK not installed")
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not self.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint must be provided via env or argument")
        # credential will pick up AZURE_CLIENT_ID/AZURE_CLIENT_SECRET etc
        self.client = OpenAIClient(self.endpoint, DefaultAzureCredential())
        self.model = model
        logger.info(f"AzureChatbot initialized with model={self.model}")

    def chat(self, messages: list) -> str:
        """Send a conversation (list of message dicts) and receive a reply"""
        if not AZURE_AVAILABLE:
            raise ImportError("azure.ai.openai SDK not installed")
        response = self.client.chat.completions.create(
            model=self.model, messages=messages)
        content = response.choices[0].message.content
        logger.debug(f"AzureChatbot response: {content}")
        return content
