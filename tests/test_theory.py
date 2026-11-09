"""Every algorithm shown in the Theory section is tested here."""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent / "codebreaker/web/static/theory_engine.js"


def node(body):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const T=require({json.dumps(str(ENGINE))});console.log(JSON.stringify((()=>{{{body}}})()))"], capture_output=True, text=True, check=True).stdout)


def test_entropy_values():
    assert abs(node("return T.entropyOf('AABB')") - 1) < 1e-9
    assert abs(node("return T.entropyOf('ABCDEFGH')") - 3) < 1e-9


def test_huffman_textbook_case_and_roundtrip():
    r = node("const f={A:45,B:13,C:12,D:16,E:9,F:5};const h=T.huffman(f).codes,s=T.shannonFano(f);const m='ABACADEF';return [T.avgLength(f,h),T.avgLength(f,s),T.decodePrefix(T.encode(m,h),h),T.decodePrefix(T.encode(m,s),s)]")
    assert abs(r[0] - 2.24) < 1e-9 and r[1] >= r[0] and r[2] == "ABACADEF" and r[3] == "ABACADEF"


def test_randomness_battery_separates_good_from_bad():
    r = node("return ['good','biased','lcg','alternating'].map(k=>T.randomnessTests(T.makeBits(k,4000,7)).pass)")
    assert all(r[0].values()) and not all(r[1].values()) and not all(r[2].values()) and not all(r[3].values())


def test_berlekamp_massey_breaks_lfsr():
    r = node("const s=T.lfsr([0,2],[1,0,0,1,0,1,1,0,1],200);const b=T.berlekampMassey(s.slice(0,40));return [b.L<=9,JSON.stringify(T.bmPredict(s.slice(0,40),b.C,b.L,160))===JSON.stringify(s.slice(40))]")
    assert r == [True, True]


def test_monte_carlo_pi():
    assert abs(node("return T.monteCarloPi(200000,5).estimate") - math.pi) < 0.02


def test_metropolis_matches_a_gaussian():
    r = node("const m=T.metropolis(x=>Math.exp(-x*x/2),200000,2.5,4).samples;const a=m.reduce((p,v)=>p+v,0)/m.length;return [a,m.reduce((p,v)=>p+(v-a)**2,0)/m.length]")
    assert abs(r[0]) < 0.05 and abs(r[1] - 1) < 0.08


def test_belief_propagation_corrects_a_flipped_bit():
    assert node("const c=[1,0,1,1,0,1,0];const llr=c.map(v=>v?-2:2);llr[2]=2*0.9;const d=T.bpDecode(llr);return T.parityOK(c)&&JSON.stringify(d.bits)===JSON.stringify(c)")


def test_hmm_repairs_noisy_text():
    r = node("""const sample='THEQUICKBROWNFOXJUMPSOVERTHELAZYDOGANDTHEDOGSLEPTINTHEHOUSEWITHTHEMANWHOLIVEDTHERE'.repeat(40);const c=Array.from({length:26},()=>Array(26).fill(0.5));for(let i=0;i+1<sample.length;i++)c[sample.charCodeAt(i)-65][sample.charCodeAt(i+1)-65]++;const tr=c.map(r=>{const t=r.reduce((a,b)=>a+b,0);return r.map(v=>v/t)});const R=T.rng(3);const truth=[...sample.slice(40,240)].map(x=>x.charCodeAt(0)-65);const obs=truth.map(v=>R()<0.2?Math.floor(R()*26):v);const em=(s,o)=>s===o?0.8+0.2/26:0.2/26;const acc=a=>a.reduce((n,v,i)=>n+(v===truth[i]?1:0),0)/truth.length;return [acc(obs),acc(T.hmmDecode(obs,tr,em)),acc(T.viterbi(obs,tr,em))]""")
    assert r[1] > r[0] + 0.05 and r[2] > r[0] + 0.05


def test_mean_field_and_gibbs_denoise():
    r = node("const d=T.isingData(40,0.2,3);return [T.agreement(d.noisy,d.clean),T.agreement(T.meanField(d.noisy,40,0.7,1.0,12).q,d.clean),T.agreement(T.gibbs(d.noisy,40,0.7,1.0,60,5),d.clean)]")
    assert r[1] > r[0] + 0.1 and r[2] > r[0] + 0.1


def test_shor_simulation_factors():
    assert sorted(node("return T.shorFactor(15,7,8,3).factors")) == [3, 5]
    assert sorted(node("return T.shorFactor(21,2,9,5).factors")) == [3, 7]
    p = node("const p=T.shorProbs(15,7,8);return [p.reduce((a,b)=>a+b,0),[0,64,128,192].reduce((a,k)=>a+p[k],0)]")
    assert abs(p[0] - 1) < 1e-6 and p[1] > 0.99


def test_differential_attack_ranks_true_key():
    r = node("const R=T.rng(9);let ok=0;for(let t=0;t<60;t++){const k=[0,1,2].map(()=>Math.floor(R()*16));const c=T.diffAttack(k);const best=Math.max(...c);if(c[k[2]]===best||[...c].sort((a,b)=>b-a).slice(0,2).includes(c[k[2]]))ok++}return ok")
    assert r >= 50


def test_pollard_rho():
    assert node("return T.pollardRho(8051).factor") in (83, 97)
    assert node("return T.pollardRho(10403).factor") in (101, 103)


def test_stated_examples():
    r = node("const S=[12,5,6,11,9,0,10,13,3,14,15,8,4,7,1,2];const t=T.ddt();let m=0;for(let d=1;d<16;d++)for(let o=0;o<16;o++)m=Math.max(m,t[d][o]);return [m,T.modPow(7,2,15)]")
    assert r == [4, 4]
    assert abs(-(2 / 3 * math.log2(2 / 3) + 1 / 3 * math.log2(1 / 3)) - 0.918) < 0.001
    assert round(abs(2 * 2100 - 4000) / math.sqrt(4000), 2) == 3.16
