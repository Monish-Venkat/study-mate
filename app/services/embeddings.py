from threading import RLock
from app.core.config import settings
import numpy as np
_model=None
# Shared by every caller that touches the model or its tokenizer: the Rust fast
# tokenizer raises "Already borrowed" if two threads configure it at once.
model_lock=RLock()

def get_model():
    global _model
    with model_lock:
        if _model is None:
            import torch
            torch.set_num_threads(settings.EMBED_THREADS)
            from sentence_transformers import SentenceTransformer
            _model=SentenceTransformer(settings.EMBED_MODEL)
        return _model

def embed_text(text:str):
    model=get_model()
    with model_lock:
        ids=model.tokenizer.encode(text,add_special_tokens=False)
        limit=max(32,model.max_seq_length-2)
        segments=[model.tokenizer.decode(ids[i:i+limit],skip_special_tokens=True) for i in range(0,len(ids),limit)] or ['']
        vectors=model.encode(segments,normalize_embeddings=True)
        average=np.mean(vectors,axis=0)
        average=average/max(float(np.linalg.norm(average)),1e-12)
        return average.tolist()

def embed_texts(texts):
    model=get_model()
    with model_lock:
        segments=[];ranges=[]
        limit=max(32,model.max_seq_length-2)
        for text in texts:
            ids=model.tokenizer.encode(text,add_special_tokens=False)
            parts=[model.tokenizer.decode(ids[i:i+limit],skip_special_tokens=True) for i in range(0,len(ids),limit)] or ['']
            ranges.append((len(segments),len(segments)+len(parts)))
            segments.extend(parts)
        if not segments:return []
        vectors=model.encode(segments,batch_size=32,normalize_embeddings=True,show_progress_bar=False)
        result=[]
        for start,end in ranges:
            mean=np.mean(vectors[start:end],axis=0)
            result.append((mean/max(float(np.linalg.norm(mean)),1e-12)).tolist())
        return result
