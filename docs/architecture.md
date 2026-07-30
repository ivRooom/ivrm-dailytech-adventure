# 構成概要

## Main

- Minecraft `26.1.2`
- NeoForge `26.1.2.81`
- Java `25`
- Dockerコンテナ `mc-main`
- 80 JAR固定構成
- RCON Secretは読み取り専用Bind Mount
- whitelist / opsは共有ディレクトリから読み取り専用Bind Mount

## Resource

- Mainと同じOCIホスト上の別Minecraftコンテナ
- Mainと同じ最終MODロックを利用
- 通常停止、必要時に起動
- 月次ワールドリセット
- ワールドバックアップなし
- MainとplayerdataやMOD永続データを同時共有しない

## GitHub・Notion・Linearの役割

- GitHub: 実際に反映可能な設定ソース、Manifest、検証コード
- Notion: 設計理由、運用方針、利用者向け説明
- Linear: 実装タスク、障害、進捗
- OCI: 本番ランタイム
- S3: Mainワールドのバックアップと復元データ
