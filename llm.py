from openai import OpenAI
from typing import Type
import os
from strategy import BaseStrategy
import pandas as pd
import numpy as np
from typing import Dict

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=api_key)

def generate_strategy_class(prompt: str) -> Type[BaseStrategy]:
    """Generate strategy class code from LLM prompt."""
    system_msg = """
    Generate a Python class that inherits from BaseStrategy.
    It must implement def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
    Use imports only from pandas, numpy, sklearn if needed.
    Class name: CustomStrategy
    Based on user prompt: {prompt}
    Return only the code, no explanations.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg.format(prompt=prompt)},
            {"role": "user", "content": prompt}
        ]
    )
    code = response.choices[0].message.content.strip()
    
    # Validate and exec in local scope
    local_scope = {}
    try:
        exec(code, {"BaseStrategy": BaseStrategy, "pd": pd, "np": np, "Dict": Dict}, local_scope)
        custom_class = local_scope['CustomStrategy']
        if not issubclass(custom_class, BaseStrategy):
            raise ValueError("Generated class not subclass of BaseStrategy")
        return custom_class
    except Exception as e:
        raise ValueError(f"Failed to generate valid strategy: {e}\nCode: {code}")

