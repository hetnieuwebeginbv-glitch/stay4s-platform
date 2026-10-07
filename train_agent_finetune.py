#!/usr/bin/env python3
"""Stay4S Agent Fine-tune - Qwen2.5-7B LoRA on agent training data"""
import torch, json, os, sys, time
from datetime import datetime

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset
except ImportError as e:
    print(f"Installing deps: {e}")
    os.system("pip install -q transformers peft datasets accelerate")
    from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
DATA_PATH = "/workspace/agent_training_50k.jsonl"
OUTPUT_DIR = "/workspace/agent_finetune_output"
BATCH_SIZE = 2
GRAD_ACCUM = 8
EPOCHS = 3
LR = 2e-4
MAX_SEQ_LEN = 1024

print(f"[{datetime.now()}] Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print(f"[{datetime.now()}] Loading model in 4-bit...")
from transformers import BitsAndBytesConfig
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, quantization_config=bnb_config,
    device_map="auto", trust_remote_code=True
)
model.config.use_cache = False

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=64, lora_alpha=128, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

print(f"[{datetime.now()}] Loading data...")
data = []
with open(DATA_PATH) as f:
    for line in f:
        data.append(json.loads(line))
print(f"Loaded {len(data)} records")

def format_example(ex):
    messages = ex["messages"]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return {"text": text}

ds = Dataset.from_list(data[:20000])  # Use 20K for speed
ds = ds.map(format_example, remove_columns=ds.column_names)

def tokenize_fn(examples):
    tokens = tokenizer(examples["text"], truncation=True, max_length=MAX_SEQ_LEN, padding="max_length")
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens

ds = ds.map(tokenize_fn, batched=True, remove_columns=["text"])

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=LR,
    warmup_steps=100,
    logging_steps=50,
    save_steps=1000,
    save_total_limit=3,
    fp16=True,
    optim="adamw_torch",
    lr_scheduler_type="cosine",
    report_to="none",
    dataloader_num_workers=4,
)

print(f"[{datetime.now()}] Starting training...")
trainer = Trainer(model=model, args=training_args, train_dataset=ds)
trainer.train()

print(f"[{datetime.now()}] Training complete! Saving...")
trainer.save_model(OUTPUT_DIR + "/final")
tokenizer.save_pretrained(OUTPUT_DIR + "/final")
print(f"[{datetime.now()}] Done! Model at {OUTPUT_DIR}/final")
