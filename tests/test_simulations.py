"""The browser simulators must produce exactly what the Python ciphers produce."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.machines import enigma
from codebreaker.ciphers.polygraphic import pf_e
from codebreaker.ciphers.transposition import _grille_order

ENGINE = Path(__file__).resolve().parent.parent / "codebreaker/web/static/sim_engine.js"
CASES = [("HELLOWORLDTHEQUICKBROWNFOX" * 12, ["I", "II", "III"], "AAA", "AAA", ""), ("ATTACKATDAWN" * 40, ["IV", "II", "V"], "BXK", "ADU", "AV BS CG DL FU HZ"), ("Q" * 700, ["III", "I", "II"], "ZZA", "VEQ", "QW")]


def node(script):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const S=require({json.dumps(str(ENGINE))});{script}"], capture_output=True, text=True, check=True).stdout)


@pytest.mark.parametrize("text,rotors,ring,start,plug", CASES)
def test_enigma_matches_python(text, rotors, ring, start, plug):
    spec = json.dumps({"rotors": rotors, "ring": ring, "start": start, "plugboard": plug})
    assert node(f"console.log(JSON.stringify(new S.Enigma({spec}).run({json.dumps(text)})))") == enigma(text, " ".join(rotors), ring, start, plug)


def test_playfair_matches_python():
    msg, key = "HIDE THE GOLD BALLOON UNDER THE OLD STUMP", "PLAYFAIR"
    got = node(f"const q=S.playfairSquare({json.dumps(key)});console.log(JSON.stringify(S.playfairPairs({json.dumps(msg)}).map(([a,b])=>S.playfairStep(q,a,b).out).join('')))")
    assert got == pf_e(msg, key)


def test_vigenere_matches_python():
    got = node("console.log(JSON.stringify(S.vigenereTrace('ATTACK AT DAWN','LEMON').map(x=>x.c).join('')))")
    assert got == REGISTRY["vigenere"].encrypt("ATTACK AT DAWN", key="LEMON")


def test_grille_matches_python():
    key = "012301230"
    got = node(f"let h=S.grilleHoles({json.dumps(key)}),o=[];for(let q=0;q<4;q++){{o=o.concat(h.map(p=>p[0]*6+p[1]).sort((a,b)=>a-b));h=S.grilleRotate(h)}};console.log(JSON.stringify(o))")
    assert got == _grille_order(key)
    assert sorted(got) == list(range(36))
