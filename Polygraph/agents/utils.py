import os
from typing import List, Dict

def load_prompts(prompt_dir):
    """
    Loads prompts from a directory, stored as text file deliminted by \n\n 
    """
    prompts = []
    for filename in os.listdir(prompt_dir):
        with open(os.path.join(prompt_dir, filename), 'r') as f:
            prompts.append(f.read())
    return prompts


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