"""
Tests for OpenRouter integration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os

from mnemovox.openrouter import OpenRouterClient, OpenRouterError, create_openrouter_client
from mnemovox.config import Config
from mnemovox.prompts import format_prompt, parse_llm_response, get_prompt_template
from mnemovox.llm_processor import process_recording_with_llm


class TestOpenRouterClient:
    """Test cases for OpenRouter API client."""

    def test_client_initialization_without_api_key(self):
        """Test that client initialization fails without API key."""
        config = Config()
        
        # Ensure no API key is set
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(OpenRouterError, match="OPENROUTER_API_KEY environment variable not set"):
                OpenRouterClient(config)

    def test_client_initialization_with_api_key(self):
        """Test successful client initialization with API key."""
        config = Config()
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            client = OpenRouterClient(config)
            assert client.api_key == "test-key"
            assert client.model == config.openrouter_model
            assert client.base_url == config.openrouter_base_url

    @pytest.mark.asyncio
    async def test_send_prompt_success(self):
        """Test successful prompt sending."""
        config = Config()
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            client = OpenRouterClient(config)
            
            # Mock successful HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "This is a test summary."
                        }
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                result = await client.send_prompt("Test prompt")
                
                assert result == "This is a test summary."
                mock_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_prompt_http_error(self):
        """Test prompt sending with HTTP error."""
        config = Config()
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            client = OpenRouterClient(config)
            
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.side_effect = Exception("HTTP Error")
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                with pytest.raises(OpenRouterError, match="API request failed"):
                    await client.send_prompt("Test prompt")

    @pytest.mark.asyncio
    async def test_create_openrouter_client_factory(self):
        """Test client factory function."""
        config = Config()
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            client = await create_openrouter_client(config)
            assert isinstance(client, OpenRouterClient)
            assert client.api_key == "test-key"


class TestPromptTemplates:
    """Test cases for prompt templates."""

    def test_get_prompt_template_success(self):
        """Test getting a valid prompt template."""
        template = get_prompt_template("summarization")
        assert template is not None
        assert template.output_tag == "summarization"

    def test_get_prompt_template_invalid(self):
        """Test getting an invalid prompt template."""
        with pytest.raises(ValueError, match="Unknown task 'invalid'"):
            get_prompt_template("invalid")

    def test_format_prompt(self):
        """Test formatting a prompt with variables."""
        prompt = format_prompt("summarization", transcript_text="Test transcript")
        assert "Test transcript" in prompt
        assert "<summarization>" in prompt

    def test_parse_llm_response_with_tags(self):
        """Test parsing LLM response with XML tags."""
        response = "Some text <summarization>This is the summary</summarization> more text"
        result = parse_llm_response("summarization", response)
        assert result == "This is the summary"

    def test_parse_llm_response_without_tags(self):
        """Test parsing LLM response without XML tags (fallback)."""
        response = "This is just plain text"
        result = parse_llm_response("summarization", response)
        assert result == "This is just plain text"


class TestLLMProcessor:
    """Test cases for LLM processing functions."""

    @pytest.mark.asyncio
    async def test_process_recording_with_llm_success(self):
        """Test successful recording processing."""
        # Mock database recording
        mock_recording = MagicMock()
        mock_recording.transcript_text = "Test transcript"
        mock_recording.transcript_status = "complete"
        
        # Mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_recording
        
        # Mock OpenRouter client
        mock_client = AsyncMock()
        mock_client.send_prompt.return_value = "<summarization>Test summary</summarization>"
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.create_openrouter_client", return_value=mock_client):
                with patch("mnemovox.llm_processor.get_config"):
                    result = await process_recording_with_llm(1, "summarization", "test.db")
                    
                    assert result == "Test summary"
                    mock_client.send_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_recording_not_found(self):
        """Test processing with non-existent recording."""
        # Mock session returning None
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.get_config"):
                result = await process_recording_with_llm(999, "summarization", "test.db")
                
                assert result is None

    @pytest.mark.asyncio
    async def test_process_recording_no_transcript(self):
        """Test processing recording without transcript."""
        # Mock recording without transcript
        mock_recording = MagicMock()
        mock_recording.transcript_text = None
        mock_recording.transcript_status = "pending"
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_recording
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.get_config"):
                result = await process_recording_with_llm(1, "summarization", "test.db")
                
                assert result is None