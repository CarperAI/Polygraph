# Utilizes tree_generation to generaate a large
# tree of possible utterances between agents
# and then trains a reward model on the resulting MCTS tree

from tree_generation import *
# tools for training reward models
from autocrit import preference