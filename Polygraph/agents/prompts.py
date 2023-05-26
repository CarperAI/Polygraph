import logging
import json

class AgentPrompts:
    def __init__(self, prompt_json, 
                 agent_prefix_list=["agent", "assistant", "alice"], 
                 user_prefix_list=["user", "bob"],
                 evaluator_prefix_list=None):
        # load prompt_json, add every k,v pair as an attribute to this class
        with open(prompt_json, "r") as f:
            self.prompts = json.load(f)
        logging.log(f"Loaded prompts from {prompt_json}")

        # create a dictionary called "agent".
        # any key that starts with agent/assistanat/alice will be added to this dictionary. remove the prefix
        self.agent = dict()
        for k,v in self.prompts.items():
            for prefix in agent_prefix_list:
                if k.startswith(prefix):
                    self.agent[k[len(prefix)+1:]] = v
        
        # create a dictioanry called "user"
        # any key that starts with user/bob will be added to this dictionary. remove the prefix
        self.user = dict()
        for k,v in self.prompts.items():
            for prefix in user_prefix_list:
                if k.startswith(prefix):
                    self.user[k[len(prefix)+1:]] = v

        # if evaluator_prefix_list is not None, create a dictionary called "evaluator"
        # any key that starts with the prefixes in evaluator_prefix_list will be added to this dictionary. remove the prefix
        if evaluator_prefix_list is not None:
            self.evaluator = dict()
            for k,v in self.prompts.items():
                for prefix in evaluator_prefix_list:
                    if k.startswith(prefix):
                        self.evaluator[k[len(prefix)+1:]] = v                
        