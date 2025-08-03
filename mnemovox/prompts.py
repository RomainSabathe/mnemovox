# ABOUTME: Prompt templates for LLM processing tasks
# ABOUTME: Structured prompts with XML tags for reliable output parsing

import re
from typing import Dict


class PromptTemplate:
    """Base class for LLM prompt templates with XML tag parsing."""

    def __init__(self, template: str, output_tag: str):
        self.template = template
        self.output_tag = output_tag

    def format(self, **kwargs) -> str:
        """Format the prompt template with provided variables."""
        return self.template.format(**kwargs)

    def parse_response(self, response: str) -> str:
        """Parse LLM response and extract content from XML tags."""
        pattern = rf"<{self.output_tag}>(.*?)</{self.output_tag}>"
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()
        else:
            # Fallback: return full response if no tags found
            return response.strip()


# Summarization prompt template
SUMMARIZATION_PROMPT = PromptTemplate(
    template="""You are an expert at summarizing audio transcriptions. Provide a concise summary of the following transcription.

The summary should:
- Capture the main points and key information
- Be clear and well-structured
- Be approximately 2-4 sentences long
- Focus on the most important content

Transcription to summarize:
{transcript_text}

Please provide your summary within <summarization> tags, like so:

<summarization>
Your summary here
</summarization>""",
    output_tag="summarization",
)


# Template registry for easy access
PROMPT_TEMPLATES: Dict[str, PromptTemplate] = {
    "summarization": SUMMARIZATION_PROMPT,
}


def get_prompt_template(task: str) -> PromptTemplate:
    """
    Get a prompt template by task name.

    Args:
        task: The task name (e.g., "summarization")

    Returns:
        The corresponding prompt template

    Raises:
        ValueError: If task is not found
    """
    if task not in PROMPT_TEMPLATES:
        available_tasks = ", ".join(PROMPT_TEMPLATES.keys())
        raise ValueError(f"Unknown task '{task}'. Available tasks: {available_tasks}")

    return PROMPT_TEMPLATES[task]


def format_prompt(task: str, **kwargs) -> str:
    """
    Format a prompt template with the provided variables.

    Args:
        task: The task name
        **kwargs: Variables to format into the template

    Returns:
        The formatted prompt string
    """
    template = get_prompt_template(task)
    return template.format(**kwargs)


def parse_llm_response(task: str, response: str) -> str:
    """
    Parse an LLM response and extract the relevant content.

    Args:
        task: The task name
        response: The raw LLM response

    Returns:
        The parsed content from XML tags
    """
    template = get_prompt_template(task)
    return template.parse_response(response)

