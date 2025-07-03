import math
import wave
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def make_image(path: Path) -> None:
    Image.new("RGB", (10, 10), color="skyblue").save(path)


def make_audio(path: Path, duration: float = 1.0, rate: int = 16000) -> None:
    freq = 440.0
    samples = int(duration * rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(samples):
            value = int(32767 * math.sin(2 * math.pi * freq * (i / rate)))
            frames += int(value).to_bytes(2, byteorder="little", signed=True)
        wf.writeframes(frames)


def make_video(path: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to generate sample video")
    tmp_img = path.with_suffix(".jpg")
    tmp_wav = path.with_suffix(".wav")
    make_image(tmp_img)
    make_audio(tmp_wav)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(tmp_img),
            "-i",
            str(tmp_wav),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-t",
            "1",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    tmp_img.unlink()
    tmp_wav.unlink()


def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)
    make_image(data_dir / "sample_image.jpg")
    make_audio(data_dir / "sample_audio.wav")
    try:
        make_video(data_dir / "sample_video.mp4")
    except Exception as exc:
        print(f"Warning: {exc}. Video not generated.")


if __name__ == "__main__":
    main()
