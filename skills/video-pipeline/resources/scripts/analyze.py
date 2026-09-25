#!/usr/bin/env python3
"""analyze.py - Opção B: frame em todo shot change."""
from __future__ import annotations
import argparse, base64, json, subprocess, sys, time, urllib.request
from pathlib import Path
import cv2, pytesseract, whisper
from PIL import Image


def detect_scenes(video_path, threshold=15.0):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30.0
    scenes = []
    prev_frame = None
    scene_start_frame = 0
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            score = float(diff.mean())
            if score > threshold:
                scenes.append({"start_frame": scene_start_frame, "end_frame": frame_idx,
                              "start": scene_start_frame/fps, "end": frame_idx/fps,
                              "mid": (scene_start_frame+frame_idx)/(2*fps), "score": score})
                scene_start_frame = frame_idx
        prev_frame = gray
        frame_idx += 1
    scenes.append({"start_frame": scene_start_frame, "end_frame": frame_idx,
                  "start": scene_start_frame/fps, "end": frame_idx/fps,
                  "mid": (scene_start_frame+frame_idx)/(2*fps), "score": 0})
    cap.release()
    return scenes


def extract_frame_at(video_path, t, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-ss", "{:.2f}".format(t), "-i", str(video_path),
           "-frames:v", "1", "-q:v", "2", str(output_path)]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def ocr_frame(frame_path, lang="eng"):
    try:
        return pytesseract.image_to_string(Image.open(frame_path), lang=lang).strip()
    except Exception as e:
        return "[OCR error: " + str(e) + "]"


def is_visual_meaningful(ocr_text):
    cleaned = ocr_text.strip()
    if len(cleaned) < 10: return True
    alnum = sum(c.isalnum() for c in cleaned)
    return alnum < len(cleaned) * 0.5


def call_minimax_vision(frame_path, api_key, max_tokens=300):
    with open(frame_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    payload = {
        "model": "MiniMax-Vision-01",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Descreva em JSON com description e tags."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}}
        ]}],
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request("https://api.MiniMax.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            try: return json.loads(content)
            except json.JSONDecodeError: return {"description": content, "tags": []}
    except Exception as e:
        return {"description": "[Vision API error: " + str(e) + "]", "tags": []}


def analyze(video_path, output_dir, vision_key=None, scene_threshold=15.0,
           whisper_model="base", lang="auto"):
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    ocr_dir = output_dir / "ocr"
    vision_dir = output_dir / "vision"
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    frames_dir.mkdir(exist_ok=True)
    ocr_dir.mkdir(exist_ok=True)
    vision_dir.mkdir(exist_ok=True)
    timeline = []

    print("[1/4] Extracting audio from " + video_path.name)
    t0 = time.time()
    audio_path = audio_dir / "audio.mp3"
    subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ar", "16000",
                    "-ac", "1", "-c:a", "libmp3lame", "-q:a", "4", str(audio_path)],
                   capture_output=True)
    print("  Audio: " + str(round(time.time()-t0, 1)) + "s")

    print("[2/4] Whisper " + whisper_model)
    t0 = time.time()
    asr_model = whisper.load_model(whisper_model)
    asr_result = asr_model.transcribe(str(audio_path), verbose=False,
                                       language=None if lang == "auto" else lang)
    asr_segments = asr_result["segments"]
    detected_lang = asr_result.get("language", "en")
    print("  " + str(len(asr_segments)) + " segments " + str(round(time.time()-t0, 1)) + "s, " + detected_lang)

    print("[3/4] Shot detection threshold=" + str(scene_threshold))
    t0 = time.time()
    scenes = detect_scenes(video_path, threshold=scene_threshold)
    print("  " + str(len(scenes)) + " scenes " + str(round(time.time()-t0, 1)) + "s")

    print("[4/4] Process " + str(len(scenes)) + " scenes")
    t0 = time.time()
    stats = {"scenes_total": len(scenes), "frames_extracted": 0,
             "ocr_calls": 0, "vision_api_calls": 0, "ocr_meaningful": 0}

    for scene_idx, scene in enumerate(scenes):
        mid_time = scene["mid"]
        asr_at_scene = None
        for seg in asr_segments:
            if seg["start"] <= mid_time <= seg["end"]:
                asr_at_scene = seg
                break
        asr_text = asr_at_scene["text"].strip() if asr_at_scene else ""

        entry = {"t": round(mid_time, 2), "scene_idx": scene_idx,
                 "asr_text": asr_text, "kind": "asr+frame"}

        frame_name = "frame_scene" + str(scene_idx).zfill(3) + "_t" + str(int(mid_time*10)).zfill(6) + ".jpg"
        frame_path = frames_dir / frame_name
        if not extract_frame_at(video_path, mid_time, frame_path):
            timeline.append(entry)
            continue
        stats["frames_extracted"] += 1
        entry["frame"] = frame_name

        stats["ocr_calls"] += 1
        ocr_text = ocr_frame(frame_path, lang=detected_lang if detected_lang in ("eng","por","spa") else "eng")
        ocr_path = ocr_dir / (frame_name + ".txt")
        ocr_path.write_text(ocr_text, encoding="utf-8")
        entry["ocr_text"] = ocr_text

        if vision_key and is_visual_meaningful(ocr_text):
            stats["vision_api_calls"] += 1
            stats["ocr_meaningful"] += 1
            vision_data = call_minimax_vision(frame_path, vision_key)
            entry["vision"] = vision_data
            (vision_dir / (frame_name + ".json")).write_text(
                json.dumps(vision_data, indent=2, ensure_ascii=False), encoding="utf-8")
        timeline.append(entry)

    print("  Frames: " + str(stats["frames_extracted"]) + "/" + str(len(scenes)))

    output = {"video": str(video_path), "output_dir": str(output_dir),
              "duration_sec": scenes[-1]["end"] if scenes else 0,
              "language": detected_lang,
              "pipeline": {"whisper_model": whisper_model,
                           "scene_threshold": scene_threshold,
                           "vision_api_used": vision_key is not None,
                           "mode": "B: extract frame in every shot change"},
              "stats": stats, "scenes_total": len(scenes), "timeline": timeline}

    (output_dir / "timeline.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "transcript.json").write_text(json.dumps({"language": detected_lang, "segments": asr_segments}, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--vision-key")
    parser.add_argument("--scene-threshold", type=float, default=15.0)
    parser.add_argument("--whisper-model", default="base", choices=["tiny","base","small","medium","large"])
    parser.add_argument("--lang", default="auto")
    args = parser.parse_args()
    result = analyze(Path(args.video), Path(args.output_dir),
                     vision_key=args.vision_key,
                     scene_threshold=args.scene_threshold,
                     whisper_model=args.whisper_model, lang=args.lang)
    print("=== Stats ===")
    print("  Scenes: " + str(result["scenes_total"]))
    print("  Frames: " + str(result["stats"]["frames_extracted"]))
    print("  OCR: " + str(result["stats"]["ocr_calls"]))
    print("  Vision: " + str(result["stats"]["vision_api_calls"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
