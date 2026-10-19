#!/bin/bash
cd /root/stay4s-llm
RUN=runs/stay4s-lm-002-reus-wiki
echo "=== EVAL start $(date -u) ==="
python3 scripts/eval_harness.py --ckpt $RUN/ckpt_best.pt --device cuda --report runs/EVAL_stay4s-lm-002-reus-wiki.md || echo "EVAL FAILED"
echo "=== EXPORT $(date -u) ==="
sed -e "s|stay4s-lm-001-reus|stay4s-lm-002-reus-wiki|" -e "s|export/reus-hf|export/reus-v2-hf|" scripts/export_hf.py > scripts/export_hf_v2.py
python3 scripts/export_hf_v2.py
python3 -c "import json;p='/root/stay4s-llm/export/reus-v2-hf/config.json';c=json.load(open(p));c.update({'n_ctx':1024,'unk_token_id':3,'pad_token_id':0});json.dump(c,open(p,'w'),indent=2);print('config patched')"
echo "=== GGUF f16 $(date -u) ==="
python3 /root/llama.cpp/convert_hf_to_gguf.py export/reus-v2-hf --outfile export/reus-v2-f16.gguf --outtype f16
echo "=== QUANT $(date -u) ==="
/root/llama.cpp/build/bin/llama-quantize export/reus-v2-f16.gguf export/reus-v2-Q4_K_M.gguf Q4_K_M
echo "=== SMOKE $(date -u) ==="
/root/llama.cpp/build/bin/llama-cli -m export/reus-v2-Q4_K_M.gguf -p "Amsterdam is de hoofdstad van" -n 60 --temp 0.8 2>&1 | tail -8
echo "=== HASHES ==="
sha256sum export/reus-v2-Q4_K_M.gguf $RUN/ckpt_best.pt
echo "=== FINISH-PIPELINE KLAAR $(date -u) ==="