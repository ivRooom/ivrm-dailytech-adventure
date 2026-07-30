# config-src

このディレクトリは人が編集する設定ソースの正本です。

現在は、FTB QuestsとPMMOの設計ソースを先に置いています。実際のMODが生成したJSON5、TOML、Data PackをOCIから取得して差分確認するまで、存在しない設定キーを推測で追加しません。

生成物は`generated/`へ出力し、原則コミットしません。リリース時に必要な生成物だけをタグまたはRelease Artifactとして保存します。
