import requests
import json
import os
import time


class DialogueNode:
    def __init__(self, dialogue) -> None:
        self.dialogue = dialogue
        self.children = {}
        self.child_count = 0
        self.succeeded = False

    def add_child(self, child) -> None:
        self.children[f"child_{self.child_count}"] = child
        self.child_count += 1


class DialogueTree:
    def __init__(self, root) -> None:
        self.root = root