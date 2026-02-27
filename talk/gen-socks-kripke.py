#!/usr/bin/env python3
"""Generate the socks Kripke structure .dot file."""
from pathlib import Path

SHIRT_J = ["black", "red"]
SOCKS_J = ["black", "red", "white"]
SOCKS_R = ["blue", "yellow"]  # top row first

PROPOSITIONS = [
    ("shirt", "J", "black"),
    ("shirt", "J", "red"),
    ("socks", "J", "black"),
    ("socks", "J", "red"),
    ("socks", "J", "white"),
    ("socks", "R", "yellow"),
    ("socks", "R", "blue"),
]

states = []
for sr in SOCKS_R:
    for sj_val in ["black", "red"]:  # shirt_J
        for sk_val in SOCKS_J:
            states.append({"shirt_J": sj_val, "socks_J": sk_val, "socks_R": sr})

# neato positions are in points (72 per inch)
COL_SPACING = 130  # ~1.8"
ROW_SPACING = 110  # ~1.5"


def node_id(s):
    return f's_{s["shirt_J"][0]}{s["socks_J"][0]}{s["socks_R"][0]}'


def node_label(s):
    lines = []
    for garment, agent, color in PROPOSITIONS:
        var = f"{garment}_{agent}"
        actual = s[var]
        neg = "" if actual == color else "&not;"
        lines.append(f'{neg}{garment}<SUB>{agent}</SUB> = {color}')
    body = "<BR/>".join(lines)
    return (f'<<TABLE BORDER="0" CELLPADDING="1" CELLSPACING="0">'
            f'<TR><TD BALIGN="LEFT">{body}<BR/></TD></TR></TABLE>>')


def node_pos(idx):
    col = idx % 6
    row = idx // 6
    return f"{col * COL_SPACING},{-row * ROW_SPACING}!"


lines = ['graph kripke {',
         '  graph [outputorder=edgesfirst, splines=true, margin=0];',
         '  node [shape=box, style=filled, fillcolor=white, '
         'fontsize=9, penwidth=2, margin="0.08,0.04"];',
         '  edge [penwidth=2, fontsize=10];',
         '']

for i, s in enumerate(states):
    nid = node_id(s)
    label = node_label(s)
    pos = node_pos(i)
    lines.append(f'  {nid} [label={label}, pos="{pos}"];')

lines.append('')
lines.append('  // J edges: agent J cannot distinguish socks_R values')
lines.append('  // (states differing only in socks_R)')

for i in range(6):
    top = states[i]
    bot = states[i + 6]
    lines.append(f'  {node_id(top)} -- {node_id(bot)} '
                 f'[color=blue, label=< <FONT COLOR="blue">J</FONT> >];')

lines.append('')
lines.append('  // R edges: agent R cannot distinguish socks_J values')
lines.append('  // (states differing only in socks_J, within same shirt_J and socks_R)')

for row_start in [0, 3, 6, 9]:  # 4 groups of 3
    row = row_start // 6  # 0=top, 1=bottom
    group = [row_start, row_start + 1, row_start + 2]
    for a in range(3):
        for b in range(a + 1, 3):
            si, sj = states[group[a]], states[group[b]]
            is_long = (b - a == 2)
            if is_long:
                # Force long-range edges to route above (top row) or below (bottom row)
                port = "n" if row == 0 else "s"
                src = f'{node_id(si)}:{port}'
                dst = f'{node_id(sj)}:{port}'
            else:
                src = node_id(si)
                dst = node_id(sj)
            lines.append(f'  {src} -- {dst} '
                         f'[color=red, label=< <FONT COLOR="red">R</FONT> >];')

lines.append('}')
lines.append('')

out = Path(__file__).parent / "socks-kripke.dot"
out.write_text("\n".join(lines))
print(f"Wrote {out}")
