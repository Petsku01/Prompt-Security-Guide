# LLM Attacks

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This is the official repository for "[Universal and Transferable Adversarial Attacks on Aligned Language Models](https://arxiv.org/abs/2307.15043)" by [Andy Zou](https://andyzoujm.github.io/), [Zifan Wang](https://sites.google.com/west.cmu.edu/zifan-wang/home), [Nicholas Carlini](https://nicholas.carlini.com/), [Milad Nasr](https://people.cs.umass.edu/~milad/), [J. Zico Kolter](https://zicokolter.com/), and [Matt Fredrikson](https://www.cs.cmu.edu/~mfredrik/).

Check out our [website and demo here](https://llm-attacks.org/).

## Updates
- (2024-08-01) We release `nanogcg`, a fast and easy-to-use implementation of the GCG algorithm. `nanogcg` can be installed via pip and the code is available [here](https://github.com/GraySwanAI/nanoGCG/tree/main).
- (2023-08-16) We include a notebook `demo.ipynb` (or see it on [Colab](https://colab.research.google.com/drive/1dinZSyP1E4KokSLPcCh1JQFUFsN-WV--?usp=sharing)) containing the minimal implementation of GCG for jailbreaking LLaMA-2 for generating harmful completion.


## Table of Contents

- [Installation](#installation)
- [Models](#models)
- [Experiments](#experiments)
- [Demo](#demo)
- [Reproducibility](#reproducibility)
- [License](#license)
- [Citation](#citation)

## Installation

We need the newest version of FastChat `fschat==0.2.23` and please make sure to install this version. The `llm-attacks` package can be installed by running the following command at the root of this repository:

```bash
pip install -e .
```

## Models

Please follow the instructions to download Vicuna-7B or/and LLaMA-2-7B-Chat first (we use the weights converted by HuggingFace [here](https://huggingface.co/meta-llama/Llama-2-7b-hf)).  Our script by default assumes models are stored in a root directory named as `/DIR`. To modify the paths to your models and tokenizers, please add the following lines in `experiments/configs/