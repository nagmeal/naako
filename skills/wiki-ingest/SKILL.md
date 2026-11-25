---
name: wiki-ingest
description: docs-inbox に入れた資料（xlsx / pptx / txt / md）をプロジェクト wiki に取り込みたいときに使う。
input: task
timeout: 1200
---

# wiki-ingest

プロジェクトルートの `docs-inbox/` にある資料を取り込み、
`wiki/pages/` に Markdown ページを生成する。対応形式は
xlsx / pptx / txt / md / csv。PDF は対象外。

## 手順

1. スクリプト `scripts/run.py` を実行する（入力は使わない）。
2. スクリプトは取り込んだページの一覧と、読めなかったファイルの
   アラートを返す。その内容をそのまま報告すること。
3. 処理済みファイルは `docs-inbox/done/` に自動で移動する。
   読めなかったファイルは inbox に残る（無理に読むことはしない）。
4. 取り込みは1回で最大10件まで。残りがあるとアラートに出るので、
   その場合はもう一度実行すれば続きを取り込める。
