import requests
import json
from typing import Optional, List, Dict, Any
import settings

class LLMClient:
    """
    A unified client to interact with LLMs via Ollama or Cloud APIs.
    Handles model switching and prompt formatting.
    """
    def __init__(self):
        self.mode = settings.LLM_MODE
        self.ollama_config = settings.OLLAMA_CONFIG
        self.agent_settings = settings.AGENT_SETTINGS

    def _get_ollama_payload(self, model: str, system_prompt: str, user_prompt: str, messages: Optional[List[Dict[str, str]]] = None):
        """Constructs the payload for Ollama's generate/chat API."""
        # Using the /api/chat endpoint for better conversation management
        chat_messages = [{"role": "system", "content": system_prompt}]
        if messages:
            chat_messages.extend(messages)
        chat_messages.append({"role": "user", "content": user_prompt})
        
        return {
            "model": model,
            "messages": chat_messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 1024,
            }
        }

    def call_local(self, model: str, system_prompt: str, user_prompt: str, messages: Optional[List[Dict[str, str]]] = None) -> str:
        """Calls a local model via Ollama."""
        url = f"{self.ollama_config['base_url']}/api/chat"
        payload = self._get_ollama_payload(model, system_prompt, user_prompt, messages)
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.ollama_config['timeout']
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except requests.exceptions.RequestException as e:
            return f"Error calling Ollama: {str(e)}"

    def call_cloud(self, model: str, system_prompt: str, user_prompt: str, messages: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Placeholder for Cloud API implementation.
        Actual implementation depends on the chosen cloud provider (OpenAI, Anthropic, etc.).
        """
        return f"[Cloud Mode Simulation] Model {model} would be called here. User prompt: {user_prompt}"

    def generate(self, agent_type: str, user_prompt: str, task_type: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None) -> str:
        """
        High-level method to generate a response based on agent type and task.
        - agent_type: 'main' (Naako) or 'sub' (Sabuko)
        - task_type: 'nlp' or 'code' (only relevant for Sabuko)
        """
        if agent_type == "main":
            config = self.agent_settings["main"]
            model = config["model"]
            system_prompt = config["system_prompt"]
        elif agent_type == "sub":
            config = self.agent_settings["sub"]
            system_prompt = config["system_prompt"]
            # Determine which model to use for Sabuko
            if task_type and task_type in config["models"]:
                model = config["models"][task_type]
            else:
                model = config["models"]["default"]
        else:
            raise ValueError(f"Unknown agent_type: {agent_type}")

        if self.mode == "local":
            return self.call_local(model, system_prompt, user_prompt, messages)
        else:
            return self.call_cloud(model, system_prompt, user_prompt, messages)

# Simple smoke test if run directly
if __name__ == "__main__":
    client = LLMClient()
    print("--- Testing Naako (Main) ---")
    print(client.generate("main", "こんにちは！"))
    print("\n--- Testing Sabuko (Sub - NLP) ---")
    print(client.generate("sub", "1+1は？", task_type="nlp"))
    print("\n--- Testing Sabuko (Sub - Code) ---")
    print(client.generate("sub", "PythonでHello Worldを書いて", task_type="code"))
