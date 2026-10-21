"""Unapproved V1 draft: repair the analysis, not just its formatting."""
import pandas as pd
def analyze(folder):
    demo = pd.read_sas(folder / "DEMO_J.xpt", format="xport")
    bp = pd.read_sas(folder / "BPX_J.xpt", format="xport")
    data = demo.merge(bp, on="SEQN")
    data = data[data.RIDAGEYR >= 20]
    data["y"] = data[["BPXSY1", "BPXSY2", "BPXSY3", "BPXSY4"]].fillna(0).mean(axis=1)
    return (data.y * data.WTINT2YR).sum() / data.WTINT2YR.sum(), data.y.sem()
