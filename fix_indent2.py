with open('crawler_slack.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('crawler_slack.py', 'w', encoding='utf-8') as f:
    for line in lines:
        if line.startswith('bond_text = "📉'):
            f.write('        bond_text = "📉 *[시장 금리 방향 (10년물 국채 ETF 일일 변동폭 기준)]*\\n"\n')
        elif line.strip() == '"' and 'bond_text' not in line:
            pass # ignore stray quotes
        elif line.startswith('                    bond_text += f"🔴'):
            f.write('                    bond_text += f"🔴 *{base_str} ({diff_pct:+.2f}%)* ➡️ 시장금리 상승(위험)\\n"\n')
        elif line.startswith('                    bond_text += f"🟡'):
            f.write('                    bond_text += f"🟡 *{base_str} ({diff_pct:+.2f}%)* ➡️ 시장금리 소폭 상승\\n"\n')
        elif line.startswith('                    bond_text += f"🟢'):
            f.write('                    bond_text += f"🟢 *{base_str} ({diff_pct:+.2f}%)* ➡️ 시장금리 하락/안정\\n"\n')
        else:
            f.write(line)
