# OCI 80 JARロック取得手順

## 目的

本番OCIの`mc-main`で稼働している80 JARを正として、JAR名、modId、SHA-256、ファイルサイズ、Side、配布元を含む公開可能なロックを生成します。

MOD JAR本体、ワールド、プレイヤーデータ、Whitelist、OPS、RCON Secretは取得・出力しません。

## 前提条件

- `mc-main`が`running / healthy`
- Host、Data、Containerが80 JAR
- `mc-resource`が停止中
- `/home/opc/ivrm-dailytech-adventure`へclone済み

## メタデータ解析

NeoForgeの正式な`META-INF/neoforge.mods.toml`、Forgeの`META-INF/mods.toml`、Fabricの`fabric.mod.json`を読み取ります。

NeoForge TOMLでは次の両方を標準形式として扱います。

```toml
[[mods]]
modId="example"
```

```toml
[[mods]] #mandatory
modId="example"
```

行末コメント付き`[[mods]]`は正式なTOML構文です。標準メタデータが存在するJARを、個別Overrideへ登録してはいけません。

標準メタデータを本当に持たないJARだけを、完全一致ファイル名で`manifests/metadata-overrides.json`へ登録します。現在のレビュー済み対象はAlternate Currentだけです。

## 1. リポジトリ更新

```bash
set +e
set +u
set -o pipefail

REPO="/home/opc/ivrm-dailytech-adventure"
cd "${REPO}"

git switch main
git pull --ff-only origin main
git log -1 --format='Commit=%H%nMessage=%s'
```

## 2. 80 JARのメタデータ一括診断

```bash
sudo python3 scripts/report_missing_mod_metadata.py \
  --mods-dir /opt/ivrm/compose/minecraft-main/mods \
  --metadata-overrides manifests/metadata-overrides.json \
  --expected-count 80
```

正常時の目安：

```text
JAR count=80
Standard metadata=79
Filename overrides=1
Missing metadata=0
```

## 3. ロック生成

旧`export_oci_mod_lock.py`ではなく、修正版パーサーを適用する`export_oci_mod_lock_v2.py`を実行します。

```bash
sudo python3 scripts/export_oci_mod_lock_v2.py \
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
```

## 4. 所有者と検証

```bash
sudo chown opc:opc \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256

PYTHONPATH=scripts python3 -m unittest scripts/test_mod_metadata_parser.py
python3 scripts/validate_repository.py

sha256sum \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256
```

## 5. 生成結果確認

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("manifests/main-26.1.2-80.lock.json")
data = json.loads(path.read_text(encoding="utf-8"))
mods = data["mods"]

print("jarCount=", data["jarCount"])
print("both=", sum(mod["side"] == "both" for mod in mods))
print("server=", sum(mod["side"] == "server" for mod in mods))
print("client=", sum(mod["side"] == "client" for mod in mods))
print("metadata override=", sum(mod["metadataSource"] == "filename-override" for mod in mods))
print("manual source=", sum(mod["source"] == "manual" for mod in mods))
PY
```

## 6. レビュー用アーカイブ

```bash
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="/home/opc/ivrm-main-80-lock-${STAMP}.tar.gz"

tar -C "${REPO}" -czf "${ARCHIVE}" \
  manifests/main-26.1.2-80.lock.json \
  manifests/main-26.1.2-80.lock.json.sha256 \
  manifests/metadata-overrides.json \
  manifests/side-overrides.json \
  manifests/distribution-overrides.json

chown opc:opc "${ARCHIVE}"
sha256sum "${ARCHIVE}"
echo "Archive=${ARCHIVE}"
```

## エラー時

- `Missing metadata`が1以上の場合、一覧をまとめて確認する。
- ファイル名からmodIdを推測しない。
- Host／Data／Containerの不一致時はロックを作らない。
- エクスポート処理はMODやワールドを変更しない。
- MODを更新・追加・削除した場合は本番状態からロックを再生成する。
