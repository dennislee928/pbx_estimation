"""Builder for notebooks/10_financial_hypothesis.ipynb (run from repo root)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

md(r"""# 10 — Financial Hypothesis Test: Replacing Physical PBX / 財務假設檢定：汰換實體 PBX

**EN.** This notebook applies **null-hypothesis significance testing** (per the framework at
[yongxi-stat.com/hypothesis-stat](https://www.yongxi-stat.com/hypothesis-stat/)) to a single
business question:

> *Is replacing a physical (on-premise / TDM) PBX with a modern alternative (cloud / IP-PBX)
> financially reasonable — in **Taiwan** and **worldwide**, over **3-, 5- and 10-year** horizons?*

We answer it with an explicit **Total-Cost-of-Ownership (TCO)** model built from *real* market
prices (sourced below), not ordinal guesses. Cost uncertainty is propagated by **Monte-Carlo
sampling** over the published price *ranges*, which gives each market/horizon a proper sample on
which to run a **one-sided t-test**.

**繁中.** 本筆記本採用**虛無假設顯著性檢定**（依
[yongxi-stat.com/hypothesis-stat](https://www.yongxi-stat.com/hypothesis-stat/) 的框架），
回答單一商業問題：

> *將實體（地端 / TDM）PBX 汰換為現代替代方案（雲端 / IP-PBX），在**台灣**與**全球**、
> **3 年、5 年、10 年**期間內，是否具財務合理性？*

我們以明確的**總持有成本（TCO）**模型作答，所用價格為下方標註之*真實*市場行情，而非
順序性的主觀猜測。成本不確定性以**蒙地卡羅抽樣**在公開價格*區間*上傳播，使每個
市場／期間皆有適當樣本可進行**單尾 t 檢定**。

---

### Consistency with other notebooks / 與其他筆記本的一致性
**EN.** No logic conflict with notebooks 01–09. This notebook **reuses** the decline trajectory in
`data/processed/longhorizon_projection.csv` and the **same decline-based "market death" definition
adopted in notebook 08** (penetration falling toward each market's historical floor). That decline
is the *only* driver of the migration/stranding-risk term — we do **not** introduce a competing
death metric. We add a new, purely financial layer on top of the existing adoption story.

**繁中.** 與筆記本 01–09 無邏輯衝突。本筆記本**重用** `longhorizon_projection.csv` 的衰退軌跡，
並沿用**筆記本 08 所採之「以衰退為基礎的市場消亡定義」**（滲透率朝各市場歷史低點下滑）。
該衰退是遷移／擱淺風險項的*唯一*來源——我們**不**引入相互矛盾的消亡指標，
僅在既有採用敘事之上，疊加一層全新的純財務分析。""")

md(r"""## 1. Hypothesis design / 假設設計

**EN.** For each market group (Taiwan; Worldwide) and horizon (3 / 5 / 10 years) we test, per seat:

- **H₀ (null):** replacing is **not** financially reasonable — mean NPV(TCO_physical − TCO_alternative) **≤ 0**.
- **H₁ (alternative):** replacing **is** financially reasonable — mean Δ **> 0** (the kept physical PBX is *more* expensive).
- **Test:** one-sample, **one-sided t-test** on the Monte-Carlo sample of per-seat NPV differences.
- **Decision rule:** reject H₀ at **α = 0.05**. We also report **Cohen's d** (effect size) and the **95% CI**.

**繁中.** 對每個市場群（台灣；全球）與期間（3 / 5 / 10 年），以每席位為單位檢定：

- **H₀（虛無）：** 汰換**不**具財務合理性——NPV(TCO_實體 − TCO_替代) 的平均值 **≤ 0**。
- **H₁（對立）：** 汰換**具**財務合理性——平均 Δ **> 0**（續用實體 PBX *較*昂貴）。
- **檢定方法：** 對每席位 NPV 差額的蒙地卡羅樣本，進行單樣本**單尾 t 檢定**。
- **判定準則：** 在 **α = 0.05** 下拒絕 H₀。另報告 **Cohen's d**（效果量）與 **95% 信賴區間**。""")

md(r"""## 2. Real cost anchors & the discount rate / 真實成本錨點與折現率

> **⚠️ DISCOUNT RATE — 折現率 = 3% (per user request) ⚠️**
>
> **EN.** Every multi-year cost below is discounted to present value at a **3% annual real discount
> rate**. This is the single most important time-value assumption in the model: a **higher** rate
> would shrink the future subscription stream and *favour keeping* the physical box, while a
> **lower** rate would *favour replacement* even more strongly. 3% is a conservative real
> (inflation-adjusted) cost-of-capital appropriate for a low-risk infrastructure decision. A
> sensitivity sweep over 0%–8% is included in §6 so the conclusion does **not** hinge on this number.
>
> **繁中.** 下方所有跨年度成本，皆以 **3% 年實質折現率**折現為現值。這是模型中最關鍵的
> 時間價值假設：折現率**愈高**，未來訂閱費用流的現值愈小，*愈有利於續用*實體設備；
> 折現率**愈低**，則*愈有利於汰換*。3% 為適用於低風險基礎設施決策的保守實質
> （經通膨調整）資金成本。§6 提供 0%–8% 的敏感度分析，確保結論**不**取決於此單一數字。

**Sourced price ranges (USD, per seat) — used as Monte-Carlo bounds / 來源價格區間（美元，每席位）：**

| Component / 項目 | Range / 區間 | Source / 來源 |
|---|---|---|
| Physical PBX upfront capex (hardware + licensing + install) | **\$500 – \$1,000 / seat** | PBX.IM 2026; JustCall 2026 |
| Physical PBX annual maintenance + line rental | **15% – 20% of capex / yr** | VitalPBX 2025 on-prem breakdown |
| Cloud / IP-PBX subscription | **\$15 – \$35 / seat / month** | CloudTalk 2026; Avoxi 2025 |
| Reported cloud TCO advantage over 5 yr | **30% – 40%** (cross-check) | bluIP 2026; Phone.com 2025 |

**EN.** Cloud subscription pricing is effectively global (the same SaaS providers serve TW and the
world; Taiwan's Chunghwa Telecom 雲端總機 falls inside the \$15–35 band). Markets are therefore
**differentiated by their decline speed** (stranding risk), not by re-quoting list prices.

**繁中.** 雲端訂閱定價實質上為全球一致（相同 SaaS 供應商同時服務台灣與全球；台灣中華電信
雲端總機亦落在 \$15–35 區間）。因此各市場以其**衰退速度**（擱淺風險）區分，而非重新報價。""")

code(r"""# Run from the repository root (same convention as notebooks 03/04/08).
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
import matplotlib.pyplot as plt

RNG = np.random.default_rng(20260612)   # reproducible
PROC = Path("data/processed")
assert PROC.exists(), "Run this notebook from the repository root (data/processed must be visible)."

# ---- Real, sourced cost anchors (Monte-Carlo bounds) ---------------------------------
CAPEX_LO, CAPEX_HI       = 500.0, 1000.0      # USD/seat, physical PBX upfront
MAINT_LO, MAINT_HI       = 0.15, 0.20         # fraction of capex / yr (physical)
CLOUD_MO_LO, CLOUD_MO_HI = 15.0, 35.0         # USD/seat/month, alternative subscription
DISCOUNT_RATE            = 0.03               # <<< 3% per user request — see markdown above
N_SIM                    = 20_000             # Monte-Carlo draws per market

HORIZONS = [3, 5, 10]                          # years
print(f"Discount rate fixed at {DISCOUNT_RATE:.0%}.  Monte-Carlo draws per market: {N_SIM:,}")""")

code(r"""# Load the SAME long-horizon decline trajectory used downstream of notebook 08.
proj = pd.read_csv(PROC / "longhorizon_projection.csv").set_index("market")
proj.columns = proj.columns.astype(int)
display(proj)

# Decline-based stranding factor (reuses 08's decline definition — NOT a new death metric):
# how much of a market's CURRENT (2027) fixed-line penetration survives to the horizon year.
# Faster decline -> physical PBX is stranded sooner -> higher migration/write-off risk.
BASE_YEAR = 2027
def survival_ratio(market, horizon):
    'Fraction of 2027 penetration still present horizon years out (clipped to [0,1]).'
    target = BASE_YEAR + horizon
    cols = proj.columns
    near = min(cols, key=lambda c: abs(c - target))     # nearest projected year
    return float(np.clip(proj.loc[market, near] / proj.loc[market, BASE_YEAR], 0, 1))

MARKETS = list(proj.index)            # TW, JP, KR, CN, IN, DE, GB, SE, US
print("Markets:", MARKETS)
for h in HORIZONS:
    print(f"  TW survival ratio @ {h}y:", round(survival_ratio("TW", h), 3))""")

code(r"""def npv(annual_cashflows, rate=DISCOUNT_RATE):
    'Present value of a list/array of year-1..year-N cash flows at rate.'
    years = np.arange(1, len(annual_cashflows) + 1)
    return np.sum(np.asarray(annual_cashflows) / (1 + rate) ** years, axis=0)

def tco_delta_samples(market, horizon, n=N_SIM, rate=DISCOUNT_RATE):
    'Monte-Carlo sample of per-seat NPV(TCO_physical - TCO_alternative); positive => replacement justified.'
    capex   = RNG.uniform(CAPEX_LO, CAPEX_HI, n)          # sunk if kept; avoided if replaced
    maint_r = RNG.uniform(MAINT_LO, MAINT_HI, n)          # physical annual maintenance fraction
    cloud_mo = RNG.uniform(CLOUD_MO_LO, CLOUD_MO_HI, n)   # alternative monthly subscription

    surv = survival_ratio(market, horizon)               # 0..1 ; lower => steeper decline
    strand = (1.0 - surv)                                 # stranded fraction of the asset

    pv_phys  = np.empty(n)
    pv_alt   = np.empty(n)
    for i in range(n):
        # PHYSICAL (keep): pay maintenance every year; a stranding write-off (re-spend the
        # residual capex on emergency migration) lands at the horizon as the market collapses.
        maint_stream = [capex[i] * maint_r[i]] * horizon
        write_off = capex[i] * strand                    # forced migration cost at end of horizon
        maint_stream[-1] += write_off
        pv_phys[i] = npv(maint_stream, rate)

        # ALTERNATIVE (replace): pay the subscription every year; no on-prem capex, no stranding.
        sub_stream = [cloud_mo[i] * 12] * horizon
        pv_alt[i] = npv(sub_stream, rate)

    return pv_phys - pv_alt

# quick smoke check
d = tco_delta_samples("TW", 5)
print(f"TW @5y  mean Δ = {d.mean():,.0f} USD/seat   (positive => replace)")""")

code(r"""def run_test(samples):
    'One-sided one-sample t-test of H0: mean<=0 vs H1: mean>0, with Cohen d and 95% CI.'
    t, p_two = stats.ttest_1samp(samples, 0.0)
    p_one = p_two / 2 if t > 0 else 1 - p_two / 2       # one-sided (H1: mean>0)
    d = samples.mean() / samples.std(ddof=1)           # Cohen's d
    se = samples.std(ddof=1) / np.sqrt(len(samples))
    ci = (samples.mean() - 1.96 * se, samples.mean() + 1.96 * se)
    return dict(mean_delta=samples.mean(), t=t, p_value=p_one, cohens_d=d,
                ci_low=ci[0], ci_high=ci[1], n=len(samples))

rows = []
for h in HORIZONS:
    # --- Taiwan: TW market only -------------------------------------------------------
    tw = tco_delta_samples("TW", h)
    rows.append({"scope": "Taiwan", "horizon_years": h, **run_test(tw)})
    # --- Worldwide: pool all markets --------------------------------------------------
    world = np.concatenate([tco_delta_samples(m, h) for m in MARKETS])
    rows.append({"scope": "Worldwide", "horizon_years": h, **run_test(world)})

results = pd.DataFrame(rows)
results["reject_H0"] = results["p_value"] < 0.05
results["verdict"] = np.where(results["reject_H0"],
                              "Replace IS financially reasonable",
                              "Cannot reject H0 (not justified)")
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")
display(results[["scope","horizon_years","mean_delta","t","p_value","cohens_d",
                 "ci_low","ci_high","reject_H0","verdict"]])

out = PROC / "financial_hypothesis_results.csv"
results.to_csv(out, index=False)
print("saved ->", out)""")

code(r"""# Visual summary: mean per-seat NPV saving from replacing, with 95% CI, by scope & horizon.
fig, ax = plt.subplots(figsize=(9, 5))
colors = {"Taiwan": "#d1495b", "Worldwide": "#30638e"}
width = 0.35
x = np.arange(len(HORIZONS))
for i, scope in enumerate(["Taiwan", "Worldwide"]):
    sub = results[results.scope == scope].set_index("horizon_years").loc[HORIZONS]
    err = [sub.mean_delta - sub.ci_low, sub.ci_high - sub.mean_delta]
    ax.bar(x + (i - 0.5) * width, sub.mean_delta, width, yerr=err, capsize=4,
           color=colors[scope], label=scope, alpha=0.9)
ax.axhline(0, color="k", lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"{h}y" for h in HORIZONS])
ax.set_ylabel("Mean NPV(keep − replace)  USD/seat\n(>0 ⇒ replacement justified)")
ax.set_title("Financial case for replacing physical PBX (3% discount, real-price Monte-Carlo)\n"
             "汰換實體 PBX 的財務理據（3% 折現，真實價格蒙地卡羅）")
ax.legend(); fig.tight_layout()
fig.savefig(PROC / "financial_hypothesis.png", dpi=120)
plt.show()
print("saved ->", PROC / "financial_hypothesis.png")""")

md(r"""## 6. Sensitivity to the discount rate / 折現率敏感度

**EN.** Because the 3% rate is the model's key time-value lever, we re-run all tests across
**0%–8%** and confirm the sign/decision is stable. If H₀ is rejected across the whole sweep, the
conclusion does **not** depend on the exact 3% choice.

**繁中.** 由於 3% 折現率是模型的關鍵時間價值槓桿，我們在 **0%–8%** 範圍重跑所有檢定，
確認結論方向與判定穩定。若整段範圍皆拒絕 H₀，則結論**不**取決於 3% 的確切選擇。""")

code(r"""sweep = []
for rate in [0.0, 0.02, 0.03, 0.05, 0.08]:
    for h in HORIZONS:
        for scope, sample in [("Taiwan", tco_delta_samples("TW", h, rate=rate)),
                              ("Worldwide", np.concatenate(
                                  [tco_delta_samples(m, h, rate=rate) for m in MARKETS]))]:
            r = run_test(sample)
            sweep.append({"rate": rate, "scope": scope, "horizon_years": h,
                          "mean_delta": r["mean_delta"], "p_value": r["p_value"],
                          "reject_H0": r["p_value"] < 0.05})
sweep = pd.DataFrame(sweep)
display(sweep.pivot_table(index=["scope","horizon_years"], columns="rate",
                          values="reject_H0"))
print("If every cell is True, the replace decision is robust to the discount rate 0%–8%.")""")

md(r"""## 7. Interpretation / 結論詮釋

**EN.** Read the saved table `financial_hypothesis_results.csv`:
- **Reject H₀ (p < 0.05) ⇒** for that market/horizon, keeping a physical PBX is *significantly*
  more expensive in present-value terms than replacing it — **replacement is financially reasonable.**
- **Fail to reject ⇒** the data do not support a financial case at that horizon (typically the
  shortest horizons, where avoided capex has less time to pay back the subscription stream).
- **Cohen's d** gauges *how* decisive the gap is; the **95% CI** shows the plausible per-seat saving.

This financial layer is **consistent with**, and downstream of, the adoption/decline story in
notebooks 03–08: the faster a market's fixed-line base declines, the larger the stranding term and
the stronger the financial case — exactly the ordering those notebooks already established.

**繁中.** 解讀已儲存的 `financial_hypothesis_results.csv`：
- **拒絕 H₀（p < 0.05）⇒** 對該市場／期間而言，續用實體 PBX 之現值成本*顯著*高於汰換——
  **汰換具財務合理性。**
- **無法拒絕 ⇒** 資料在該期間不支持財務理據（通常為最短期間，因避免之資本支出尚無
  足夠時間回收訂閱費用流）。
- **Cohen's d** 衡量差距的決定性程度；**95% 信賴區間**顯示每席位可能的節省金額。

此財務層與筆記本 03–08 的採用／衰退敘事**一致**且為其下游：市場固網基礎衰退愈快，
擱淺項愈大、財務理據愈強——恰與該些筆記本既已確立的排序相符。""")

nb["cells"] = cells
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
               "language_info": {"name": "python"}}
nbf.write(nb, "notebooks/10_financial_hypothesis.ipynb")
print("wrote notebooks/10_financial_hypothesis.ipynb with", len(cells), "cells")
