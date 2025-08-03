# ABOUTME: OpenRouter API client for LLM operations
# ABOUTME: Handles async communication with OpenRouter API for text processing

import logging
import os

import httpx

from .config import Config

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Exception raised for OpenRouter API errors."""

    pass


class OpenRouterClient:
    """Async client for OpenRouter API interactions."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY environment variable not set")

        self.base_url = config.openrouter_base_url
        self.model = config.openrouter_model

    async def send_prompt(self, prompt: str) -> str:
        """
        Send prompt to OpenRouter API and get completion.

        Args:
            prompt: The input prompt text

        Returns:
            The completed text response

        Raises:
            OpenRouterError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
                response.raise_for_status()

                data = response.json()

                # Extract content from OpenRouter response format
                if "choices" in data and len(data["choices"]) > 0:
                    content: str = data["choices"][0]["message"]["content"]
                    logger.info(
                        f"OpenRouter API call successful, received {len(content)} characters"
                    )
                    return content
                else:
                    raise OpenRouterError("Invalid response format from OpenRouter API")

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"OpenRouter API HTTP error: {e.response.status_code} - {e.response.text}"
                )
                raise OpenRouterError(f"API request failed: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.error("OpenRouter API request timed out")
                raise OpenRouterError("API request timed out")
            except Exception as e:
                logger.error(f"OpenRouter API request failed: {e}")
                raise OpenRouterError(f"API request failed: {str(e)}")


async def create_openrouter_client(config: Config) -> OpenRouterClient:
    """
    Factory function to create OpenRouter client.

    Args:
        config: Application configuration

    Returns:
        Configured OpenRouter client

    Raises:
        OpenRouterError: If client cannot be created
    """
    return OpenRouterClient(config)
