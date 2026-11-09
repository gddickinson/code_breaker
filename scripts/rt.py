from codebreaker.ciphers import REGISTRY
bad=0
for c in REGISTRY.values():
    try: d=c.detail()
    except Exception as e: print('ERR',c.id,repr(e)); bad+=1; continue
    print(f"{c.id:12} {str(d['example_cipher'])[:32]:34} {d['example_back']}")
print(len(REGISTRY),'bad',bad)
