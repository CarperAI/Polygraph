from typing import List, Dict

def add_system_message(messages: List[Dict[str, str]], content: str) -> List[Dict[str, str]]:
    messages_copy = messages.copy()
    messages_copy.append({"role": "system", "content": content})
    return messages_copy

def add_response_to_messages(messages: List[Dict[str, str]], role: str, response: str) -> List[Dict[str, str]]:
    messages_copy = messages.copy()
    messages_copy.append({"role": role, "content": response})
    return messages_copy

def print_dialogue(messages, incl_system=False):
    for message in messages:
        if message["role"] != "system" or incl_system:
            role = message["role"].capitalize()
            content = message["content"]
            print(f"{role}: {content}")