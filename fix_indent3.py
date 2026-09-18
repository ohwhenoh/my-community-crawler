with open('crawler_slack.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('crawler_slack.py', 'w', encoding='utf-8') as f:
    for line in lines:
        if 'return fx_text + "' in line:
            f.write('        return fx_text + "\\n" + bond_text + "\\n"\n')
        elif line.strip() == '" + bond_text + "':
            pass
        elif 'return "⚠️ 거시경제 지표 실시간 수집 지연' in line:
            f.write('        return "⚠️ 거시경제 지표 실시간 수집 지연\\n\\n"\n')
        else:
            f.write(line)
