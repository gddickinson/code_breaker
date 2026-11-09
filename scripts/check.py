import random, sys, time
from codebreaker import ciphers
from codebreaker.ciphers.base import REGISTRY, DEMO_PLAIN
from codebreaker.ciphers.runner import attack_demo
only=sys.argv[1:]
for cid,c in REGISTRY.items():
    if only and cid not in only: continue
    t=time.time()
    try: r=attack_demo(cid,seed=4)
    except Exception as e: print(f"{cid:14} ERROR {e!r}"); continue
    print(f"{cid:14} {r.get('accuracy',r.get('success'))} {time.time()-t:.1f}s")
