# IVRM DailyTech Adventure

Minecraft `26.1.2` / NeoForge `26.1.2.81` を対象とした、ivRooom生活・探索・RPGサーバーの公開設定リポジトリです。

## 現在地

- Mainサーバー: `mc-main`
- 状態: `running / healthy`
- MOD: Host / Data / Containerすべて`80 JAR`
- Java: `25`
- 想定規模: 平均5人、最大10人
- Mainワールド: 維持。既生成チャンクは再生成しない
- Resourceサーバー: 別コンテナ、月次リセット、バックアップなしの方針

## このリポジトリで管理するもの

- FTB Questsのソース定義と生成・検証ツール
- Project MMOの設計方針と将来のData Pack
- MODバージョン・File ID・SHA-256ロック
- サニタイズ済みの設定例、Compose例、運用ドキュメント
- GitHub Actionsによる構文・秘密情報・禁止ファイル検査

## 管理しないもの

- MOD JARそのもの
- ワールド、playerdata、バックアップ
- RCONパスワード、Webhook、APIキー、秘密鍵
- whitelist.json、ops.json、usercache.json
- 本番のserver.propertiesや本番固有Compose

## ディレクトリ

```text
config-src/   人が編集する設定ソース
manifests/    MOD構成・ロック情報
docs/         設計・運用判断
scripts/      生成・検証ツール
deploy/       秘密情報を含まない例
.github/      CI、PRテンプレート
```

## OCIの80 JARロック

本番のHost、Data、ContainerをSHA-256で三者照合し、JAR名・modId・Side・配布元を含む公開可能なロックを生成します。

- 手順: [`docs/oci-mod-lock.md`](docs/oci-mod-lock.md)
- 生成ツール: [`scripts/export_oci_mod_lock.py`](scripts/export_oci_mod_lock.py)
- Side補正: [`manifests/side-overrides.json`](manifests/side-overrides.json)
- 配布元補正: [`manifests/distribution-overrides.json`](manifests/distribution-overrides.json)

## 開発フロー

1. `main`から作業ブランチを作る
2. `config-src`または`docs`を変更する
3. `python scripts/validate_repository.py`を実行する
4. PRを作成する
5. CI成功・レビュー後にマージする
6. OCIへ反映し、起動・RCON・JAR数・実プレイを確認する

## 重要な運用判断

- PMMOを主要スキルシステムとして採用し、Pufferfish Skillsとの二重XPを解消する
- FTB Questsは最初にBatch 001〜003、約45件をMVPとして作る
- Mainワールドは再作成せず、新構造物は未生成チャンクとResourceサーバーで補う
- MOD更新時はJAR、設定、Data Packを同じリリース単位でロックする

## ライセンス

このリポジトリ内の独自スクリプトと設定ソースはMIT Licenseです。各MOD本体・名称・画像・アセットは各作者のライセンスに従います。このリポジトリはMOD JARを再配布しません。
