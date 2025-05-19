#!/bin/bash
cd "$(dirname "$0")/システム"
echo "議事録自動生成を停止します..."
if [ -f auto_processor.pid ]; then
    pid=$(cat auto_processor.pid)
    if kill -0 $pid 2>/dev/null; then
        kill $pid
        echo "停止しました。"
    else
        echo "既に停止しています。"
    fi
    rm -f auto_processor.pid
else
    echo "実行されていません。"
fi
echo ""
read -p "Enterキーを押してください..."