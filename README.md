# HOTEL UKIUKI 空室監視

GitHub Actionsで10分ごとに空室情報を確認し、新しい空室が出た場合にntfyでiPhoneへ通知します。

## ファイル

- `monitor.py`: 空室数・部屋番号を取得して前回状態と比較
- `.github/workflows/monitor.yml`: 10分ごとの定期実行
- `state.json`: 前回の空室数・部屋番号（初回実行時に自動作成）

## セットアップ

1. ntfyアプリをiPhoneにインストールし、長くランダムなTopicを作成してSubscribeする。
2. GitHubで**Public**リポジトリを作成する（例: `ukiuki-vacancy-monitor`）。
3. このフォルダの内容をリポジトリのルートへアップロードする。
4. GitHubリポジトリの Settings → Secrets and variables → Actions → New repository secret を開く。
5. Nameを `NTFY_TOPIC`、Secretをntfyで作ったTopic名にして保存する。
6. Actionsタブでワークフローを有効にし、`HOTEL UKIUKI vacancy monitor` の `Run workflow` で初回実行する。
7. 初回は現在の状態を基準値として保存する。次回以降、新しい部屋番号または空室数増加を検知すると通知する。

## 注意

- Publicリポジトリではソースコードと `state.json` は公開されます。Topic名は必ずGitHub Secretsに保存し、コードやREADMEへ書かないでください。
- ntfy.shのTopicは、名前を知っている人が閲覧・投稿できる公開Topicです。十分に長いランダム名を使ってください。
- GitHub Actionsのscheduleは混雑時に遅延・欠落する場合があります。厳密な10分間隔や即時性は保証されません。
- 対象サイトのHTML変更、アクセス制限、通信障害があると実行ログにエラーが記録されます。ページ取得に失敗した場合、前回状態は更新しません。
- サイトの利用条件に反しない範囲で、10分に1回のアクセスに留めてください。
