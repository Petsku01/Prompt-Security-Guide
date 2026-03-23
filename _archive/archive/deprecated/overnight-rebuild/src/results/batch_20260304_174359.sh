#!/bin/bash
set -e
cd /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src

echo '🔬 Testing llama3:8b...'
/usr/bin/python3 /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/cli.py run --model llama3:8b --battery smart --thorough --non-interactive --output /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results/llama3_8b_20260304_174359.json
echo '✅ llama3:8b complete!'

echo '🔬 Testing qwen2.5:1.5b...'
/usr/bin/python3 /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/cli.py run --model qwen2.5:1.5b --battery smart --thorough --non-interactive --output /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results/qwen2.5_1.5b_20260304_174359.json
echo '✅ qwen2.5:1.5b complete!'

echo '🔬 Testing gemma2:2b...'
/usr/bin/python3 /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/cli.py run --model gemma2:2b --battery smart --thorough --non-interactive --output /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results/gemma2_2b_20260304_174359.json
echo '✅ gemma2:2b complete!'

echo '🔬 Testing stablelm2:1.6b...'
/usr/bin/python3 /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/cli.py run --model stablelm2:1.6b --battery smart --thorough --non-interactive --output /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results/stablelm2_1.6b_20260304_174359.json
echo '✅ stablelm2:1.6b complete!'

echo ''
echo '🎉 All tests complete!'
echo 'Results saved to: /home/ette/.openclaw/workspace/prompt-security-guide/overnight-rebuild/src/results'
echo ''
echo 'Press any key to close...'
read -n1