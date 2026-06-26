#!/bin/bash
# 子账号会话外壳:claude 退出就重开,永远不掉到裸 shell。
# 这是"可写终端也接管不了机器"的核心一层——pane 的命令就是这个脚本本身,
# 它背后没有交互 shell,所以 Ctrl-D / /exit / claude 崩了都只会重启 claude。
# 用法: sub_claude_loop.sh <project_dir> <settings_json>
set +m                      # 关闭 job control,Ctrl-Z 不产生可用的后台 shell
trap '' INT QUIT TSTP TERM  # 外壳层吞掉 Ctrl-C/Ctrl-\/Ctrl-Z/TERM,自己不退出

dir="$1"
settings="$2"
cd "$dir" || exit 1

while true; do
  claude --settings "$settings" --permission-mode dontAsk
  # claude 退出(/exit、Ctrl-D、崩溃)→ 稍等重开,中间这一瞬不给 shell
  sleep 0.5
done
