"""
C3 — LoRA fine-tune of a Qwen2.5 Instruct model on data/pocket_chat → an adapter (+ merged).

Colab (T4, 16 GB):   python training/train.py --model Qwen/Qwen2.5-1.5B-Instruct --qlora
Merge only:          python training/train.py --merge-only   (adapter already in outputs/)
Mac smoke test:      python training/train.py --model Qwen/Qwen2.5-0.5B-Instruct \
                         --limit 40 --max-steps 5

QLoRA: the frozen base is loaded in 4-bit (NF4) so a 1.5B–3B model and its activations fit a T4;
only the LoRA matrices (bf16/fp16) are trained. Without --qlora (Mac, CPU) the base stays in
float32 — bitsandbytes' 4-bit kernels need CUDA.

The loss covers the assistant's reply only (prompt–completion format): the model is not trained
to write the system prompt or the user's question.
"""

import argparse
import json
import time
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'pocket_chat'


def load(split: str, limit: int) -> Dataset:
    rows = [json.loads(line) for line in (DATA / f'{split}.jsonl').open(encoding='utf-8')]
    if limit:
        rows = rows[:limit]
    # prompt = system + user, completion = the assistant turn → TRL masks the prompt's tokens.
    return Dataset.from_list(
        [{'prompt': r['messages'][:-1], 'completion': r['messages'][-1:]} for r in rows]
    )


def merge(model_name: str, adapter_dir: str) -> None:
    """Reload the base in 16-bit (a 4-bit base cannot be merged), apply the adapter, merge."""
    from peft import PeftModel

    base = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.float16)
    merged = PeftModel.from_pretrained(base, adapter_dir).merge_and_unload()
    merged_dir = Path(adapter_dir).with_name('pocket-merged')
    merged.save_pretrained(merged_dir, safe_serialization=True)
    AutoTokenizer.from_pretrained(adapter_dir).save_pretrained(merged_dir)
    print('merged →', merged_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='Qwen/Qwen2.5-1.5B-Instruct')
    parser.add_argument('--qlora', action='store_true', help='4-bit base (CUDA only)')
    parser.add_argument('--epochs', type=float, default=1)
    parser.add_argument('--lr', type=float, default=2e-4)
    parser.add_argument('--rank', type=int, default=16)
    parser.add_argument('--max-length', type=int, default=1024)
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--accum', type=int, default=4)
    parser.add_argument(
        '--limit', type=int, default=0, help='use only the first N rows (smoke test)'
    )
    parser.add_argument('--max-steps', type=int, default=-1)
    parser.add_argument('--out', default=str(ROOT / 'outputs' / 'pocket-lora'))
    parser.add_argument('--merge', action='store_true', help='also save base + adapter merged')
    parser.add_argument(
        '--merge-only', action='store_true', help='skip training; merge the adapter in --out'
    )
    args = parser.parse_args()
    if args.merge_only:
        merge(args.model, args.out)
        return

    cuda = torch.cuda.is_available()
    bf16 = cuda and torch.cuda.is_bf16_supported()  # T4: no bf16 → fp16
    if cuda and torch.cuda.get_device_capability()[0] < 8:
        # TRL's chunked log-prob kernel multiplies 16-bit inputs into an fp32 result with
        # `torch.addmm(..., out_dtype=float32)`, which needs compute capability 8.0+ (A100 and
        # later); on a T4 (7.5) backward fails. Its own fallback upcasts to fp32 first — the same
        # result, a little slower. TRL has no setting for it, so the module flag is switched off.
        import trl.kernels.chunked_divergence as chunked_divergence
        import trl.kernels.chunked_logprob as chunked_logprob

        chunked_logprob._MM_OUT_DTYPE = False
        chunked_divergence._MM_OUT_DTYPE = False
    train, val = load('train', args.limit), load('val', args.limit // 4 if args.limit else 0)
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    model_kwargs: dict = {}
    if args.qlora:
        from transformers import BitsAndBytesConfig

        model_kwargs['quantization_config'] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if bf16 else torch.float16,
        )
        model_kwargs['device_map'] = 'auto'
        # The modules bitsandbytes leaves unquantized (embeddings, lm_head, norms) load in the
        # checkpoint's dtype — bfloat16 for Qwen2.5. A T4 has no bf16: load them in fp16 there.
        model_kwargs['dtype'] = torch.bfloat16 if bf16 else torch.float16
    else:
        model_kwargs['dtype'] = torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)

    lora = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank * 2,
        lora_dropout=0.05,
        # Every linear layer (attention + MLP). Jaydari GPT trained q_proj/v_proj only, r=8 — and
        # its answers barely moved from the base model's.
        target_modules='all-linear',
        task_type='CAUSAL_LM',
    )
    config = SFTConfig(
        output_dir=str(ROOT / 'outputs' / 'checkpoints'),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=args.accum,
        learning_rate=args.lr,
        lr_scheduler_type='cosine',
        warmup_steps=0.03,  # transformers 5: a float below 1 is a ratio of the steps
        max_length=args.max_length,
        completion_only_loss=True,
        gradient_checkpointing=True,
        logging_steps=10,
        eval_strategy='steps' if len(val) else 'no',
        eval_steps=50,
        save_strategy='no',
        report_to='none',
        seed=42,
        bf16=bf16,
        fp16=cuda and not bf16,
        dataloader_pin_memory=cuda,
    )
    trainer = SFTTrainer(
        model=model,
        args=config,
        train_dataset=train,
        eval_dataset=val if len(val) else None,
        processing_class=tokenizer,
        peft_config=lora,
    )
    trainer.model.print_trainable_parameters()
    started = time.perf_counter()
    result = trainer.train()
    minutes = (time.perf_counter() - started) / 60
    # Save before evaluate(): an out-of-memory there must not lose the adapter.
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    metrics = trainer.evaluate() if len(val) else {}

    report = {
        'base_model': args.model,
        'qlora': args.qlora,
        'device': 'cuda' if cuda else ('mps' if torch.backends.mps.is_available() else 'cpu'),
        'train_examples': len(train),
        'val_examples': len(val),
        'epochs': args.epochs,
        'learning_rate': args.lr,
        'lora_rank': args.rank,
        'train_loss': round(result.training_loss, 4),
        'eval_loss': round(metrics['eval_loss'], 4) if 'eval_loss' in metrics else None,
        'minutes': round(minutes, 1),
        'history': [h for h in trainer.state.log_history if 'loss' in h or 'eval_loss' in h],
    }
    Path(args.out, 'training.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'history'}, indent=2))

    if args.merge:
        merge(args.model, args.out)


if __name__ == '__main__':
    main()
