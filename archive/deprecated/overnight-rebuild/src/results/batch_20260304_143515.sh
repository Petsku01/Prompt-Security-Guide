#!/bin/bash
set -e
cd /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src

echo '🔬 Testing stablelm2:1.6b...'
/usr/bin/python3 /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/cli.py run --model stablelm2:1.6b --battery smart --thorough --non-interactive --output /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results/stablelm2_1.6b_20260304_143515.json
echo '✅ stablelm2:1.6b complete!'

echo '🔬 Testing qwen2.5:1.5b...'
/usr/bin/python3 /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/cli.py run --model qwen2.5:1.5b --battery smart --thorough --non-interactive --output /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results/qwen2.5_1.5b_20260304_143515.json
echo '✅ qwen2.5:1.5b complete!'

echo ''
echo '🎉 All tests complete!'
echo 'Results saved to: /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results'
echo ''
echo 'Press any key to close...'
read -n1