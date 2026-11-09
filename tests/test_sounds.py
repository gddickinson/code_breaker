"""Sound Lab: synthetic-song control, sequence statistics, identification on reference recordings, and the API."""
import base64
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.sound import audio, identify, service, song, synth
from codebreaker.web.app import app

client = TestClient(app)
REF = json.loads((service.SOUNDS / "sources.json").read_text())


def test_synthetic_song_is_segmented_and_typed():
    scores = []
    for seed in range(5):
        x, sr, truth = synth.song(40, seed)
        r = song.analyse(x, sr)
        assert len(r["sequence"]) == len(truth)
        scores.append(song.agreement(truth, r["sequence"]))
    assert np.mean(scores) >= 0.75


def test_sequence_statistics():
    s = song.sequence_stats("ABABABAB")
    assert s["types"] == 2 and s["entropy_bits"] == 1.0 and s["conditional_bits"] == 0.0
    assert song.agreement("AABB", "BBAA") == 1.0


def test_wav_round_trip():
    x = np.sin(np.linspace(0, 200, 8000)).astype(np.float32) * 0.5
    y, sr = audio.decode(audio.wav_bytes(x, 8000))
    assert sr == 8000 and np.allclose(x, y, atol=1e-3)


@pytest.mark.parametrize("ref", [r for r in REF if (service.SOUNDS / r["file"]).exists()], ids=lambda r: r["file"])
def test_birdnet_names_the_reference_species_first(ref):
    x, sr = audio.load(str(service.SOUNDS / ref["file"]), 30)
    b = identify.birds(x, sr)
    assert b["available"] and b["species"][0]["scientific"] == ref["species"]


def test_yamnet_hears_a_bird():
    x, sr = audio.load(str(service.SOUNDS / "Turdus_merula_2.ogg"), 20)
    names = [c["name"] for c in identify.sounds(x, sr)["classes"][:5]]
    assert "Bird" in names or "Animal" in names


def test_api_example_and_upload():
    r = client.post("/api/sounds/analyse", json={"example": "synthetic"}).json()
    assert r["truth"] and r["agreement"] is not None and r["spectrogram"].startswith("data:image/png")
    x, sr, _ = synth.song(10, 2)
    up = client.post("/api/sounds/analyse", json={"data": base64.b64encode(audio.wav_bytes(x, sr)).decode()})
    assert up.status_code == 200 and up.json()["stats"]["syllables"] == 10
    assert client.post("/api/sounds/analyse", json={"data": ""}).status_code == 400
