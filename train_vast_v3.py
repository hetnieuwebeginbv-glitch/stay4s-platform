#!/usr/bin/env python3
"""train_vast_v3.py - Fine-tune Qwen2.5-1.5B on Vast.ai with usable_training_25k.jsonl
Focuses on math, reasoning, code, Dutch, English (stay4s-1b weaknesses)"""

import os, json, torch, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [INFO] %(message)s")
log = logging.getLogger(__name__)

MODEL_PATH = "/workspace/Qwen2.5-1.5B-Instruct"
DATA_FILE = "/workspace/usable_training_25k.jsonl"
OUTPUT_DIR = "/workspace/checkpoints_v3"

def main():
    from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset
    
    log.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    log.info("Loading model in 4-bit...")
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=bnb_config,
        trust_remote_code=True,
        device_map="auto",
    )
    
    # LoRA config
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load data
    log.info(f"Loading data from {DATA_FILE}...")
    records = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            system = r.get("system", "Je bent Stay4S, een behulpzame Nederlandse AI-assistent.")
            prompt = r["prompt"]
            response = r["response"]
            text = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n{response}<|im_end|>"
            records.append({"text": text})
    
    log.info(f"Loaded {len(records)} records")
    dataset = Dataset.from_list(records)
    
    # Tokenize
    def tokenize_fn(examples):
        return tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length")
    
    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    
    # Training args
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=50,
        save_steps=2500,
        save_total_limit=4,
        fp16=True,
        report_to="none",
        optim="adamw_torch",
        dataloader_num_workers=4,
        remove_unused_columns=False,
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=data_collator,
    )
    
    log.info("Starting training...")
    trainer.train()
    
    log.info("Training complete! Saving model...")
    model.save_pretrained(os.path.join(OUTPUT_DIR, "final"))
    tokenizer.save_pretrained(os.path.join(OUTPUT_DIR, "final"))
    
    log.info("=== DONE ===")

if __name__ == "__main__":
    main()
