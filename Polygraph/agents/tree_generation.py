from Polygraph.keys import *

class TreeGeneration:
    """
    Generates a dialogue tree between two agents to accomplish some goal.
    Utilizes prompts found in prompts/
    """
    def __init__(self, alice_dir, bob_dir):
        