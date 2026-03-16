import sys, re
path = r'f:\co\CO-PO-POS\backend\app\modules\attainment_engine\services\attainment_service.py'
with open(path,'rb') as f: raw=f.read()
content = raw.decode('utf-8-sig')
sys.stdout.write(f"len={len(content)}\n")
sys.stdout.flush()

# search for the skip pattern
for pat in ['if not co_q_ids', 'co_q_ids: continue', 'co_question_map']:
    idx = content.find(pat)
    sys.stdout.write(f"'{pat}' at {idx}\n")
    if idx >= 0:
        sys.stdout.write(repr(content[idx-80:idx+80]) + "\n\n")
sys.stdout.flush()
