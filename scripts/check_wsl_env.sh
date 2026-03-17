#!/bin/bash
source ~/venvs/qwen3tts/bin/activate
echo "Python: $(python --version)"
python -c "from qwen_tts import Qwen3TTSModel; print('qwen_tts: OK')"
python -c "import soundfile; print('soundfile: OK')"
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
echo "VRAM: $(nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader 2>/dev/null || echo 'N/A')"
