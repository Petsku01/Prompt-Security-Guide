
cd /home/ette/.openclaw/workspace/prompt-security-guide
for MODEL in llama3:8b mistral:7b qwen2.5:3b phi3:mini gemma2:2b; do
    MODEL_SAFE=$(echo $MODEL | tr ':' '_')
    echo "Testing: $MODEL"
    python3 -m jailbreak_tester \
        --catalog /home/ette/.openclaw/workspace/prompt-security-guide/datasets/auto_20260321.json \
        --model "$MODEL" \
        --allow-insecure-http \
        --timeout 120 \
        --checkpoint "results/auto_${MODEL_SAFE}.jsonl" \
        --json-report "results/auto_${MODEL_SAFE}.json" \
        --text-report "results/auto_${MODEL_SAFE}.txt"
done
echo "=== ALL TESTS COMPLETE ==="
