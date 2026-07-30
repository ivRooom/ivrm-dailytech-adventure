# OCI 80 JARロック取得手順

## 目的

本番OCIの`mc-main`で稼働している80 JARを正として、以下を含む公開可能なロックファイルを生成します。

- JARファイル名
- 主modIdと同梱modId
- SHA-256
- ファイルサイズ
- Client / Server分類
- 配布元
- Project ID / File ID
- Minecraft / NeoForge / Javaバージョン

MOD JAR本体、ワールド、プレイヤーデータ、Whitelist、OPS、RCON Secretは取得・出力しません。

## 前提条件

- `mc-main`が`running / healthy`
- Hostと`/data/mods`が80 JAR
- Container内`/data/mods`が80 JAR
- `mc-resource`は停止中
- リポジトリをOCIへclone済み
- OCIからGitHubへpushできる認証を設定済み

## 分類Override

自動判定できない情報は、次のファイルで明示します。

```text
manifests/side-overrides.json
manifests/distribution-overrides.json
```

`side-overrides.json`は、サーバー専用MODをmodIdまたはファイル名で指定します。未指定JARは`both`になります。

`distribution-overrides.json`では配布元を指定します。

```json
{
  "byModId": {
    "examplemod": {
      "source": "curseforge",
      "projectId": 123456,
      "fileId": 7890123
    }
  },
  "byFilename": {}
}
```

ModrinthやGitHubのIDは文字列も使用できます。

## OCIで実行

リポジトリのルートで実行します。

```bash
set -Eeuo pipefail

REPO="/home/opc/ivrm-dailytech-adventure"

cd "${REPO}"
git switch main
git pull --ff-only

sudo -v

python3 scripts/export_oci_mod_lock.py \
  --main-dir /opt/ivrm/compose/minecraft-main \
  --container mc-main \
  --resource-container mc-resource \
  --expected-count 80 \
  --side-overrides manifests/side-overrides.json \
  --distribution-overrides manifests/distribution-overrides.json \
  --output manifests/main-26.1.2-80.lock.json

python3 scripts/validate_repository.py

sha256sum \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256
```

成功時は次の内容が表示されます。

```text
OCI MOD lock export complete
Main=running/healthy
Resource=created
Host/Data/Container JAR count=80
Output=manifests/main-26.1.2-80.lock.json
SHA256=...
```

## 生成物を確認

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("manifests/main-26.1.2-80.lock.json")
data = json.loads(path.read_text(encoding="utf-8"))

print("jarCount=", data["jarCount"])
print("both=", sum(mod["side"] == "both" for mod in data["mods"]))
print("server=", sum(mod["side"] == "server" for mod in data["mods"]))
print("client=", sum(mod["side"] == "client" for mod in data["mods"]))
print("manual source=", sum(mod["source"] == "manual" for mod in data["mods"]))
print("default side=", sum(mod["sideSource"] == "default" for mod in data["mods"]))
PY
```

次の項目はPR前にレビューします。

- サーバー専用MODが`both`になっていないか
- CurseForge / ModrinthのProject IDとFile IDが埋まっているか
- 同梱modIdを含めて内容が正しいか
- 手動配置JARの入手元が文書化されているか
- `jarCount`が80か

## GitHubへ反映

```bash
git switch -c feat/import-main-80-jar-lock

git add \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256 \
  manifests/side-overrides.json \
  manifests/distribution-overrides.json

git commit -m "Main 80 JARの完全ロックを追加"
git push -u origin feat/import-main-80-jar-lock
```

PRでは、OCI上のJAR数・SHA一致結果だけを記録します。OCIのIPアドレス、秘密情報、実パス以外の本番固有情報は記載しません。

## 更新時

MODを1件でも更新・追加・削除した場合は、同じスクリプトでロックを再生成します。古いロックファイルを手編集せず、本番状態から生成し直します。
