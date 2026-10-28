# なあこ

ローカル LLM（Ollama）を呼び出す AI エージェントです。

## 前提条件

- Python 3
- [Ollama](https://ollama.com/) がインストールされ、起動していること
- モデル `gemma4:e4b` が利用できること

```bash
ollama pull gemma4:e4b
```

使うモデルを変える場合は `main.py` の `model='gemma4:e4b'` を書き換えてください。

## セットアップ

```bash
pip install ollama
```

## 実行方法

プロジェクトのルートで次を実行します。

```bash
python main.py
```

起動すると入力待ちになります。話しかけてなあこと会話できます。終了するには `/bye` と入力してください。
