import requests
import json
import os
import time
import pickle
from tree import DialogueTree, DialogueNode

from typing import List, Dict

# Open key file
API_KEY = ""
with open("../auth/openai-api-key", "r") as f:
    API_KEY = f.read().strip('\n')
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

def generate_chat_completion(messages, model="gpt-3.5-turbo", temperature=1, max_tokens=None, max_retries=5, retry_interval=60):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if max_tokens is not None:
        data["max_tokens"] = max_tokens

    retries = 0
    while retries < max_retries:
        response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print("Response OK")
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"Error {response.status_code}: {response.text}")
            retries += 1
            if retries < max_retries:
                print(f"Retrying ({retries}/{max_retries}) after {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                raise Exception(f"Error {response.status_code}: {response.text}. Failed after {max_retries} retries.")
            

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

def sale_completed(user_messages, evaluator_prompt, branch_id, model="gpt-3.5-turbo", temperature=1.0):

    response = generate_chat_completion(add_system_message(user_messages, evaluator_prompt), model=model, temperature=temperature).strip().lower()
    #print(f"Message: {user_messages[-1]}\nResponse: {response}\n")
    if response in ["affirmative."]:
        print("=========== Sale completed! ===========")
        print(f"Branch ID: {branch_id}")
        return True

    return False

def explore_branches(
        assistant_messages: List[Dict[str, str]], 
        user_messages: List[Dict[str, str]], 
        parent_node: DialogueNode, 
        current_turn: int, 
        num_turns: int, 
        labels: Dict[str, bool], 
        assistant_prompts: Dict[str, str],
        evaluator_prompt: str, 
        model="gpt-3.5-turbo", 
        temperature=1.0
):  
    sale_complete = sale_completed(user_messages, evaluator_prompt, parent_node.branch_id, model=model)
    if current_turn >= num_turns or sale_complete:
        labels[parent_node.branch_id] = parent_node.is_leaf()
        parent_node.set_success_pct(1.0 if sale_complete else 0.0)
        return

    # Iterate over Assistant prompts
    for i, prompt in enumerate(assistant_prompts.values()):
        new_branch_id = f"{parent_node.branch_id}-{i}"  # Update the branch_id
        print(f"Branch ID: {new_branch_id}")
        # Generate assistant response
        assistant_response = generate_chat_completion(add_system_message(assistant_messages, prompt), model=model, temperature=temperature)
        print(f"Assistant response: {assistant_response}")

        # Update the dialogues with the assistant's response
        assistant_messages_updated = add_response_to_messages(assistant_messages, "assistant", assistant_response)
        user_messages_updated = add_response_to_messages(user_messages, "assistant", assistant_response)

        # Generate user response
        user_response = generate_chat_completion(add_system_message(user_messages_updated, "As Bob, inquire about the apples and respond to Sally's suggestions."), model=model, temperature=temperature)
        print(f"User response: {user_response}")

        # Update the dialogues with the user's response
        assistant_messages_updated = add_response_to_messages(assistant_messages_updated, "user", user_response)
        user_messages_updated = add_response_to_messages(user_messages_updated, "user", user_response)

        # Add the child node to the tree
        print(f"Adding child node to tree...")
        print(f"Dialogue:")
        print_dialogue(assistant_messages_updated)

        child_node = DialogueNode(assistant_messages_updated, new_branch_id)
        parent_node.add_child(child_node)

        explore_branches(
            assistant_messages_updated, 
            user_messages_updated, 
            child_node, 
            current_turn + 1, 
            num_turns, 
            labels, 
            assistant_prompts, 
            evaluator_prompt,
            model=model, 
            temperature=temperature)


class TreeGenerator:
    """
    Generates a dialogue tree between two agents to accomplish some goal.
    Utilizes prompts found in prompts/
    """
    def __init__(self, prompt_file="prompts/prompts.json"):
        # load the prompts from the json file
        with open(prompt_file, "r") as f:
            prompts = json.load(f)
            self.assistant_prompts = dict()
            self.assistant_prompts["honest"] = prompts["assistant_prompt_honest"]
            #self.assistant_prompts["mildly_deceptive"] = prompts["assistant_prompt_mildly_deceptive"]
            self.assistant_prompts["deceptive"] = prompts["assistant_prompt_deceptive"]
            self.user_prompt = prompts["user_prompt"]
            self.evaluator_prompt = prompts["evaluator_prompt"]

    
    def generate_tree(self, num_turns=5, data_dir=None, model="gpt-3.5-turbo", temperature=1.0):
        # make the directory if it doesn't exist
        if data_dir is not None:
            os.makedirs(data_dir, exist_ok=True)

        initial_assistant_messages = [
            {"role": "user", "content": "Hi, I'm looking to buy some apples. Can you help me with that?"}
        ]

        initial_user_messages = [
            {"role": "system", "content": self.user_prompt},
            {"role": "user", "content": initial_assistant_messages[-1]["content"]}
        ]

        root_node = DialogueNode(initial_assistant_messages, "0")
        labels = dict()

        explore_branches(
            initial_assistant_messages, 
            initial_user_messages, 
            root_node, 
            0, 
            num_turns, 
            labels, 
            self.assistant_prompts, 
            self.evaluator_prompt,
            model=model, 
            temperature=temperature
        )

        # save the labels
        if data_dir is not None:
            with open(f"{data_dir}/labels.json", "w") as f:
                json.dump(labels, f)

        return DialogueTree(root_node)