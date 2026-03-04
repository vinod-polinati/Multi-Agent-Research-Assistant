"""Tests for utils.py — parse_llm_json, get_llm, sanitize_input."""

from utils import parse_llm_json, sanitize_input


class TestParseLlmJson:
    def test_valid_json_object(self):
        result = parse_llm_json('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_valid_json_array(self):
        result = parse_llm_json('["a", "b", "c"]', expect_array=True)
        assert result == ["a", "b", "c"]

    def test_json_wrapped_in_text(self):
        content = 'Here is the result:\n{"score": 8, "gaps": []}\nDone!'
        result = parse_llm_json(content)
        assert result == {"score": 8, "gaps": []}

    def test_json_wrapped_in_markdown(self):
        content = '```json\n{"summary": "test"}\n```'
        result = parse_llm_json(content)
        assert result == {"summary": "test"}

    def test_array_wrapped_in_text(self):
        content = 'Questions:\n["q1", "q2"]\nEnd.'
        result = parse_llm_json(content, expect_array=True)
        assert result == ["q1", "q2"]

    def test_complete_garbage_uses_fallback_dict(self):
        result = parse_llm_json("This is not JSON at all", fallback={"default": True})
        assert result == {"default": True}

    def test_complete_garbage_uses_fallback_list(self):
        result = parse_llm_json("Not JSON", fallback=["fallback"], expect_array=True)
        assert result == ["fallback"]

    def test_no_fallback_returns_empty(self):
        assert parse_llm_json("garbage") == {}
        assert parse_llm_json("garbage", expect_array=True) == []

    def test_nested_json(self):
        content = '{"critique": {"quality_score": 7}, "follow_up_queries": ["q1"]}'
        result = parse_llm_json(content)
        assert result["critique"]["quality_score"] == 7


class TestSanitizeInput:
    def test_strips_whitespace(self):
        assert sanitize_input("  hello  world  ") == "hello world"

    def test_truncates_to_max_length(self):
        long_text = "a" * 1000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) == 100

    def test_removes_control_characters(self):
        text = "hello\x00world\x01test"
        result = sanitize_input(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "hello" in result

    def test_preserves_newlines(self):
        # Newlines get collapsed to spaces by the whitespace normalisation
        result = sanitize_input("line1\nline2")
        assert result == "line1 line2"

    def test_empty_string(self):
        assert sanitize_input("") == ""
        assert sanitize_input("   ") == ""

    def test_normal_input_unchanged(self):
        text = "Recent advances in Large Language Models"
        assert sanitize_input(text) == text
