"""Generate notebooks/09_sim_connectivity_analysis.ipynb from source.

Keeping the notebook generated from a script avoids hand-editing notebook JSON
and lets the SIM analysis stay in sync with src/research/sim_technologies.py.
"""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "09_sim_connectivity_analysis.ipynb"

nb = nbf.v4.new_notebook()
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

md(
    "# 09 — SIM & Cellular Connectivity Analysis\n"
    "\n"
    "Analyzes the **de-hardwaring ladder** of cellular identity — eSIM → iSIM → "
    "SoftSIM — alongside the GSMA specifications (SGP.32 / SGP.41 / SGP.42) and "
    "adjacent network evolutions (NTN, 5G-Advanced, 6G), and **compares them "
    "against traditional communication methods** (removable SIM, analog PSTN "
    "line, wired Ethernet).\n"
    "\n"
    "Outputs feed the frontend `SIM & Connectivity` page:\n"
    "- `frontend/data/sim_technologies.json` — tagged catalog (canonical source: "
    "`src/research/sim_technologies.py`)\n"
    "- `frontend/data/sim_comparison.json` — derived comparison vs traditional methods\n"
    "\n"
    "分析行動身分的**去硬體化階梯**（eSIM → iSIM → SoftSIM），並與**傳統通訊方式**"
    "（可插拔 SIM、類比 PSTN 線路、有線乙太網路）比較。"
)

code(
    "import sys\n"
    "import json\n"
    "import os\n"
    "from pathlib import Path\n"
    "\n"
    "# Resolve repo root whether run from repo root or notebooks/ dir.\n"
    "ROOT = Path.cwd()\n"
    "if not (ROOT / 'src').exists() and (ROOT.parent / 'src').exists():\n"
    "    ROOT = ROOT.parent\n"
    "os.chdir(ROOT)\n"
    "sys.path.insert(0, str(ROOT))\n"
    "\n"
    "import pandas as pd\n"
    "import numpy as np\n"
    "import matplotlib.pyplot as plt\n"
    "import seaborn as sns\n"
    "import warnings\n"
    "warnings.filterwarnings('ignore')\n"
    "\n"
    "from src.research.sim_technologies import build_sim_catalog\n"
    "\n"
    "%matplotlib inline\n"
    "sns.set_theme(style='whitegrid')\n"
    "\n"
    "PROCESSED = Path('data/processed')\n"
    "FRONTEND_DATA = Path('frontend/data')\n"
    "PROCESSED.mkdir(parents=True, exist_ok=True)"
)

md(
    "## 1. Load the tagged SIM technology catalog\n"
    "Each entry carries machine-readable `tags` and a bilingual `maturity` label so the "
    "frontend can render and filter them consistently."
)
code(
    "catalog = build_sim_catalog()\n"
    "df = pd.DataFrame(catalog)\n"
    "print(f'Loaded {len(df)} SIM technologies / specifications')\n"
    "df['tag_str'] = df['tags'].apply(lambda t: ', '.join(t))\n"
    "display(df[['id', 'name_en', 'maturity', 'footprint_mm2', 'power_en', 'tag_str']])"
)

