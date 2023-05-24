import json
import os
from typing import List, Dict
import logging



from keys import InferenceHook, OpenAIHook
from tree import DialogueTree, DialogueNode
from utils import add_system_message, add_response_to_messages, print_dialogue


def sale_completed(user_messages, evaluator_prompt,
                    branch_id, 
                    inference_hook, 
                    generate_kwargs = {"model": "gpt-3.5-turbo", "temperature": 1.0}):

    response = inference_hook.infer(message=add_system_message(user_messages, evaluator_prompt), **generate_kwargs).strip().lower()
    #logging.log(f"Message: {user_messages[-1]}\nResponse: {response}\n")
    if response in ["affirmative."]:
        logging.log("=========== Sale completed! ===========")
        logging.log(f"Branch ID: {branch_id}")
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
        inference_hook : InferenceHook,
        generate_kwargs = {"model": "gpt-3.5-turbo", "temperature": 1.0}
):  
    sale_complete = sale_completed(user_messages, evaluator_prompt, parent_node.branch_id, generate_kwargs)
    if current_turn >= num_turns or sale_complete:
        labels[parent_node.branch_id] = parent_node.is_leaf()
        parent_node.set_success_pct(1.0 if sale_complete else 0.0)
        return

    # Iterate over Assistant prompts
    for i, prompt in enumerate(assistant_prompts.values()):
        new_branch_id = f"{parent_node.branch_id}-{i}"  # Update the branch_id
        logging.log(f"Branch ID: {new_branch_id}")
        # Generate assistant response
        assistant_response = inference_hook(message=add_system_message(assistant_messages, prompt), 
                                            **generate_kwargs)
        logging.log(f"Assistant response: {assistant_response}")

        # Update the dialogues with the assistant's response
        assistant_messages_updated = add_response_to_messages(assistant_messages, "assistant", assistant_response)
        user_messages_updated = add_response_to_messages(user_messages, "assistant", assistant_response)

        # Generate user response
        user_response = inference_hook(message=add_system_message(user_messages_updated, 
                                    "As Bob, inquire about the apples and respond to Sally's suggestions."), 
                                    **generate_kwargs)
        logging.log(f"User response: {user_response}")

        # Update the dialogues with the user's response
        assistant_messages_updated = add_response_to_messages(assistant_messages_updated, "user", user_response)
        user_messages_updated = add_response_to_messages(user_messages_updated, "user", user_response)

        # Add the child node to the tree
        logging.log(f"Adding child node to tree...")
        logging.log(f"Dialogue:")
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
            generate_kwargs)

class TreeGenerator:
    """
    Generates a dialogue tree between two agents to accomplish some goal.
    Utilizes prompts found in prompts/
    """
    def __init__(self, prompt_file="prompts/prompts.json"):

        self.inference_hook = OpenAIHook("../auth/openai-api-key")
        self.inference_hook.load(API_ENDPOINT="https://api.openai.com/v1/chat/completions")
        # load the prompts from the json file
        with open(prompt_file, "r") as f:
            prompts = json.load(f)
            self.assistant_prompts = dict()
            self.assistant_prompts["honest"] = prompts["assistant_prompt_honest"]
            #self.assistant_prompts["mildly_deceptive"] = prompts["assistant_prompt_mildly_deceptive"]
            self.assistant_prompts["deceptive"] = prompts["assistant_prompt_deceptive"]
            self.user_prompt = prompts["user_prompt"]
            self.evaluator_prompt = prompts["evaluator_prompt"]

    
    def generate_tree(self, num_turns=5, data_dir=None, generate_kwargs={"model": "gpt-3.5-turbo", "temperature": 1.0}):
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
            generate_kwargs
        )

        # save the labels
        if data_dir is not None:
            with open(f"{data_dir}/labels.json", "w") as f:
                json.dump(labels, f)

        return DialogueTree(root_node)