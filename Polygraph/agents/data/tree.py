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
        self.success_likelihood = None

    def add_child(self, node):
        self.children.append(node)
        self.child_count += 1

    def is_leaf(self):
        return len(self.children) == 0

    def set_success_pct(self, success_pct) -> None:
        self.success_pct = success_pct

    def set_success_likelihood(self, success_likelihood) -> None:
        self.success_likelihood = success_likelihood

    def get_node_count(self) -> int:
        """ Returns the number of nodes in this node's subtree (including this node). """
        if self.is_leaf():
            return 1
        else:
            return 1 + sum(c.get_node_count() for c in self.children)

    def calculate_success_pct(self) -> float:
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
            return 0.01 if not self.success_pct else self.success_pct

        if self.success_pct is None:
            total_node_count = sum(c.get_node_count() for c in self.children)
            self.success_pct = sum(c.calculate_success_pct() * c.get_node_count() for c in self.children) / total_node_count

        return self.success_pct
    
    def get_success_likelihood(self) -> float:
        """ Returns the success likelihood of this node.
        If the success likelihood is not set, it will be calculated recursively.

        Returns:
            float: The success likelihood of this node.
        """
        if self.is_leaf():
            return 0.01 if not self.success_likelihood else self.success_likelihood

        if self.success_likelihood is None:
            total_node_count = sum(c.get_node_count() for c in self.children)
            self.success_likelihood = sum(c.get_success_likelihood() * c.get_node_count() for c in self.children) / total_node_count

        return self.success_likelihood


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
    def __init__(self, tree_id=0, root=None, honesty="honest") -> None:
        self.root = root
        self.tree_id = tree_id
        self.honesty = honesty

    def get_root(self):
        return self.root
    
    def traverse_and_save_text(self, path="dialogue_tree", include_final_user_response=False):
        """ Traverses the tree and saves each node's dialogue to a separate text file labeled with the node's branch ID.
        """
        def traverse(node):
            print(f"Traversing and saving node {node.branch_id}")
            # Create directory if it doesn't exist
            if not os.path.exists(path):
                os.makedirs(path)
            with open(os.path.join(path, f"{self.honesty}-tree-{self.tree_id}-branch-{node.branch_id}.txt"), "w") as f:
                f.write(node.get_formatted_dialogue(include_final_user_response=include_final_user_response))
            for c in node.children:
                traverse(c)

        traverse(self.root)
    
    def save_as_json(self, path="tree.json"):
        """ Saves the root node as a json file
        """
        #if not os.path.exists(path):
        #    os.makedirs(path)
        with open(path, "w") as f:
            json.dump(self.root.to_dict(), f)
    
    def build_from_json(self, path):
        """ Builds a dialogue tree from a folder containing json dict of root node.
        """
        with open(path, "r") as f:
            root_dict = json.load(f)
        self.root = DialogueNode([], "")
        self.root.from_dict(root_dict)

    def get_tree_success_pct(self, save_as_file=True, labels_dir="success_pcts") -> dict:
        """ Returns the success percentage of each node of the tree, recursively.
        """
        def traverse(node):
            if node.is_leaf():
                return {node.branch_id: node.calculate_success_pct()}
            else:
                return {node.branch_id: node.calculate_success_pct(), **{k: v for c in node.children for k, v in traverse(c).items()}}
            
        success_pct_dict = traverse(self.root)
        if save_as_file:
            with open(os.path.join(labels_dir, f"{self.honesty}-tree-{self.tree_id}-success-pct.json"), "w") as f:
                json.dump(success_pct_dict, f)

        return success_pct_dict

    
    def get_tree_success_likelihood(self, save_as_file=True, labels_dir="success_likelihoods") -> dict:
        """ Returns the success likelihood of each node of the tree, recursively.
        """
        def traverse(node):
            if node.is_leaf():
                return {node.branch_id: node.get_success_likelihood()}
            else:
                return {node.branch_id: node.get_success_likelihood(), **{k: v for c in node.children for k, v in traverse(c).items()}}
            
        success_likelihood_dict = traverse(self.root)
        if save_as_file:
            with open(os.path.join(labels_dir, f"{self.honesty}-tree-{self.tree_id}-success-likelihood.json"), "w") as f:
                json.dump(success_likelihood_dict, f)

        return success_likelihood_dict
        