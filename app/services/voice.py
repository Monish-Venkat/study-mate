import asyncio
import io
import os
import subprocess
import shutil
import tempfile
import threading
from pathlib import Path
import numpy as np
from app.core.config import settings
from app.services.llm_client import GenerationUnavailable

_lock=threading.Lock()
_model=None

def transcribe_audio(content):
    if not content or len(content)>10*1024*1024:raise ValueError('Provide an audio file no larger than 10 MB.')
    global _model
    try:
        import whisper
        with tempfile.TemporaryDirectory(prefix='studymate-voice-') as folder:
            path=Path(folder)/'input.audio'
            path.write_bytes(content)
            executable=shutil.which('ffmpeg')
            if not executable:
                import imageio_ffmpeg
                executable=imageio_ffmpeg.get_ffmpeg_exe()
            result=subprocess.run([executable,'-nostdin','-v','error','-i',str(path),'-t','120','-f','s16le','-ac','1','-ar','16000','pipe:1'],capture_output=True,timeout=40,check=True)
            audio=np.frombuffer(result.stdout,np.int16).astype(np.float32)/32768.0
            if not len(audio):raise ValueError('No audio could be decoded.')
            with _lock:
                if _model is None:_model=whisper.load_model(settings.WHISPER_MODEL,download_root=str(Path(settings.DATA_DIR)/'models'/'whisper'))
                output=_model.transcribe(audio,fp16=False)
            return {'text':output['text'].strip(),'language':output.get('language','en'),'limit_seconds':120}
    except (ImportError,FileNotFoundError) as exc:
        raise GenerationUnavailable('Voice input requires openai-whisper and FFmpeg. Install them and retry.') from exc
    except (subprocess.SubprocessError,RuntimeError) as exc:
        raise GenerationUnavailable('Audio could not be transcribed. Check the recording, FFmpeg and Whisper model availability.') from exc

def synthesize(text,language):
    if not settings.ENABLE_GTTS:raise GenerationUnavailable('Speech output is disabled. Set ENABLE_GTTS=true to enable Google text-to-speech; response text will be sent to Google.')
    try:
        from gtts import gTTS
        output=io.BytesIO()
        gTTS(text=text,lang=language,timeout=(10,30)).write_to_fp(output)
        return output.getvalue()
    except Exception as exc:
        raise GenerationUnavailable('Speech synthesis is unavailable for this language or network connection.') from exc
