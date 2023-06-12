import os

def load_prompts(prompt_dir):
    """
    Loads prompts from a directory, stored as text file deliminted by \n\n 
    """
    prompts = []
    for filename in os.listdir(prompt_dir):
        with open(os.path.join(prompt_dir, filename), 'r') as f:
            prompts.append(f.read())
    return prompts