md(
    "## 2. Define traditional baselines\n"
    "We anchor the new SIM technologies against the incumbents they aim to replace, scoring "
    "each on footprint, a relative power index (removable SIM = 100), a relative SIM-related "
    "BOM-cost index, the provisioning model, and whether the operator profile is remotely switchable."
)
code(
    "# (footprint_mm2, power_index, bom_index, provisioning, remote_switchable, kind)\n"
    "BASELINES = [\n"
    "    {'option': 'Analog PSTN line',  'footprint_mm2': None, 'power_index': None, 'bom_index': 60,\n"
    "     'provisioning': 'Physical wiring', 'remote_switchable': False, 'kind': 'traditional'},\n"
    "    {'option': 'Wired Ethernet/IP', 'footprint_mm2': None, 'power_index': None, 'bom_index': 50,\n"
    "     'provisioning': 'Physical wiring / DHCP', 'remote_switchable': False, 'kind': 'traditional'},\n"
    "    {'option': 'Removable SIM (2FF/3FF/4FF)', 'footprint_mm2': 120, 'power_index': 100, 'bom_index': 100,\n"
    "     'provisioning': 'Manual card swap', 'remote_switchable': False, 'kind': 'traditional'},\n"
    "]\n"
    "\n"
    "# Map the catalog onto the same comparison axes.\n"
    "POWER_INDEX = {'esim': 100, 'isim': 30, 'softsim': 5}          # iSIM ~70% lower; SoftSIM no SIM-HW draw\n"
    "BOM_INDEX   = {'esim': 70,  'isim': 25, 'softsim': 0}           # relative SIM-related BOM cost\n"
    "PROVISIONING = {\n"
    "    'esim': 'OTA RSP (SGP.22)', 'isim': 'OTA RSP via eIM (SGP.42)',\n"
    "    'softsim': 'Software / cloud download', 'sgp32': 'eIM RSP (SMS-free)',\n"
    "    'sgp41-42': 'eIM RSP (SMS-free)', 'ntn': 'Inherited (satellite handover)',\n"
    "    '5g-advanced': 'Slice-aware (SIM-bound)', '6g': 'Research',\n"
    "}\n"
    "\n"
    "rows = list(BASELINES)\n"
    "for c in catalog:\n"
    "    rows.append({\n"
    "        'option': c['name_en'],\n"
    "        'footprint_mm2': c['footprint_mm2'],\n"
    "        'power_index': POWER_INDEX.get(c['id']),\n"
    "        'bom_index': BOM_INDEX.get(c['id']),\n"
    "        'provisioning': PROVISIONING.get(c['id'], 'N/A'),\n"
    "        'remote_switchable': c['id'] not in ('6g',),\n"
    "        'kind': 'new',\n"
    "    })\n"
    "comp = pd.DataFrame(rows)\n"
    "display(comp)"
)

md(
    "## 3. The de-hardwaring trend — footprint & power collapse\n"
    "From removable SIM (~120 mm², 100% power) down to SoftSIM (0 mm², ~5% SIM-related power draw)."
)
code(
    "ladder = comp[comp['option'].str.contains('Removable SIM|eSIM|iSIM|SoftSIM', regex=True)].copy()\n"
    "ladder = ladder.dropna(subset=['footprint_mm2', 'power_index'])\n"
    "order = ['Removable SIM (2FF/3FF/4FF)', 'eSIM (Embedded SIM)',\n"
    "         'iSIM (Integrated SIM)', 'SoftSIM / vSIM (Software / Virtual SIM)']\n"
    "ladder['option'] = pd.Categorical(ladder['option'], categories=order, ordered=True)\n"
    "ladder = ladder.sort_values('option')\n"
    "labels = ['Removable SIM', 'eSIM', 'iSIM', 'SoftSIM']\n"
    "\n"
    "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
    "axes[0].bar(labels, ladder['footprint_mm2'], color='#3498db', edgecolor='k')\n"
    "axes[0].set_title('Board Footprint Collapse (mm\\u00b2)', fontweight='bold')\n"
    "axes[0].set_ylabel('mm\\u00b2')\n"
    "axes[1].bar(labels, ladder['power_index'], color='#e67e22', edgecolor='k')\n"
    "axes[1].set_title('Relative SIM Power Index (Removable = 100)', fontweight='bold')\n"
    "axes[1].set_ylabel('Power index')\n"
    "for ax in axes:\n"
    "    ax.set_xlabel('De-hardwaring ladder')\n"
    "fig.suptitle('eSIM \\u2192 iSIM \\u2192 SoftSIM: shrinking footprint & power', fontsize=14, fontweight='bold')\n"
    "fig.tight_layout()\n"
    "fig.savefig(PROCESSED / 'sim_dehardwaring.png', dpi=150)\n"
    "plt.show()"
)

