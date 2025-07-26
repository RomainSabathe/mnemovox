# ABOUTME: Tests for search excerpt highlighting functionality
# ABOUTME: Verifies _generate_excerpt preserves FTS highlighting in search results


def test_excerpt_highlighting_with_fts_markup():
    """Test excerpt generation with FTS <mark> tags."""
    # Test data with FTS highlighting
    highlighted_text = "This is a sample <mark>transcript</mark> with some highlighted <mark>content</mark> for testing purposes."
    search_term = "transcript"

    # Expected: excerpt should preserve the <mark> tags
    expected_contains = "<mark>transcript</mark>"

    # Import and call _generate_excerpt directly
    # For now, this will fail until we implement the function
    from mnemovox.app import _generate_excerpt_with_highlighting  # noqa: E402

    result = _generate_excerpt_with_highlighting(highlighted_text, search_term)

    assert expected_contains in result
    assert len(result) <= 200  # Default max length
    assert "..." in result or len(highlighted_text) <= 200


def test_excerpt_highlighting_fallback_without_fts():
    """Test excerpt generation falls back to manual highlighting when no FTS markup."""
    clean_text = "This is a sample transcript with some content for testing purposes."
    search_term = "transcript"

    # Expected: should add <mark> tags around the search term
    expected_contains = "<mark>transcript</mark>"

    from mnemovox.app import _generate_excerpt_with_highlighting  # noqa: E402

    result = _generate_excerpt_with_highlighting(clean_text, search_term)

    assert expected_contains in result
    assert len(result) <= 200


def test_excerpt_highlighting_multiple_terms():
    """Test excerpt generation with multiple highlighted terms."""
    highlighted_text = "The <mark>audio</mark> recording contains <mark>important</mark> information about the meeting."
    search_term = "audio"

    from mnemovox.app import _generate_excerpt_with_highlighting

    result = _generate_excerpt_with_highlighting(highlighted_text, search_term)

    # Should preserve existing highlighting
    assert "<mark>audio</mark>" in result
    assert "<mark>important</mark>" in result


def test_excerpt_highlighting_case_insensitive():
    """Test excerpt generation is case insensitive."""
    highlighted_text = (
        "The meeting discussed <mark>IMPORTANT</mark> topics about the project."
    )
    search_term = "important"  # lowercase search term

    from mnemovox.app import _generate_excerpt_with_highlighting

    result = _generate_excerpt_with_highlighting(highlighted_text, search_term)

    assert "<mark>IMPORTANT</mark>" in result


def test_excerpt_highlighting_word_boundaries():
    """Test excerpt generation respects word boundaries."""
    highlighted_text = "This is a very long transcript with many words that contains the highlighted <mark>search</mark> term somewhere in the middle of a much longer text that should be truncated properly while preserving the highlighting and word boundaries."
    search_term = "search"

    from mnemovox.app import _generate_excerpt_with_highlighting

    result = _generate_excerpt_with_highlighting(
        highlighted_text, search_term, max_length=100
    )

    assert "<mark>search</mark>" in result
    assert len(result) <= 120  # Allow some margin for ellipsis and markup
    assert result.startswith("...") or not highlighted_text.startswith(
        result.split()[0]
    )
