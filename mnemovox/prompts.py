# ABOUTME: Prompt templates for LLM processing tasks
# ABOUTME: Structured prompts with XML tags for reliable output parsing

import re
from typing import Dict, List


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


class MultiTagPromptTemplate(PromptTemplate):
    """Prompt template that can parse multiple instances of the same XML tag."""

    def parse_response(self, response: str) -> List[str]:
        """Parse LLM response and extract content from multiple XML tags."""
        pattern = rf"<{self.output_tag}>(.*?)</{self.output_tag}>"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        if matches:
            return [match.strip() for match in matches]
        else:
            # Fallback: return full response as single item if no tags found
            return [response.strip()]


# Summarization prompt template
SUMMARIZATION_PROMPT = PromptTemplate(
    template="""You are an expert at summarizing audio transcriptions. Provide a concise summary of the following transcription.

The summary should:
- Capture the main points and key information
- Be clear and well-structured
- Be approximately 2-4 sentences long
- Focus on the most important content
- Keep the tone of voice from the original recording. If the original recording says "I"
  or "Je", use "I" and "Je".

Transcription to summarize:
{transcript_text}

Please provide your summary within <summarization> tags, like so:

<summarization>
Your summary here
</summarization>""",
    output_tag="summarization",
)


# Title assessment prompt template
TITLE_ASSESSMENT_PROMPT = MultiTagPromptTemplate(
    template="""You are an expert at analyzing audio transcriptions and creating appropriate titles. 
Based on the following transcription, suggest 2-3 potential titles that accurately 
represent the main content and would be useful for organizing and searching.

Guidelines:
- Titles should be concise (5-10 words maximum)
- Focus on the main topic or purpose of the recording
- Consider the context and setting if evident
- Avoid generic titles like "Recording" or "Audio Note"
- If the content has multiple distinct topics, reflect the primary focus

Transcription to analyze:
{transcript_text}

Please provide your title suggestions using multiple <title> tags:

<title>First title suggestion</title>
<title>Second title suggestion</title>
<title>Third title suggestion</title>""",
    output_tag="title",
)


# Formatting prompt template
FORMATTING_PROMPT = PromptTemplate(
    template="""You are an expert editor specializing in cleaning up audio transcriptions. Please 
improve the following transcription by fixing spelling mistakes, correcting grammar, 
improving sentence structure, and organizing the content into clear sections.

Tasks to perform:
- Fix spelling errors and typos
- Correct grammatical mistakes
- Improve sentence structure and flow
- Remove filler words and false starts (um, uh, like, you know)
- Add appropriate punctuation
- Break content into logical paragraphs
- Add section headers if the content covers multiple distinct topics
- Preserve the original meaning and tone
- Maintain first-person perspective if present
- The sections should be high-level and often are already indicated clearly in the text (e.g.
  "And now switching to another topic..."). Don't provide sections that are too narrow
  and specific.

Original transcription:
{transcript_text}

Please provide the formatted version within <formatted_text> tags:

<formatted_text>
Your cleaned and formatted transcription here
</formatted_text>""",
    output_tag="formatted_text",
)


# Template registry for easy access
PROMPT_TEMPLATES: Dict[str, PromptTemplate] = {
    "summarization": SUMMARIZATION_PROMPT,
    "title_assessment": TITLE_ASSESSMENT_PROMPT,
    "formatting": FORMATTING_PROMPT,
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


def parse_llm_response(task: str, response: str):
    """
    Parse an LLM response and extract the relevant content.

    Args:
        task: The task name
        response: The raw LLM response

    Returns:
        The parsed content from XML tags (str for single tag, List[str] for multi-tag)
    """
    template = get_prompt_template(task)
    return template.parse_response(response)
