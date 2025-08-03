"""
Tests for OpenRouter integration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os

from mnemovox.openrouter import OpenRouterClient, OpenRouterError, create_openrouter_client
from mnemovox.config import Config
from mnemovox.prompts import format_prompt, parse_llm_response, get_prompt_template, MultiTagPromptTemplate
from mnemovox.llm_processor import process_recording_with_llm, assess_recording_title, format_recording


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

    def test_get_title_assessment_template(self):
        """Test getting the title assessment prompt template."""
        template = get_prompt_template("title_assessment")
        assert template is not None
        assert template.output_tag == "title"
        assert isinstance(template, MultiTagPromptTemplate)

    def test_get_formatting_template(self):
        """Test getting the formatting prompt template."""
        template = get_prompt_template("formatting")
        assert template is not None
        assert template.output_tag == "formatted_text"

    def test_format_title_assessment_prompt(self):
        """Test formatting the title assessment prompt."""
        prompt = format_prompt("title_assessment", transcript_text="Test transcript")
        assert "Test transcript" in prompt
        assert "<title>" in prompt
        assert "5-10 words maximum" in prompt

    def test_format_formatting_prompt(self):
        """Test formatting the formatting prompt."""
        prompt = format_prompt("formatting", transcript_text="Test transcript")
        assert "Test transcript" in prompt
        assert "<formatted_text>" in prompt
        assert "spelling errors" in prompt

    def test_parse_multiple_title_tags(self):
        """Test parsing multiple title tags from LLM response."""
        response = """Here are some titles:
        <title>First Title</title>
        Some other text
        <title>Second Title</title>
        <title>Third Title</title>
        """
        result = parse_llm_response("title_assessment", response)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == "First Title"
        assert result[1] == "Second Title"
        assert result[2] == "Third Title"

    def test_parse_single_title_tag(self):
        """Test parsing single title tag from LLM response."""
        response = "Some text <title>Only Title</title> more text"
        result = parse_llm_response("title_assessment", response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "Only Title"

    def test_parse_title_response_without_tags(self):
        """Test parsing title response without XML tags (fallback)."""
        response = "This is just plain text without tags"
        result = parse_llm_response("title_assessment", response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "This is just plain text without tags"

    def test_parse_formatting_response(self):
        """Test parsing formatting response with XML tags."""
        response = "Some text <formatted_text>This is the cleaned text</formatted_text> more text"
        result = parse_llm_response("formatting", response)
        assert result == "This is the cleaned text"


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

    @pytest.mark.asyncio
    async def test_process_recording_title_assessment(self):
        """Test successful title assessment processing."""
        # Mock database recording
        mock_recording = MagicMock()
        mock_recording.transcript_text = "This is a test recording about machine learning"
        mock_recording.transcript_status = "complete"
        
        # Mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_recording
        
        # Mock OpenRouter client
        mock_client = AsyncMock()
        mock_client.send_prompt.return_value = """
        <title>Machine Learning Discussion</title>
        <title>AI Topics Overview</title>
        <title>Tech Talk Session</title>
        """
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.create_openrouter_client", return_value=mock_client):
                with patch("mnemovox.llm_processor.get_config"):
                    result = await process_recording_with_llm(1, "title_assessment", "test.db")
                    
                    assert isinstance(result, list)
                    assert len(result) == 3
                    assert "Machine Learning Discussion" in result
                    assert "AI Topics Overview" in result
                    assert "Tech Talk Session" in result
                    mock_client.send_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_recording_formatting(self):
        """Test successful formatting processing."""
        # Mock database recording
        mock_recording = MagicMock()
        mock_recording.transcript_text = "um, this is like, a test recording, you know"
        mock_recording.transcript_status = "complete"
        
        # Mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_recording
        
        # Mock OpenRouter client
        mock_client = AsyncMock()
        mock_client.send_prompt.return_value = "<formatted_text>This is a test recording.</formatted_text>"
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.create_openrouter_client", return_value=mock_client):
                with patch("mnemovox.llm_processor.get_config"):
                    result = await process_recording_with_llm(1, "formatting", "test.db")
                    
                    assert result == "This is a test recording."
                    mock_client.send_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_assess_recording_title_success(self):
        """Test successful title assessment background task."""
        # Mock database recording
        mock_recording = MagicMock()
        mock_recording.transcript_text = "Test transcript"
        mock_recording.transcript_status = "complete"
        mock_recording.original_filename = "test.wav"
        
        # Mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_recording
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.process_recording_with_llm", return_value=["Title 1", "Title 2"]) as mock_process:
                with patch("mnemovox.llm_processor.logger") as mock_logger:
                    await assess_recording_title(1, "test.db")
                    
                    mock_process.assert_called_once_with(1, "title_assessment", "test.db")
                    mock_logger.info.assert_called_once()
                    
                    # Check that logger was called with title information
                    call_args = mock_logger.info.call_args
                    assert "title assessment completed" in call_args[0][0]
                    assert "Title 1 | Title 2" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_format_recording_success(self):
        """Test successful formatting background task."""
        # Mock database recording
        mock_recording = MagicMock()
        mock_recording.transcript_text = "Original transcript"
        mock_recording.transcript_status = "complete"
        mock_recording.original_filename = "test.wav"
        
        # Mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_recording
        
        with patch("mnemovox.llm_processor.get_session", return_value=mock_session):
            with patch("mnemovox.llm_processor.process_recording_with_llm", return_value="Formatted transcript") as mock_process:
                with patch("mnemovox.llm_processor.logger") as mock_logger:
                    await format_recording(1, "test.db")
                    
                    mock_process.assert_called_once_with(1, "formatting", "test.db")
                    mock_logger.info.assert_called_once()
                    
                    # Check that logger was called with formatting information
                    call_args = mock_logger.info.call_args
                    assert "formatting completed" in call_args[0][0]
                    assert "Formatted transcript" in call_args[0][0]