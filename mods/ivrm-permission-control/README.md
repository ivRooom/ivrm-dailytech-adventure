# IVRM Permission Control

Minecraft 26.1.2 / NeoForge向けのサーバー専用権限制御MODです。

## 判定する権限

- `ivrm.play.build`: ブロック破壊・設置
- `ivrm.play.craft`: クラフト制御用予約ノード
- `ivrm.play.container`: コンテナ制御用予約ノード
- `ivrm.play.interact`: ブロック・アイテム・エンティティ操作
- `ivrm.play.combat`: Mob・プレイヤーへの攻撃
- `ivrm.play.pickup`: アイテム拾得・ドロップ

LuckPermsへ直接依存せず、NeoForge PermissionAPIを使用します。サーバー側で`luckperms:permission_handler`が有効な場合、既存のLuckPermsノードが利用されます。

## 現在のMVP制限

- ブロック破壊
- ブロック設置
- ブロックへの左・右クリック
- アイテム使用
- エンティティ操作
- Mob・プレイヤーへの攻撃
- アイテム拾得
- アイテムドロップ

権限判定に失敗した場合は安全側で拒否します。拒否メッセージは3秒間のクールダウン付きです。

## 未完了

`ivrm.play.craft`と`ivrm.play.container`は登録済みですが、インベントリ内2x2クラフトや全MOD独自GUIを確実に止める処理は、実機イベント調査後に追加します。ホワイトリストはQA完了までONを維持してください。

## ビルド

Java 25とGradle 9.2.1を使用します。

```bash
gradle build
```

成果物は`build/libs/ivrm_permission_control-0.1.0.jar`です。
