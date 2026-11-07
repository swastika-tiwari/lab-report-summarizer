DIFF = ("neutrophil", "lymphocyte", "eosinophil", "monocyte", "basophil")


def differential_check(results):
    """The five differential percentages should add up to about 100."""
    picked = {}
    for r in results:
        n = r.name.lower()
        if "absolute" in n or r.value > 100:
            continue
        for key in DIFF:
            if key in n and key not in picked:
                picked[key] = r
    if not picked:
        return None
    total = sum(r.value for r in picked.values())
    missing = [k for k in DIFF if k not in picked]
    found = ", ".join(f"{k} {picked[k].value:g}" for k in picked)
    if not missing and abs(total - 100) > 3:
        return f"differential count sums to {total:g}, expected ~100 ({found}): check these values"
    if missing and total > 103:
        return f"differential count already sums to {total:g} (over 100): check these values ({found})"
    if missing and total + 10 * len(missing) < 95:
        return (f"differential count looks low: {total:g} from {len(picked)} of 5 rows "
                f"(missing: {', '.join(missing)}): check for misread or missing rows")
    return None