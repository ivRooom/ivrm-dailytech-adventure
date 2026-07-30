# OCI 80 JARロック取得手順

## 目的

本番OCIの`mc-main`で稼働している80 JARを正として、以下を含む公開可能なロックファイルを生成します。

- JARファイル名
- 主modIdと同梱modId
- メタデータ取得元
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

## Override

自動判定できない情報は、次のファイルで明示します。

```text
manifests/metadata-overrides.json
manifests/side-overrides.json
manifests/distribution-overrides.json
```

### Metadata Override

標準のNeoForge・Forge・Fabricメタデータを持たないJARだけを、**完全一致するファイル名**で登録します。エクスポーターはファイル名からmodIdを推測しません。

```json
{
  "byFilename": {
    "example-1.0.0.jar": {
      "name": "Example Mod",
      "modId": "example_mod",
      "modIds": ["example_mod"],
      "reason": "標準メタデータを持たないことを確認済み"
    }
  }
}
```

現在は`alternate_current-mc26.1-1.9.0.jar`を明示登録しています。ファイル名やバージョンが変わった場合は自動適用されず、安全側で停止します。

### Side Override

`side-overrides.json`は、サーバー専用MODをmodIdまたはファイル名で指定します。未指定JARは`both`になります。

### Distribution Override

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
git pull --ff-only origin main

sudo -v

sudo python3 scripts/export_oci_mod_lock.py \
  --main-dir /opt/ivrm/compose/minecraft-main \
  --container mc-main \
  --resource-container mc-resource \
  --expected-count 80 \
  --minecraft 26.1.2 \
  --loader neoforge \
  --loader-version 26.1.2.81 \
  --java 25 \
  --metadata-overrides manifests/metadata-overrides.json \
  --side-overrides manifests/side-overrides.json \
  --distribution-overrides manifests/distribution-overrides.json \
  --output manifests/main-26.1.2-80.lock.json

sudo chown opc:opc \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256

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
Metadata filename overrides=1
Output=manifests/main-26.1.2-80.lock.json
SHA256=...
```

## メタデータエラー時

次のエラーは、JAR破損やサーバー障害ではなく、標準メタデータを読み取れないJARを検出したことを表します。

```text
No NeoForge/Forge/Fabric MOD metadata found in <filename>
```

対象JARを確認し、正体が確定している場合だけ`metadata-overrides.json`へ完全一致ファイル名で追加します。未知のJARを推測登録したり、エラーを無視してロックを作成したりしません。

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
print(
    "metadata override=",
    sum(mod["metadataSource"] == "filename-override" for mod in data["mods"]),
)
PY
```

PR前に次をレビューします。

- サーバー専用MODが`both`になっていないか
- CurseForge / ModrinthのProject IDとFile IDが埋まっているか
- 同梱modIdを含めて内容が正しいか
- `metadataSource=filename-override`が既知のJARだけか
- 手動配置JARの入手元が文書化されているか
- `jarCount`が80か

## GitHubへ反映

```bash
git switch -c feat/import-main-80-jar-lock

git add \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256 \
  manifests/metadata-overrides.json \
  manifests/side-overrides.json \
  manifests/distribution-overrides.json

git commit -m "Main 80 JARの完全ロックを追加"
git push -u origin feat/import-main-80-jar-lock
```

PRにはOCI上のJAR数・SHA一致結果だけを記録します。OCIのIPアドレス、秘密情報、本番固有の資格情報は記載しません。

## 更新時

MODを1件でも更新・追加・削除した場合は、同じスクリプトでロックを再生成します。古いロックファイルを手編集せず、本番状態から生成し直します。
