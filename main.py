import ollama
from settings import AGENT_SETTINGS, MESSAGES

MODEL = AGENT_SETTINGS["main"]["model"]
SYSTEM_PROMPT = AGENT_SETTINGS["main"]["system_prompt"]
SUBAGENT_SYSTEM_PROMPT = AGENT_SETTINGS["sub"]["default"]["system_prompt"]


def _chat(system_prompt: str, prompt: str) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]


def _call_subagent(prompt: str, agent_type: str = "default") -> str:
    """サブエージェントを呼び出し、プロンプトを渡して返答を返す。"""
    sub_config = AGENT_SETTINGS["sub"].get(agent_type, AGENT_SETTINGS["sub"]["default"])
    return _chat(sub_config["system_prompt"], prompt)


def talk_to_naako(prompt: str, use_subagent: bool = True) -> str:
    if not use_subagent:
        # サブエージェントを通さず、なあこが直接回答する
        return _chat(SYSTEM_PROMPT, prompt)

    # タグ [agent_type] を抽出
    import re
    tag_match = re.search(r"\[([a-zA-Z0-9_]+)\]", prompt)
    agent_type = tag_match.group(1) if tag_match else "default"
    
    # タグ部分を削除して純粋な依頼内容にする
    clean_prompt = re.sub(r"\[([a-zA-Z0-9_]+)\]", "", prompt).strip()

    # 1. メインエージェントでプロンプトを英語に翻訳
    translation_prompt = f"以下のユーザー依頼を、サブエージェントに指示するための正確な英語に翻訳してください。翻訳結果のみを出力してください:\n\n{clean_prompt}"
    english_prompt = _chat(SYSTEM_PROMPT, translation_prompt)

    # 2. 翻訳後のプロンプトをサブエージェントに渡す
    sub_result = _call_subagent(english_prompt, agent_type=agent_type)
    summary_prompt = (
        f"ユーザーの依頼:\n{clean_prompt}\n\n"
        f"サブエージェントの処理結果:\n{sub_result}\n\n"
        "上記の処理結果だけを根拠に、依頼への返答を要約してください。"
    )
    return _chat(SYSTEM_PROMPT, summary_prompt)


if __name__ == "__main__":
    print("【エージェント『なあこ』を起動しています...】")
    print("終了するには /bye と入力してください。")
    print("サブエージェントの有効/無効は /subko enable または /subko disable で切り替えられます。\n")

    use_subagent = True
    while True:
        prompt = input("> ").strip()
        if prompt == "/bye":
            print(MESSAGES["exit"])
            break
        if not prompt:
            continue

        if prompt == "/subko enable":
            use_subagent = True
            print(MESSAGES["subko_enable"])
            continue
        if prompt == "/subko disable":
            use_subagent = False
            print(MESSAGES["subko_disable"])
            continue
        if prompt == "/subko":
            use_subagent = not use_subagent
            message = MESSAGES["subko_enable"] if use_subagent else MESSAGES["subko_disable"]
            print(message)
            continue

        reply = talk_to_naako(prompt, use_subagent=use_subagent)
        print(f"なあこ: \n{reply}\n")