import requests
import json
import os
import time


class DialogueNode:
    def __init__(self, dialogue, branch_id) -> None:
        self.dialogue = dialogue
        self.branch_id = branch_id
        self.children = []
        self.child_count = 0
        self.success_pct = None

    def add_child(self, node):
        self.children.append(node)
        self.child_count += 1

    def is_leaf(self):
        return len(self.children) == 0

    def set_success_pct(self, success_pct) -> None:
        self.success_pct = success_pct

    def get_success_pct(self) -> float:
        """ Returns the success percentage of this node.
        If the success percentage is not set, it will be calculated recursively.

        Returns:
            float: The success percentage of this node.
        """
        print(f"Getting success percentage for node {self.branch_id}")
        print(f"Success percentage is {self.success_pct}")
        print(f"Is leaf? {self.is_leaf()}")
        print(f"children: {self.children}")
        if self.is_leaf():
            return 0 if not self.success_pct else self.success_pct
        
        if self.success_pct is None:
            self.success_pct = 0
            for c in self.children:
                self.success_pct += c.get_success_pct()
            self.success_pct /= self.child_count

        return self.success_pct

    def get_formatted_dialogue(self, include_final_user_response=False) -> str:
        """ Returns the dialogue of this node in a formatted string, omitting the system messages and the final assistant message.

        Returns:
            str: The formatted dialogue of this node.
        """
        dialogue_string = ""
        message_count = len(self.dialogue)
        message_counter = 0
        for message in self.dialogue:
            message_counter += 1
            if message["role"] != "system" and (message_counter < message_count  or include_final_user_response):
                role = message["role"].capitalize()
                content = message["content"]
                dialogue_string += f"{role}: {content}\n"

        return dialogue_string

    def to_dict(self):
        """ Returns a dictionary representation of the node and its children.
        """
        children = [c.to_dict() for c in self.children]
        return {
            "dialogue": self.dialogue,
            "branch_id": self.branch_id,
            "children": children,
            "child_count": self.child_count,
            "success_pct": self.success_pct
        }
    
    def from_dict(self, node_dict):
        """ Loads the node and its children from a dictionary.
        """
        self.dialogue = node_dict["dialogue"]
        self.branch_id = node_dict["branch_id"]
        self.child_count = node_dict["child_count"]
        self.success_pct = node_dict["success_pct"]
        self.children = []
        for child_dict in node_dict["children"]:
            child = DialogueNode([], "")
            child.from_dict(child_dict)
            self.add_child(child)

class DialogueTree:
    def __init__(self, root=None) -> None:
        self.root = root

    def get_root(self):
        return self.root
    
    def traverse_and_save_text(self, path="dialogue_tree"):
        """ Traverses the tree and saves each node's dialogue to a separate text file labeled with the node's branch ID.
        """
        def traverse(node, path):
            print(f"Traversing and saving node {node.branch_id}")
            # Create directory if it doesn't exist
            if not os.path.exists(path):
                os.makedirs(path)
            with open(os.path.join(path, f"{node.branch_id}.txt"), "w") as f:
                f.write(node.get_formatted_dialogue())
            for c in node.children:
                traverse(c, os.path.join(path, node.branch_id))

        traverse(self.root, os.path.abspath(path))
    
    def save_as_json(self, path="dialogue_tree"):
        """ Saves the root node as a json file
        """
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "root.json"), "w") as f:
            json.dump(self.root.to_dict(), f)
    
    def build_from_json(self, path):
        """ Builds a dialogue tree from a folder containing json dict of root node.
        """
        with open(os.path.join(path, "root.json"), "r") as f:
            root_dict = json.load(f)
        self.root = DialogueNode([], "")
        self.root.from_dict(root_dict)
        