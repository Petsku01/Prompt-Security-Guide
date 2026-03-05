# garak, LLM vulnerability scanner

*Generative AI Red-teaming & Assessment Kit*

`garak` checks if an LLM can be made to fail in a way we don't want. `garak` probes for hallucination, data leakage, prompt injection, misinformation, toxicity generation, jailbreaks, and many other weaknesses. If you know `nmap` or `msf` / Metasploit Framework, garak does somewhat similar things to them, but for LLMs. 

`garak` focuses on ways of making an LLM or dialog system fail. It combines static, dynamic, and adaptive probes to explore this.

`garak`'s a free tool. We love developing it and are always interested in adding functionality to support applications. 

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests/Linux](https://github.com/NVIDIA/garak/actions/workflows/test_linux.yml/badge.svg)](https://github.com/NVIDIA/garak/actions/workflows/test_linux.yml)
[![Tests/Windows](https://github.com/NVIDIA/garak/actions/workflows/test_windows.yml/badge.svg)](https://github.com/NVIDIA/garak/actions/workflows/test_windows.yml)
[![Tests/OSX](https://github.com/NVIDIA/garak/actions/workflows/test_macos.yml/badge.svg)](https://github.com/NVIDIA/garak/actions/workflows/test_macos.yml)
[![Documentation Status](https://readthedocs.org/projects/garak/badge/?version=latest)](http://garak.readthedocs.io/en/latest/?badge=latest)
[![arXiv](https://img.shields.io/badge/cs.CL-arXiv%3A2406.11036-b31b1b.svg)](https://arxiv.org/abs/2406.11036)
[![discord-img](https://img.shields.io/badge/chat-on%20discord-yellow.svg)](https://discord.gg/uVch4puUCs)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/garak)](https://pypi.org/project/garak)
[![PyPI](https://badge.fury.io/py/garak.svg)](https://badge.fury.io/py/garak)
[![Downloads](https://static.pepy.tech/badge/garak)](https://pepy.tech/project/garak)
[![Do