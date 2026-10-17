# ivrm-dailytech-adventure Agent Rules

- Source of Truthは最新main、Issue/PR/CI、README、`docs/oci-mod-lock.md`、`docs/world-generation.md`、`manifests/`。本番版・JAR数は実環境から再確認。
- Modpack作業: [`.agents/skills/modpack-change-rollout/SKILL.md`](.agents/skills/modpack-change-rollout/SKILL.md)。共通の接続・運用変更: [ivrm-platform](https://github.com/ivRooom/ivrm-platform/tree/main/.agents/skills)。
- 実World/Playerdata、MOD JAR、秘密情報、本番ComposeなどをGitへ追加しない。Mainの既存Worldを勝手に再生成・削除しない。
- `python3 scripts/validate_repository.py`、`PYTHONPATH=scripts python3 -m unittest scripts/test_mod_metadata_parser.py` 等、現在のCIを検証。未実施を成功と呼ばない。
- OCI/Host MCP利用前はscope/read-only接続状態を確かめる。Production JAR/Config/World/VM/Network変更は事前に影響・Backup/Restore/費用・明示承認を確認。
