from main import talk_to_naako
from rewriter import update_setting
from settings import load_settings

def test_add_agent():
    agent_name = "philosopher"
    system_prompt = "あなたは哲学者サブエージェントです。あらゆることに哲学的な視点から回答してください。"
    
    print(f"Adding agent {agent_name}...")
    new_config = {
        "model": "gemma4:e4b",
        "system_prompt": system_prompt
    }
    
    if update_setting(['sub', agent_name], new_config):
        print("Successfully updated settings.py")
    else:
        print("Failed to update settings.py")
        return

    # Verify by loading settings
    settings, _ = load_settings()
    if agent_name in settings['sub'] and settings['sub'][agent_name]['system_prompt'] == system_prompt:
        print(f"Verification successful: {agent_name} is now in settings.")
    else:
        print(f"Verification failed: {agent_name} not found or prompt mismatch.")

if __name__ == "__main__":
    test_add_agent()
