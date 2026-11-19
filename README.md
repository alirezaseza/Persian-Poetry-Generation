# Persian Poetry Generation

A Persian poetry generation system built with a custom Transformer architecture, multi-stage training pipeline, and linguistically guided text generation.

## Overview

This project explores the development of a custom language model specialized in Persian poetry generation.

The system combines language model pretraining, poetry fine-tuning, and rule-based linguistic evaluation to generate Persian poems with attention to poetic structure, rhyme, and literary style.

The project includes a custom Transformer implementation, training infrastructure, generation engine, and Telegram bot integration.

## Key Features

- Custom decoder-only Transformer architecture.
- Multi-stage training pipeline.
- Prose pretraining and Persian poetry fine-tuning.
- Byte Pair Encoding (BPE) tokenizer.
- Grouped Query Attention (GQA).
- Rotary Positional Embeddings (RoPE).
- RMSNorm and SwiGLU.
- Exponential Moving Average (EMA) training support.
- Rhyme and Radif-aware generation.
- Couplets and different Persian poetic forms.
- Candidate generation and ranking.
- Vocabulary and lexical constraints.
- GPU-aware model size selection.
- Telegram bot integration.

## Model Architecture

The model uses a decoder-only Transformer inspired by modern language model architectures.

Core components:

- Multi-layer Transformer blocks
- Grouped Query Attention
- Rotary Positional Embeddings
- RMSNorm
- SwiGLU feed-forward networks
- Weight tying between token embeddings and output projection

The training pipeline supports multiple model configurations, from small to extra-large. The automatic configuration can select a model size based on available GPU resources and the training budget.

## Training Pipeline

The system supports three main training stages:

1. **Pretraining:** Learning general language patterns from Persian prose.
2. **Fine-tuning:** Adapting the model to Persian poetry.
3. **Style training:** An additional stage for refining literary characteristics.

Training includes validation, checkpoint management, EMA evaluation, and loss monitoring.

## Generation System

The generation engine supports:

- Persian poetic forms
- Poet-specific generation
- Rhyme and Radif constraints
- First-hemistich continuation
- Couplets generation
- Candidate sampling and ranking
- Optional syllable-count constraints

## Project Structure

| File | Description |
|---|---|
| `poet.py` | Main model, training pipeline, and generation |
| `model.py` | Transformer implementation |
| `train.py` | Training implementation |
| `generate.py` | Generation interface |
| `fastgen.py` | Optimized generation engine |
| `ops.py` | Computational optimizations |
| `prepare_data.py` | Dataset preparation |
| `stylecheck.py` | Poetry evaluation |
| `stylekit.py` | Style-related utilities |
| `bot.py` | Telegram bot |
| `core.py` | Bot backend and application logic |
| `lexicon.py` | Lexical utilities |

## Technology Stack

- Python
- PyTorch
- CUDA
- Transformer architectures
- Tokenization and BPE
- Telegram Bot API

## Research and Engineering Goals

The main goal is to explore how a relatively compact, domain-specialized language model can learn Persian literary patterns and generate structured poetry.

The project focuses on model architecture, training efficiency, linguistic constraints, and practical text generation.

## Model Weights

Model checkpoints and tokenizer files are not included in this repository.

The repository currently focuses on source code and implementation details.

## License

License and dataset redistribution terms are subject to review. See the repository documentation for updates.
