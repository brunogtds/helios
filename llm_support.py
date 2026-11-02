"""Provider-specific construction and shared text extraction."""
import os

CLAUDE_DEFAULT_MODEL = "claude-sonnet-5-5"


def message_text(message):
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(part if isinstance(part, str) else part.get('text', '')
                       for part in content
                       if isinstance(part, str) or
                       (isinstance(part, dict) and part.get('type', 'text') == 'text'))
    return ''


def build_claude(model_name, api_key, **options):
    key = (api_key or '').strip() or os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not key:
        raise ValueError('Anthropic API key not found. Set ANTHROPIC_API_KEY or paste a key in the UI.')
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:
        raise ValueError('Claude requires langchain-anthropic. Install the application requirements and restart.') from exc
    # New Claude models reject custom sampling parameters; use provider defaults.
    options.setdefault('max_tokens', 8192)
    return ChatAnthropic(model=model_name or CLAUDE_DEFAULT_MODEL, api_key=key, **options)
