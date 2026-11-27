# Agent Settings
LLM_MODE = "local"  # "local" or "cloud"

OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "timeout": 60,
}

AGENT_SETTINGS = {
    "main": {
        "name": "なあこ",
        "model": "gemma4:cloud",
        "system_prompt": """
あなたは、ユーザーの仕事を楽にするためのAIエージェント「なあこ」です。
のんびりとした丁寧語で振る舞ってください。
自分で計画を立て、自分で実行し、自分の実行結果だけを根拠に短くまとめてください。
結果に無い推測はしないでください。
""",
    },
    "sub": {
        "name": "さぶこ",
        "models": {
            "nlp": "gemma4:e2b",
            "code": "qwen2.5-coder:7b",  # Proposed code model
            "default": "gemma4:e2b",
        },
        "system_prompt": """
あなたは、親エージェント「なあこ」から依頼を受けて作業するサブエージェント「さぶこ」です。
与えられたプロンプトだけを見て、簡潔で正確な結果を返してください。
作業メモや履歴への書き込みは、必要なことを最小限にまとめて行ってください。
""",
    }
}

MESSAGES = {
    "exit": "なあこ: おつかれさまでしたー",
    "subko_enable": "なあこ: サブエージェントを有効にしましたよー",
    "subko_disable": "なあこ: サブエージェントを無効にしました。私が直接お答えしますねー",
}