md("## 4. Maturity distribution across catalog")
code(
    "fig, ax = plt.subplots(figsize=(8, 4))\n"
    "mat = df['maturity'].value_counts().reindex(['mainstream', 'emerging', 'frontier', 'standard']).dropna()\n"
    "colors = {'mainstream': '#1e40af', 'emerging': '#065f46', 'frontier': '#5b21b6', 'standard': '#92400e'}\n"
    "ax.bar(mat.index, mat.values, color=[colors[m] for m in mat.index], edgecolor='k')\n"
    "ax.set_title('SIM Technologies & Specs by Maturity', fontweight='bold')\n"
    "ax.set_ylabel('Count')\n"
    "fig.tight_layout()\n"
    "fig.savefig(PROCESSED / 'sim_maturity.png', dpi=150)\n"
    "plt.show()"
)

md(
    "## 5. Traditional vs SIM-evolution comparison matrix\n"
    "Provisioning model and remote switchability — the operational gap between incumbents and "
    "software-defined identity."
)
code(
    "matrix = comp[['option', 'kind', 'footprint_mm2', 'power_index', 'bom_index',\n"
    "               'provisioning', 'remote_switchable']].copy()\n"
    "display(matrix.style.set_properties(**{'text-align': 'left'}))"
)

md(
    "## 6. Export derived data for the frontend\n"
    "`sim_comparison.json` is consumed by the `SIM & Connectivity` page to render the "
    "traditional-vs-new comparison. The tagged catalog itself is written by "
    "`scripts/generate_research_outputs.py` from the same canonical module."
)
code(
    "comp_records = json.loads(comp.where(pd.notnull(comp), None).to_json(orient='records'))\n"
    "payload = {\n"
    "    'baseline_note_en': 'Power index is relative to a removable SIM (=100). BOM index is relative SIM-related bill-of-materials cost.',\n"
    "    'baseline_note_zh': '功耗指數以可插拔 SIM 為基準（=100）。BOM 指數為 SIM 相關物料成本的相對值。',\n"
    "    'rows': comp_records,\n"
    "}\n"
    "out = FRONTEND_DATA / 'sim_comparison.json'\n"
    "out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\\n')\n"
    "comp.to_csv(PROCESSED / 'sim_comparison.csv', index=False)\n"
    "print(f'Wrote {out} ({len(comp_records)} rows) and data/processed/sim_comparison.csv')"
)

md(
    "## 7. Findings\n"
    "\n"
    "**EN.** Cellular identity is de-hardwaring fast: eSIM removed the card slot, **iSIM** folds "
    "the SIM into the SoC (<1 mm², up to 70% less power, TEE-backed), and **SoftSIM** removes the "
    "hardware entirely (zero SIM BOM, cloud-managed). The unlock is the **GSMA SGP.32/41/42** "
    "specs, which replace SMS-based provisioning with SMS-free eIM Remote SIM Provisioning — the "
    "key to fleet-scale operator switching. Compared with traditional methods, the new stack trades "
    "physical wiring / manual card swaps for **remote, software-defined provisioning**, and adds "
    "**NTN** (satellite reachability for off-grid PBX sites) and **5G-Advanced** network slicing "
    "(per-tenant voice QoS SLAs). For SIM-bearer PBX / UCaaS / IoT voice endpoints this means "
    "smaller, lower-power, remotely re-homeable devices and a non-PSTN command path for resilience.\n"
    "\n"
    "**繁中.** 行動身分正快速去硬體化：eSIM 取消卡槽，**iSIM** 將 SIM 收進 SoC（<1 mm²、最高省 70% "
    "功耗、TEE 保護），**SoftSIM** 則完全移除硬體（零 SIM BOM、雲端管理）。關鍵推力是 **GSMA "
    "SGP.32/41/42**，以免 SMS 的 eIM 遠端配置取代舊式 SMS 流程，成為機隊規模切換營運商的鑰匙。相較傳統"
    "方式，新堆疊以**遠端、軟體定義的配置**取代實體佈線與手動換卡，並加入 **NTN**（離網 PBX 站點的衛星"
    "可達性）與 **5G-Advanced** 網路切片（租戶級語音 QoS SLA）。對 SIM 承載的 PBX / UCaaS / IoT 語音"
    "端點而言，代表更小、更省電、可遠端重新歸屬的裝置，以及具韌性的非 PSTN 控制路徑。"
)

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}
nbf.write(nb, OUT)
print(f"Wrote {OUT}")
