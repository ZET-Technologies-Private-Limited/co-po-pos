import sys
path = r'f:\co\CO-PO-POS\backend\app\modules\attainment_engine\services\attainment_service.py'
with open(path, 'rb') as f:
    raw = f.read()
content = raw.decode('utf-8-sig')

old = (
    "if not co_q_ids: continue\n"
    "            max_marks_co = sum(all_questions[qid] for qid in co_q_ids)"
)
new = (
    "if not co_q_ids:\n"
    "                # CO has no question mapping for this exam — include with 0 attainment\n"
    "                attainments.append({\n"
    "                    \"co_id\": co.id, \"co_code\": co.code, \"code\": co.code,\n"
    "                    \"co_statement\": co.statement, \"statement\": co.statement,\n"
    "                    \"bloom_level\": str(co.bloom_level.value if hasattr(co.bloom_level, \"value\") else co.bloom_level),\n"
    "                    \"total_students\": total_students, \"students\": total_students,\n"
    "                    \"students_cleared_threshold\": 0, \"students_cleared\": 0,\n"
    "                    \"threshold_pct\": int(threshold_pct * 100), \"threshold_marks\": 0,\n"
    "                    \"max_marks_co\": 0, \"total_obtained\": 0.0, \"marks_obtained\": 0.0,\n"
    "                    \"attainment_percentage\": 0.0, \"percentage\": 0.0, \"attainment\": 0.0,\n"
    "                    \"avg_marks_percentage\": 0.0,\n"
    "                    \"attainment_level\": _level(0.0, thresholds), \"level\": _level(0.0, thresholds),\n"
    "                    \"not_assessed\": True,\n"
    "                })\n"
    "                continue\n"
    "            max_marks_co = sum(all_questions[qid] for qid in co_q_ids)"
)

assert old in content, "Pattern not found!"
content = content.replace(old, new, 1)

with open(path, 'wb') as f:
    f.write(content.encode('utf-8-sig'))

sys.stdout.write("attainment_service.py patched OK\n")
sys.stdout.flush()
