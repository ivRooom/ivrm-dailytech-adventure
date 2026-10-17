---
name: modpack-change-rollout
description: ivRooom Minecraft ModpackのJAR/Manifest/Quest/Config/Datapack追加更新、OCI適用、ワールド生成影響、互換性・TPS・バックアップを確認して安全に段階反映する。
---

# Modpack Change / Rollout

## 作業対象

- `README.md`、`docs/architecture.md`、`docs/oci-mod-lock.md`、`docs/world-generation.md`、`manifests/`、`config-src/`、`.github/workflows/validate.yml` が正本。
- [共通Minecraft運用](https://github.com/ivRooom/ivrm-platform/blob/main/.agents/skills/minecraft-operations/SKILL.md) と [MCP接続基準](https://github.com/ivRooom/ivrm-platform/blob/main/.agents/skills/tool-access-and-mcp/SKILL.md)、プロバイダー移行時は [provider-migration](https://github.com/ivRooom/ivrm-platform/blob/main/.agents/skills/provider-migration/SKILL.md) を併用。
- このRepositoryはサニタイズ済みのManifest/設定/Quests/Datapacks/例示を管理する。Minecraft World、本番Config、MOD JAR/秘密鍵は含めない。独自MODソースは `ivrm-mcmod` の責務。

## 変更前の診断

1. 現在のServer群、Minecraft/Java/loader、CPU arch、想定人数、Memory、起動中Mod一覧・World/Chunk/Backup状態をread-onlyで確認。READMEの版・JAR件数は本番の実数と照合し、固定した現在値として扱わない。
2. Mod追加/更新/削除の目的と対象Side、client互換、依存Mod、配布元ライセンス、Forge/NeoForge/FabricとJavaの適合、ARM64での実行可否を確認。
3. ホストMODソース、コンテナ `/mods` と `/data/mods` の同期方式、SHA-256ロック/metadata overridesを `docs/oci-mod-lock.md` に沿って検証。Host/Data/Containerで差があれば生成・適用を止める。
4. Main Worldは無断再生成しない。Worldgen追加は未生成Chunk/Resourceを優先し、既存chunk・Claim/Waystone/公共施設を保護。
5. TPS/MSPT、CPU/RAM/GC/IO、プレイヤー数、ディスクとBackup時間を基準測定。一般的な推奨メモリだけで判断しない。

## PRと検証

```bash
python3 scripts/validate_repository.py
PYTHONPATH=scripts python3 -m unittest scripts/test_mod_metadata_parser.py
```

- CIの `python -m compileall -q scripts`、各ユニット・設定/Secrets検査を確認する。
- Manifest、JARの版/sha256、Config/Data Packを同じchange setで扱う。
- 仮想/隔離環境で起動、クライアントjoin、依存不足、クラッシュ/ログ、tick負荷、生成チャンク、server↔clientのHandshakeをチェック。
- PRには更新対象、影響（既存World、新規Chunk、既存プレイヤー、Resource再生成）、互換性、検証済/未済、rollbackを明記。

## 運用・MCP

- GitHubでIssue/PR/CI、利用可能なOCI/Cloud/Host MCPでread-only状態を確認。OCI connectorが未接続・対象scopeなしの場合はOperator実行のRunbookを作り、操作済みと報告しない。
- 実行時はBackupの存在・S3等への到達・Restore検証・旧JAR/configの保持を先行。Resource Worldはサービス固有の保存方針を最新確認してから扱う。
- 本番MOD/JAR反映・Minecraft再起動・World削除/復旧・任意のShell/RCON・新規課金リソースには変更対象を特定したHuman Approvalが必要。Skill・Issueは権限の代替にならない。
- 切替後はJAR lock三者整合、Minecraft Server boot、実プレイ、TPS/MSPT、Backup鮮度、既存Worldを照合。異常なら切替前ArtifactへRollbackし、World restoreが必要なら別承認を取る。

## 注意

既存実運用ドキュメントにある`expected-count`、World/MCバージョン、パス、ユーザー名はその環境用サンプル。異なるホストへのコピー・sudo実行はしない。
