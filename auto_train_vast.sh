#!/bin/bash
# auto_train_vast.sh - Wait for model upload, verify, start training
echo "=== AUTO TRAIN VAST.AI ==="
echo "Waiting for model.safetensors.new upload to complete..."

# Wait for upload to complete (check if file is still being written)
PREV_SIZE=0
for i in $(seq 1 120); do
    CURR_SIZE=$(stat -c%s /workspace/Qwen2.5-1.5B-Instruct/model.safetensors.new 2>/dev/null || echo 0)
    if [ "$CURR_SIZE" -gt 0 ] && [ "$CURR_SIZE" -eq "$PREV_SIZE" ]; then
        echo "Upload complete! Size: $CURR_SIZE bytes"
        break
    fi
    PREV_SIZE=$CURR_SIZE
    echo "Waiting... Size: $CURR_SIZE / 3087467144"
    sleep 10
done

# Replace old file
echo "Replacing model.safetensors..."
mv /workspace/Qwen2.5-1.5B-Instruct/model.safetensors.new /workspace/Qwen2.5-1.5B-Instruct/model.safetensors

# Verify
ACTUAL_SIZE=$(stat -c%s /workspace/Qwen2.5-1.5B-Instruct/model.safetensors)
echo "Model size: $ACTUAL_SIZE bytes (expected: 3087467144)"
if [ "$ACTUAL_SIZE" -ne 3087467144 ]; then
    echo "ERROR: Model size mismatch!"
    exit 1
fi

echo "Model verified! Starting training..."
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
nohup python3 /workspace/train_vast_v3.py > /workspace/train_v3.log 2>&1 &
echo "Training started! PID: $!"
echo "Log: /workspace/train_v3.log"
