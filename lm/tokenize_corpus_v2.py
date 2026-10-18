#!/usr/bin/env python3
"""Stay4S-LM — Stap 4a v2: GROOT corpus tokenizen (chunked, geen 1-string-panic).

Verschil met v1:
- encode in batches van regels (~1MB per batch) -> geen 'NormalizedString bad split'
- gebruikt ALLE NL + ALLE EN data (NL-first strategie; v1 kneep 50/50 en zou 90% NL weggooien)
- schrijft train.bin/val.bin (uint16), zelfde als v1
"""
import argparse, os
import numpy as np
from tokenizers import Tokenizer


def read_ids_chunked(tok, path, batch_bytes=1_000_000):
    ids_all = []
    batch, size, n_batches = [], 0, 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            batch.append(line)
            size += len(line.encode("utf-8", "ignore"))
            if size >= batch_bytes:
                for enc in tok.encode_batch(batch):
                    ids_all.extend(enc.ids)
                n_batches += 1
                if n_batches % 200 == 0:
                    print(f"  ... {n_batches} batches, {len(ids_all):,} tokens", flush=True)
                batch, size = [], 0
        if batch:
            for enc in tok.encode_batch(batch):
                ids_all.extend(enc.ids)
    return np.array(ids_all, dtype=np.uint16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/stay4s-llm"))
    ap.add_argument("--val-frac", type=float, default=0.005)
    a = ap.parse_args()

    tok = Tokenizer.from_file(os.path.join(a.root, "data", "tokenizer", "tokenizer.json"))
    out_dir = os.path.join(a.root, "data", "datasets")
    os.makedirs(out_dir, exist_ok=True)

    parts = {}
    for lg in ("nl", "en"):
        p = os.path.join(a.root, "data", "cleaned", lg, f"{lg}.txt")
        if os.path.exists(p):
            print(f"[{lg}] tokenizen: {os.path.getsize(p)/1e9:.2f} GB ...", flush=True)
            parts[lg] = read_ids_chunked(tok, p)
            print(f"[{lg}] tokens: {len(parts[lg]):,}", flush=True)

    if not parts:
        raise SystemExit("geen cleaned data gevonden")

    combo = np.concatenate(list(parts.values()))
    nval = max(1, int(len(combo) * a.val_frac))
    train, val = combo[:-nval], combo[-nval:]
    train.tofile(os.path.join(out_dir, "train.bin"))
    val.tofile(os.path.join(out_dir, "val.bin"))

    print("\n=== RESULTAAT ===")
    for lg, arr in parts.items():
        print(f"  {lg}: {len(arr):,} tokens ({len(arr)/len(combo)*100:.0f}%)")
    print(f"totaal: {len(combo):,} | train: {len(train):,} | val: {len(val):,}")
    print(f"type: uint16 (vocab {tok.get_vocab_size()}) -> {out_dir}")


if __name__ == "__main__":
    main()
