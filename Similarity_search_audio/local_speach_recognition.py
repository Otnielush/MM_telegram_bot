import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import gc
import pandas as pd

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
model_id = "openai/whisper-large-v3"


Model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True,
                                                  use_safetensors=True, device_map=device).eval()
Processor = AutoProcessor.from_pretrained(model_id)
torch.set_float32_matmul_precision('high')

free = torch.cuda.mem_get_info()[0] / 1024 ** 3
Batch_size = int(free // 1.9)
print(f'{device = } | {torch_dtype = } | {Batch_size = }')


pipe = pipeline(
    "automatic-speech-recognition",
    model=Model,
    tokenizer=Processor.tokenizer,
    feature_extractor=Processor.feature_extractor,
    max_new_tokens=400,
    chunk_length_s=30,  # or Sequential or chunking
    batch_size=Batch_size,
    return_timestamps=True,
    torch_dtype=torch_dtype,
)


def recognize_audio_local(file_path: str) -> pd.DataFrame:
    with torch.inference_mode():
          result = pipe(file_path, generate_kwargs={"num_beams": 5})
    gc.collect()
    torch.cuda.empty_cache()
    ds = pd.DataFrame()    
    ds['start'] = [r['timestamp'][0] for r in result['chunks']]
    ds['end'] = [r['timestamp'][1] for r in result['chunks']]
    ds['text'] = [r['text'] for r in result['chunks']]
    ds = ds[ds['text'].notna()]
    return ds


