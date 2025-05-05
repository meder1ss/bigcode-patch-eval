from unsloth import FastLanguageModel
import torch
from datasets import load_dataset
import random
random.seed(711)
from unsloth import PatchDPOTrainer
PatchDPOTrainer()
from transformers import TrainingArguments
from trl import DPOTrainer, PPOTrainer
from unsloth import is_bfloat16_supported

max_seq_length = 2048 
dtype = None
load_in_4bit = True
output_dir = 'outputs_code_preference_3_epochs'

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "Qwen/Qwen2.5-Coder-7B-Instruct",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

sample_size = 50
dataset = load_dataset("Vezora/Code-Preference-Pairs", split="train")
def apply_chat_template(
    example,
    assistant_token= "<assistant_token>", 
    user_token = "<user_token>", 
    eos_token = "<end_token>",
    bos_token = "<s>",
):
    if all(k in example.keys() for k in ("accepted", "rejected")):
        example["text_prompt"] = f"{bos_token}{user_token}\n{example['input']}{eos_token}\n{assistant_token}"
        example["text_chosen"] = f"{example['accepted']}{eos_token}\n"
        example["text_rejected"] = f"{example['rejected']}{eos_token}\n"
        
    return example
column_names = dataset.column_names
sampled_dataset = dataset.map(apply_chat_template)
sampled_dataset = sampled_dataset.remove_columns(column_names)
sampled_dataset = sampled_dataset.rename_columns(
    {"text_prompt": "prompt", "text_chosen": "chosen", "text_rejected": "rejected"} # Update here
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 4,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 4,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    use_rslora = False,
    loftq_config = None,
)

dpo_trainer = DPOTrainer(
    model = model,
    args = TrainingArguments(
        per_device_train_batch_size = 4,
        gradient_accumulation_steps = 2,
        warmup_ratio = 0.1,
        num_train_epochs = 3,
        learning_rate = 5e-6,
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 5,
        save_steps=500,
        optim = "adamw_8bit",
        weight_decay = 0.0,
        lr_scheduler_type = "linear",
        seed = 42,
        output_dir = output_dir,
    ),
    beta = 0.2,
    train_dataset = sampled_dataset,
    tokenizer = tokenizer,
    max_length = 1024,
    max_prompt_length = 512,
)
dpo_trainer.train()