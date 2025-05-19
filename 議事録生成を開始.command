#!/bin/bash
cd "$(dirname "$0")/システム"
echo "議事録自動生成を開始します..."
nohup python3 auto_processor.py > /dev/null 2>&1 &
echo $! > auto_processor.pid
echo ""
echo "開始しました！処理はバックグラウンドで実行されています。"
echo "「現在の状態.txt」で状況を確認できます。"
echo ""
echo "このウィンドウは閉じても大丈夫です。"
read -p "Enterキーを押してください..."