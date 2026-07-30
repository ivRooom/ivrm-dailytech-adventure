# Security Policy

## 公開してはいけない情報

- RCONパスワード
- Discord Webhook URL
- OCI、AWS、S3の資格情報
- SSH秘密鍵
- 実ユーザーを含むwhitelist.json、ops.json、usercache.json
- 本番IP、内部ホスト名、直接接続用エンドポイント
- LuckPerms等のDB接続情報

## 発見時の対応

秘密情報をコミットした場合、ファイル削除だけでは不十分です。直ちに資格情報を失効・再発行し、履歴から除去してください。

脆弱性や漏えいを発見した場合は公開Issueを作らず、ivRooom管理者へ非公開経路で連絡してください。
