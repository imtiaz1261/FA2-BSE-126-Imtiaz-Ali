import pandas as pd
from app.metrics import compare_binary_metric

def test_metric():
    df = pd.DataFrame({
        "variant": ["A"]*20 + ["B"]*20,
        "task_completed": [1]*10 + [0]*10 + [1]*16 + [0]*4
    })
    r = compare_binary_metric(df)
    assert r["a_rate"] == 0.5
    assert r["b_rate"] == 0.8
    assert 0 <= r["p_value"] <= 1
    assert r["ci_low"] < r["ci_high"]
