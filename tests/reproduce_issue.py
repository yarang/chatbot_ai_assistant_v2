import pytest
from langchain_core.messages import AIMessage
from services.streaming_helper import extract_text_from_stream_event

def test_reproduce_raw_json_output():
    # Simulate the event that causes the issue
    # Content is a list of dicts, which happens with multimodal models
    content_list = [
        {'type': 'text', 'text': "Hello world"},
        {'type': 'text', 'text': " This is a test."}
    ]
    
    event = {
        "GeneralAssistant": {
            "messages": [
                AIMessage(content=content_list)
            ]
        }
    }
    
    result = extract_text_from_stream_event(event)
    
    # CURRENT BEHAVIOR (BUG): result is string representation of list
    print(f"Result: {result}")
    
    # EXPECTED BEHAVIOR: result should be "Hello world This is a test."
    # If this assertion fails, it means the bug is present (or fixed if we invert logic, but here we want to see it fail or check current state)
    
    # We assert what we WANT. If it fails, we know we need to fix it.
    assert result == "Hello world This is a test."
