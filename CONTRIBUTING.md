# Contributing

## 基本ルール

- ブランチ名に`codex`を含めない
- コミット、PRタイトル、PR説明は日本語
- MOD JAR、ワールド、秘密情報をコミットしない
- 実際のMinecraft `26.1.2` / NeoForge `26.1.2.81`環境で確認できない設定キーを推測で追加しない
- 生成済み設定より`config-src`を正本とする

## 推奨ブランチ名

- `feat/ftbquests-batch-001`
- `feat/pmmo-initial-policy`
- `fix/securitycraft-permissions`
- `docs/world-generation-policy`

## PR前確認

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_repository.py
```

OCIへ反映する変更では、変更前バックアップ、起動確認、RCON、JAR数、RestartCount、OOMKilled、実プレイ結果をPRへ記録してください。
