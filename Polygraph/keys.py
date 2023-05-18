import requests
import time
from typing import Any, Tuple
import logging

class InferenceHook:
    def __init__(self, dir : str):
        self.dir = dir
        self.API_KEY = ""
        self.API_URL = ""
    
    def load(self, **kwargs) -> Tuple[str, str]:
        # return empty strings for now
        return ("", "")

    # Calls the inference API and returns the result
    def infer(self, *args: Any, **kwds: Any) -> Any:
        pass
    
class OpenAIHook(InferenceHook):
    def load(self, **kwargs) -> Tuple[str, str]:
        # Open key file
        with open(dir, "r") as f:
            API_KEY = f.read().strip('\n')

        # if we aren't using ChatGPT
        if "API_ENDPOINT" in kwargs:
            self.API_ENDPOINT = kwargs["API_ENDPOINT"]
        else:
            self.API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

        if 'max_retries' in kwargs:
            self.max_retries = kwargs['max_retries']
        else: 
            self.max_retries = 5

        return API_KEY, self.API_ENDPOINT

    def infer(self, *args : Any, **kwds : Any) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.API_KEY}",
        }

        data = {
            "model": args['model'],
            "messages": args['messages'],
            "temperature": args['temperature'],
        }

        if 'retry' in kwds:
            retry = kwds['retry']
        else:
            retry = 0

        r = requests.post(url=self.API_ENDPOINT, json=data, headers=headers)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            if retry < self.max_retries:
                logging.log(logging.ERROR, f"OpenAI API returned status code {r.status_code}. Retrying {retry} of {self.max_retries} times.")
                time.sleep(0.1)
                return self.infer(*args, **kwds, retry=retry+1)
            else: 
                logging.log(logging.ERROR, f"OpenAI API returned status code {r.status_code}. Retried {retry} times. Returning None.")
                return None
