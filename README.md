# Persian Poetry Generation

### A Custom AI System for Persian Poetry Generation

An independent AI engineering project focused on building a specialized language model for Persian poetry, combining custom Transformer architecture, multi-stage training, optimized inference, and linguistically guided generation.

---

## Overview

Persian Poetry Generation is a custom language modeling project designed to generate Persian poetry by learning linguistic patterns, literary styles, and poetic structures.

The system combines a decoder-only Transformer, a dedicated Persian text-processing pipeline, and a poetry generation engine with support for rhyme, Radif, poetic forms, and poet conditioning.

The project also includes an interactive Telegram bot connected to the generation engine.

## Features

- Custom Transformer language model
- Multi-stage training pipeline
- Persian prose pretraining
- Ganjoor poetry fine-tuning
- BPE tokenizer with a 16K vocabulary
- Grouped Query Attention (GQA)
- Rotary Positional Embeddings (RoPE)
- RMSNorm
- SwiGLU feed-forward networks
- Query-Key normalization
- Weight tying
- Exponential Moving Average (EMA)
- GPU-aware training configuration
- Custom Triton operations
- PyTorch fallback implementations
- KV-cache optimized generation
- Poet-conditioned generation
- Persian poetic-form conditioning
- Qafiya and Radif constraints
- Couplets and Masnavi generation
- Candidate sampling and ranking
- Syllable estimation and constraints
- Poetry analysis utilities
- Telegram bot integration

## Model Architecture

The model uses a custom decoder-only Transformer architecture.

| Component | Implementation |
|---|---|
| Model Type | Decoder-only Transformer |
| Attention | Grouped Query Attention |
| Position Encoding | RoPE |
| Normalization | RMSNorm |
| Feed-Forward Network | SwiGLU |
| Attention Normalization | QK-Norm |
| Embeddings | Weight Tying |
| Tokenizer | BPE |
| Inference | Autoregressive Generation |
| Cache | KV Cache |

The architecture is implemented in PyTorch and supports GPU acceleration.

## Training Pipeline

The training system consists of multiple stages.

### 1. Persian Prose Pretraining

The model learns general Persian language patterns using processed Persian prose.

### 2. Poetry Fine-tuning

The model is adapted to Persian poetic language using the Ganjoor poetry dataset.

### 3. Style Training

The training implementation also supports an optional style-training stage.

### Training Features

- Automatic model-size selection
- GPU memory-aware batch configuration
- Mixed-precision training
- AdamW optimization
- Gradient accumulation
- EMA weight tracking
- Validation monitoring
- Checkpoint management
- Resumable training
- Training visualization

## Generation Engine

The generation engine combines neural text generation with linguistic constraints.

### Supported Capabilities

- Poet selection
- Poetic-form selection
- Qafiya constraints
- Radif constraints
- First-hemistich continuation
- Couplet generation
- Masnavi-style paired rhymes
- Multiple candidate generation
- Candidate ranking
- Temperature sampling
- Top-p sampling
- Optional syllable-count constraints
- Optional poet-style reranking

## Performance Optimization

The project includes custom optimizations for model training and inference.

- Triton-based RMSNorm operations
- Fused SwiGLU operations
- Fused cross-entropy
- PyTorch fallback operations
- KV-cache-based generation

These optimizations are designed to improve computational efficiency.

## Telegram Bot

The project includes a Telegram bot connected to the poetry generation engine.

Its functionality includes:

- Interactive menus
- Poet and poetic-form selection
- Generation settings
- Credit management
- User management
- Administrative controls
- Generation request processing
- Persian-language interface

## Project Structure

```text
NEEEDSHOM/
│
├── poet.py
├── poet_text.py
├── ops.py
│
├── bot.py
├── core.py
├── texts.py
│
├── generate_fast.py
├── stylecheck.py
├── stylekit.py
├── textutil.py
│
├── model.py
├── train.py
├── generate.py
├── fastgen.py
├── prepare_data.py
├── lexicon.py
├── plot.py
├── ui.py
│
├── generated_poems.txt
├── training_curves.png
├── training_curves_smoke.png
│
└── README.md
```

## Installation

Install the required Python dependencies and a compatible PyTorch build for your hardware.

The project requires Python, PyTorch, and the supporting libraries used by its training and generation components.

## Usage

### Run Self-Tests

```bash
python poet.py selftest
```

### Run an End-to-End Smoke Test

```bash
python poet.py all --smoke
```

### Prepare Data and Train the Model

```bash
python poet.py all --hours 16
```

### Generate Persian Poetry

```bash
python poet.py gen --form غزلیات
```

### Generate Poetry by a Specific Poet

```bash
python poet.py gen --poet حافظ --form غزلیات
```

### Generate with Qafiya and Radif

```bash
python poet.py gen --qafiye ان --radif ما --form غزلیات
```

### Generate Multiple Candidates

```bash
python poet.py gen --poet سعدی --form غزلیات --n 3 --best-of 8
```

Generation requires the trained model checkpoint and tokenizer files.

The training pipeline also requires the appropriate source datasets.

## Evaluation

The project includes tools for inspecting model training and generated poetry.

Available evaluation utilities include:

- Training and validation loss monitoring
- Training curve visualization
- Rhyme matching
- Syllable estimation
- Repetition detection
- Literary-style analysis
- Candidate scoring

## Technologies

- Python
- PyTorch
- CUDA
- Triton
- Hugging Face Tokenizers
- Transformer Architectures
- Telegram Bot API

## Research Objectives

The project explores the development of compact, domain-specialized language models for Persian literary generation.

Its main objectives are:

- Persian language modeling
- Domain-specific model training
- Literary pattern learning
- Poetry structure modeling
- Linguistically constrained generation
- Efficient Transformer training and inference
- Practical AI application development

## Model Weights

Model checkpoints and tokenizer assets are not included in this repository.

This repository focuses on the source code, model implementation, training pipeline, and generation system.

## Author

Developed as an independent AI engineering project.

## License

License and dataset redistribution terms are subject to review before public redistribution.
