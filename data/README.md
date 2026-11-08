# data/pocket_chat — the PocketGPT chat dataset

Built by `training/build_dataset.py` (fixed seeds — the same command rebuilds the same files).

| Split | EN | RU | UZ | Total |
| --- | ---: | ---: | ---: | ---: |
| train | 1,200 | 1,200 | 1,200 | 3,600 |
| val | 50 | 50 | 50 | 150 |
| test (frozen) | 100 | 100 | 100 | 300 |

Each line: `{"messages": [system, user, assistant], "lang": "EN|RU|UZ", "source": "…"}`. The system
message is PocketGPT's own prompt (the backend's default), so the model trains on the frame it serves.

## Sources and licences

| Source | Used for | Licence |
| --- | --- | --- |
| [CohereLabs/aya_dataset](https://huggingface.co/datasets/CohereLabs/aya_dataset) | English, Russian (human-written Q&A) | Apache-2.0 |
| [OpenAssistant/oasst2](https://huggingface.co/datasets/OpenAssistant/oasst2) | Russian (first turns, best-ranked reply) | Apache-2.0 |
| [UAzimov/uzbek-instruct-llm](https://huggingface.co/datasets/UAzimov/uzbek-instruct-llm) | Uzbek instruction chats | Apache-2.0 |

The data is redistributed here under those licences, with this attribution. It is not reviewed by
hand: the Uzbek source is largely machine-translated, and some answers are short lists of names.
