with open('crawler_slack.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's verify what the generate_korean_outreach_report function looks like
import re
match = re.search(r'def generate_korean_outreach_report\(\):.*?(?=def send_to_slack)', content, re.DOTALL)
if match:
    print(match.group(0))
