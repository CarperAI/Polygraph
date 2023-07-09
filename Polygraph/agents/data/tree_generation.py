import json
import os
from typing import List, Dict
import requests
import json
import os
import time
import pickle
import logging


from tree import DialogueTree, DialogueNode
from utils import add_system_message, add_response_to_messages, print_dialogue
#from prompts import PromptContainer

# def sale_completed(user_messages, evaluator_prompt,
#                     branch_id, 
#                     inference_hook, 
#                     generate_kwargs = {"model": "gpt-3.5-turbo", "temperature": 1.0}):

# Open key file
API_KEY = ""
with open("../../auth/openai-api-key-l", "r") as f:
    API_KEY = f.read().strip('\n')
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

def generate_chat_completion(messages, model="gpt-3.5-turbo", temperature=1, max_tokens=None, max_retries=10, retry_interval=60):
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

    start_time = time.time()
    for attempt in range(max_retries):
        try:
            response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(data), timeout=30)
            response.raise_for_status()  # Raise an HTTPError if the response was an HTTP 4xx or 5xx
        except (requests.ConnectionError, requests.HTTPError, requests.Timeout) as e:
        #except ConnectionError as e:
            if attempt < max_retries - 1:  # Only sleep and retry if we haven't used up all our retries
                print(f"Encountered an error: {str(e)}. Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
                continue
            else:  # We've used up all our retries, time to give up
                end_time = time.time()
                print(f"Failed after {max_retries} retries in {end_time - start_time} seconds.")
                raise
        else:  # No exceptions were raised, which means the request was successful
            end_time = time.time()
            print(f"Response OK in {end_time - start_time} seconds.")
            return response.json()["choices"][0]["message"]["content"]

    # If we've fallen out of the for loop, that means we've used up all our retries
    end_time = time.time()
    print(f"Failed after {max_retries} retries in {end_time - start_time} seconds.")
    raise Exception(f"Error: Failed after {max_retries} retries")

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
            #print(f"{role}: {content}")

def sale_completed(user_messages, evaluator_prompt, branch_id, model="gpt-3.5-turbo", temperature=1.0):
    print(f"Getting sale likelihood for branch {branch_id}...")
    response = generate_chat_completion(add_system_message(user_messages, evaluator_prompt), model=model, temperature=temperature).strip().lower()
    #print(f"Message: {user_messages[-1]}\nResponse: {response}\n")
    if response in ["affirmative."]:
        print("=========== Sale completed! ===========")
        print(f"Branch ID: {branch_id}")
        return True

    return False

def get_success_likelihood(user_messages, sl_prompts, model="gpt-4", temperature=1.0):
    print("Getting success likelihood analysis...")
    response = generate_chat_completion(add_system_message(user_messages, sl_prompts["step_1"]), model=model, temperature=temperature).strip().lower()
    #print(f"Message: {user_messages[-1]}\nResponse: {response}\n")
    user_messages_updated = add_response_to_messages(user_messages, "system", response)
    print("Getting success likelihood result...")
    response = generate_chat_completion(add_system_message(user_messages_updated, sl_prompts["step_2"]), model=model, temperature=temperature).strip().lower()
    
    if response in ["yes.", "yes"]:
        return 1.0
    elif response in ["probably.", "probably"]:
        return 0.75
    elif response in ["unlikely.", "unlikely"]:
        return 0.25
    elif response in ["no.", "no"]:
        return 0.0
    elif response in ["unknown.", "unknown"]:
        return 0.5
    else:
        print(f"Error: SL response not recognized: {response}")
        return 0.5




class TreeGenerator:
    """
    Generates a dialogue tree between two agents to accomplish some goal.
    Utilizes prompts found in prompts/
    """
    def __init__(self, prompt_file="prompts/prompts.json"):

        #self.inference_hook = OpenAIHook("../auth/openai-api-key")
        #self.inference_hook.load(API_ENDPOINT="https://api.openai.com/v1/chat/completions")
        # load the prompts from the json file
        #self.prompts = PromptContainer(prompt_file)
        
        with open(prompt_file, "r") as f:
            prompts = json.load(f)
            print(prompts.keys())
            self.assistant_prompts = dict()
            self.assistant_prompts["honest"] = prompts["assistant_prompt_honest"]
            self.assistant_prompts["mildly_deceptive"] = prompts["assistant_prompt_mildly_deceptive"]
            self.assistant_prompts["deceptive"] = prompts["assistant_prompt_deceptive"]
            self.assistant_prompts["completely_deceptive"] = prompts["assistant_prompt_deceptive"]
            self.user_prompt = prompts["user_prompt"]
            self.evaluator_prompt = prompts["evaluator_prompt"]
            self.sl_prompts = dict()
            self.sl_prompts["step_1"] = prompts["sl_prompt_step_1"]
            self.sl_prompts["step_2"] = prompts["sl_prompt_step_2"]

    def explore_branches(
        self,
        assistant_messages: List[Dict[str, str]], 
        user_messages: List[Dict[str, str]], 
        parent_node: DialogueNode, 
        current_turn: int, 
        num_turns: int,
        branches: int, 
        labels: Dict[str, bool], 
        assistant_prompt: str,
        evaluator_prompt: str, 
        model="gpt-3.5-turbo", 
        temperature=1.0,
        include_success_likelihood: bool = False,
    ):  
        generate_kwargs = {"model": model, "temperature": temperature}
        if current_turn > 2:
            sale_complete = sale_completed(user_messages, evaluator_prompt, parent_node.branch_id, model, temperature)
        else:
            sale_complete = False
        if current_turn >= num_turns or sale_complete:
            labels[parent_node.branch_id] = parent_node.is_leaf()
            parent_node.set_success_pct(1.0 if sale_complete else 0.01)
            if include_success_likelihood:
                success_likelihood = get_success_likelihood(user_messages, self.sl_prompts, model=model)
                parent_node.set_success_likelihood(success_likelihood)
            return
        
        if include_success_likelihood:
            # Get the likelihood of a sale
            success_likelihood = get_success_likelihood(user_messages, self.sl_prompts, model=model)
            parent_node.set_success_likelihood(success_likelihood)

        prompt = assistant_prompt

        # Iterate over Assistant prompts
        for i in range(branches):
            start_time = time.time()
            new_branch_id = f"{parent_node.branch_id}-{i}"  # Update the branch_id
            print(f"Branch ID: {new_branch_id}")
            # Generate assistant response
            print(f"Generating assistant response...")
            assistant_response = assistant_response = generate_chat_completion(add_system_message(assistant_messages, prompt), model=model, temperature=temperature)
            #print(f"Assistant response: {assistant_response}")

            # Update the dialogues with the assistant's response
            assistant_messages_updated = add_response_to_messages(assistant_messages, "assistant", assistant_response)
            user_messages_updated = add_response_to_messages(user_messages, "assistant", assistant_response)

            # Generate user response
            print(f"Generating user response...")
            user_response = generate_chat_completion(add_system_message(user_messages_updated, "As Bob, respond to the Assistant with any remaining questions you may have. If you are ready to purchase, ask the Assistant to add the apples to your cart."), model=model, temperature=temperature)
            #print(f"User response: {user_response}")

            # Update the dialogues with the user's response
            assistant_messages_updated = add_response_to_messages(assistant_messages_updated, "user", user_response)
            user_messages_updated = add_response_to_messages(user_messages_updated, "user", user_response)

            end_time = time.time()

            # Add the child node to the tree
            print(f"Adding child node {new_branch_id} to tree after {end_time - start_time} seconds.")
            #print(f"Dialogue:")
            #print_dialogue(assistant_messages_updated)

            child_node = DialogueNode(assistant_messages_updated, new_branch_id)
            parent_node.add_child(child_node)

            self.explore_branches(
                assistant_messages_updated, 
                user_messages_updated, 
                child_node, 
                current_turn + 1, 
                num_turns,
                branches, 
                labels, 
                assistant_prompt, 
                evaluator_prompt,
                model=model, 
                temperature=temperature,
                include_success_likelihood=include_success_likelihood
                )

    
    def generate_tree(
            self, 
            num_turns=5, 
            branches=2, 
            tree_id=0, 
            data_dir=None, 
            honesty="honest", 
            model="gpt-3.5-turbo", 
            temperature=1.0,
            include_success_likelihood=False
        ):

        start_time = time.time()
        # make the directory if it doesn't exist
        if data_dir is not None:
            os.makedirs(data_dir, exist_ok=True)

        assert honesty in self.assistant_prompts.keys(), f"Invalid honesty level: {honesty}"

        initial_assistant_messages = [
            {"role": "system", "content": self.assistant_prompts[honesty]},
            {"role": "user", "content": "Hi, I'm looking to buy some apples. Can you help me with that?"}
        ]

        initial_user_messages = [
            {"role": "system", "content": self.user_prompt},
            {"role": "user", "content": initial_assistant_messages[-1]["content"]}
        ]

        root_node = DialogueNode(initial_assistant_messages, "0")
        labels = dict()

        self.explore_branches(
            initial_assistant_messages, 
            initial_user_messages, 
            root_node, 
            0, 
            num_turns,
            branches, 
            labels, 
            self.assistant_prompts[honesty], 
            self.evaluator_prompt,
            model=model, 
            temperature=temperature,
            include_success_likelihood=include_success_likelihood
        )

        # save the labels
        if data_dir is not None:
            with open(f"{data_dir}/{honesty}-tree-{tree_id}-labels.json", "w") as f:
                json.dump(labels, f)

        end_time = time.time()
        print(f"Generated tree {tree_id} in {end_time - start_time} seconds.")
        return DialogueTree(tree_id=tree_id, root=root_node, honesty=honesty)
