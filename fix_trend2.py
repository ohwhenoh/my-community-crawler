import re

with open('crawler_slack.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'def generate_korean_outreach_report\(\):\n.*?target = random\.choice\(KOREAN_TARGET_DATABASE\)', re.DOTALL)

new_func_top = """def generate_korean_outreach_report():
    import json
    with open('targets.json', 'r', encoding='utf-8') as f:
        KOREAN_TARGET_DATABASE = json.load(f)
        
    si = SalesIntelligence()
    target, trend_reason = si.get_best_target(KOREAN_TARGET_DATABASE)
    crm_data = si.get_crm_data(target['company'])
    ranked_personas = si.rank_personas(target['personas'])
"""

content = pattern.sub(new_func_top, content)

with open('crawler_slack.py', 'w', encoding='utf-8') as f:
    f.write(content)
