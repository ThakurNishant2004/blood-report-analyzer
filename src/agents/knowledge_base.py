"""Built-in knowledge base: reference ranges + value extraction from report text.

This gives the Analysis Agent grounded, deterministic pre-screening that is
passed to the LLM and also used as an offline fallback when no API is reachable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class TestDef:
    key: str
    label: str
    alias: str                      # regex (matched on lower-cased line)
    unit: str
    ranges: Dict[str, Tuple[Optional[float], Optional[float]]]
    low_msg: str
    high_msg: str
    exclude: Optional[str] = None   # regex: skip the line if it matches
    autoscale: Optional[Tuple[float, float]] = None  # (threshold, factor)


def _all(lo, hi):
    return {"ALL": (lo, hi)}


TESTS: List[TestDef] = [
    TestDef("hb", "Hemoglobin", r"\b(?:haemoglobin|hemoglobin|hgb|hb)\b", "g/dL",
            {"M": (13.0, 17.0), "F": (12.0, 15.0)},
            "Low hemoglobin can point to anaemia (iron, B12 or folate deficiency, blood loss).",
            "High hemoglobin can occur with dehydration, smoking or living at high altitude.",
            exclude=r"a1c|glyc"),
    TestDef("rbc", "RBC Count", r"\b(?:rbc|red\s+blood\s+cells?)", "million/uL",
            {"M": (4.5, 5.9), "F": (4.1, 5.1)},
            "Low red cell count is usually seen together with anaemia.",
            "High red cell count may relate to dehydration or other conditions."),
    TestDef("hct", "Hematocrit (PCV)", r"\b(?:hematocrit|haematocrit|pcv|hct)\b", "%",
            {"M": (40.0, 50.0), "F": (36.0, 46.0)},
            "Low hematocrit goes along with anaemia.",
            "High hematocrit can reflect dehydration."),
    TestDef("mcv", "MCV", r"\bmcv\b", "fL", _all(80.0, 100.0),
            "Small red cells (low MCV) often suggest iron deficiency.",
            "Large red cells (high MCV) can suggest B12/folate deficiency."),
    TestDef("wbc", "WBC Count", r"\b(?:wbc|total\s+leu[ck]ocyte\s+count|tlc|white\s+blood\s+cells?)",
            "/uL", _all(4000.0, 11000.0),
            "Low white cells can occur with some infections or medicines.",
            "High white cells commonly indicate infection or inflammation.",
            autoscale=(100.0, 1000.0)),
    TestDef("plt", "Platelets", r"\b(?:platelets?|plt)\b", "/uL", _all(150000.0, 450000.0),
            "Low platelets can increase bleeding tendency.",
            "High platelets can be reactive (infection, iron deficiency).",
            autoscale=(1000.0, 1000.0)),
    TestDef("glucose", "Fasting Glucose",
            r"(?:fasting\s+(?:blood\s+)?(?:glucose|sugar)|\bfbs\b|\bfbg\b|glucose,?\s*fasting)",
            "mg/dL", _all(70.0, 99.0),
            "Low sugar can cause weakness, sweating and dizziness.",
            "Raised fasting sugar suggests pre-diabetes (100-125) or diabetes (126+) range."),
    TestDef("hba1c", "HbA1c", r"hba1c|\ba1c\b|glyc(?:o)?(?:sylated|ated)\s+h(?:a)?emoglobin",
            "%", _all(4.0, 5.6),
            "Unusually low HbA1c may relate to anaemia or hypoglycaemia.",
            "HbA1c 5.7-6.4% is pre-diabetes range; 6.5% or more is diabetes range."),
    TestDef("tc", "Total Cholesterol", r"total\s+cholesterol|cholesterol\s*[-,:]?\s*total|^cholesterol\b",
            "mg/dL", _all(None, 200.0), "", "Raised total cholesterol increases heart-disease risk."),
    TestDef("ldl", "LDL Cholesterol", r"\bldl\b", "mg/dL", _all(None, 100.0), "",
            "High LDL ('bad') cholesterol is a major heart-disease risk factor."),
    TestDef("hdl", "HDL Cholesterol", r"(?<!non-)(?<!non )\bhdl\b", "mg/dL",
            {"M": (40.0, None), "F": (50.0, None)},
            "Low HDL ('good') cholesterol reduces protection against heart disease.", ""),
    TestDef("tg", "Triglycerides", r"triglycerides?|\btg\b", "mg/dL", _all(None, 150.0), "",
            "High triglycerides are linked to diet, weight, alcohol and sugar levels."),
    TestDef("creat", "Creatinine", r"creatinine", "mg/dL",
            {"M": (0.7, 1.3), "F": (0.6, 1.1)},
            "Low creatinine is usually not concerning (low muscle mass).",
            "High creatinine can indicate reduced kidney function or dehydration.",
            exclude=r"clearance|egfr"),
    TestDef("urea", "Blood Urea", r"\b(?:blood\s+)?urea\b(?!\s+nitrogen)", "mg/dL", _all(15.0, 45.0),
            "Low urea is rarely a concern.", "High urea can reflect dehydration or kidney issues.",
            exclude=r"nitrogen|bun"),
    TestDef("uric", "Uric Acid", r"uric\s+acid", "mg/dL",
            {"M": (3.5, 7.2), "F": (2.6, 6.0)},
            "Low uric acid is rarely a concern.", "High uric acid is linked to gout and kidney stones."),
    TestDef("alt", "ALT (SGPT)", r"\b(?:alt|sgpt)\b|alanine", "U/L", _all(7.0, 45.0),
            "", "Raised ALT suggests liver stress (fatty liver, alcohol, medicines, infection)."),
    TestDef("ast", "AST (SGOT)", r"\b(?:ast|sgot)\b|aspartate", "U/L", _all(8.0, 40.0),
            "", "Raised AST can come from liver or muscle injury."),
    TestDef("tsh", "TSH", r"\btsh\b|thyroid\s+stimulating", "uIU/mL", _all(0.4, 4.0),
            "Low TSH can suggest an overactive thyroid.",
            "High TSH can suggest an underactive thyroid."),
    TestDef("vitd", "Vitamin D (25-OH)", r"vitamin\s*d", "ng/mL", _all(30.0, 100.0),
            "Low vitamin D is very common and affects bones and immunity.",
            "Very high vitamin D is usually from over-supplementation."),
    TestDef("b12", "Vitamin B12", r"vitamin\s*b-?12|\bb12\b|cobalamin", "pg/mL", _all(200.0, 900.0),
            "Low B12 can cause anaemia, tingling and fatigue.", ""),
    TestDef("na", "Sodium", r"\bsodium\b", "mmol/L", _all(135.0, 145.0),
            "Low sodium can cause confusion and weakness.", "High sodium often reflects dehydration."),
    TestDef("k", "Potassium", r"\bpotassium\b", "mmol/L", _all(3.5, 5.1),
            "Low potassium can cause cramps and rhythm problems.",
            "High potassium needs prompt medical review."),
]

GROUP_TIPS = {
    "lipids": ("tc", "ldl", "hdl", "tg",
               "Reduce fried/processed food and sugary drinks, add oats, nuts and vegetables, "
               "and aim for 150 minutes of brisk activity per week."),
    "sugar": ("glucose", "hba1c",
              "Cut refined sugar and white-flour foods, prefer whole grains, walk after meals, "
              "and get a repeat sugar test as advised."),
    "blood": ("hb", "rbc", "hct", "mcv", "b12",
              "Include iron-, B12- and folate-rich foods (leafy greens, legumes, eggs, dairy) "
              "and ask your doctor about a deficiency work-up."),
    "vitamin D": ("vitd",
                  "Get safe morning sunlight and discuss supplementation with your doctor."),
    "liver": ("alt", "ast", "Limit alcohol and fatty foods, and maintain a healthy weight."),
}


def _norm_gender(gender: Optional[str]) -> Optional[str]:
    g = (gender or "").strip().lower()
    if g.startswith("m"):
        return "M"
    if g.startswith("f") or g.startswith("w"):
        return "F"
    return None


def get_range(t: TestDef, gender: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if "ALL" in t.ranges:
        return t.ranges["ALL"]
    g = _norm_gender(gender)
    if g in t.ranges:
        return t.ranges[g]
    los = [v[0] for v in t.ranges.values() if v[0] is not None]
    his = [v[1] for v in t.ranges.values() if v[1] is not None]
    return (min(los) if los else None, max(his) if his else None)


def _fmt(v: float) -> str:
    return f"{v:g}"


def _reference_text(lo, hi) -> str:
    if lo is not None and hi is not None:
        return f"{_fmt(lo)} - {_fmt(hi)}"
    if hi is not None:
        return f"< {_fmt(hi)}"
    if lo is not None:
        return f"> {_fmt(lo)}"
    return "-"


def extract_findings(text: str, gender: Optional[str] = None) -> List[dict]:
    """Find known tests in the report text and compare against reference ranges."""
    found: Dict[str, dict] = {}
    for raw in (text or "").splitlines():
        line = raw.strip().lower()
        if not line:
            continue
        line = re.sub(r"(?<=\d),(?=\d{3})", "", line)  # 7,200 -> 7200
        for t in TESTS:
            if t.key in found:
                continue
            if t.exclude and re.search(t.exclude, line):
                continue
            m = re.search(t.alias, line)
            if not m:
                continue
            rest = re.sub(r"\([^)]*\)", " ", line[m.end():])  # drop "(25-OH)" style text
            n = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)", rest)
            if not n:
                continue
            value = float(n.group(1))
            if t.key == "plt" and "lakh" in line:
                value *= 100000
            elif t.autoscale and value < t.autoscale[0]:
                value *= t.autoscale[1]

            lo, hi = get_range(t, gender)
            status = "Normal"
            if lo is not None and value < lo:
                status = "Low"
            elif hi is not None and value > hi:
                status = "High"
            note = t.low_msg if status == "Low" else t.high_msg if status == "High" else ""
            found[t.key] = {
                "key": t.key, "name": t.label, "value": value, "unit": t.unit,
                "reference": _reference_text(lo, hi), "status": status, "note": note,
            }
    return [found[t.key] for t in TESTS if t.key in found]


def abnormal(findings: List[dict]) -> List[dict]:
    return [f for f in findings if f["status"] != "Normal"]


def findings_to_markdown(findings: List[dict]) -> str:
    if not findings:
        return "(no known tests detected)"
    rows = ["| Test | Value | Reference | Status |", "|---|---|---|---|"]
    for f in findings:
        rows.append(f"| {f['name']} | {_fmt(f['value'])} {f['unit']} | {f['reference']} | {f['status']} |")
    return "\n".join(rows)


def rule_based_report(findings: List[dict], note: str = "") -> str:
    """Deterministic analysis used when the LLM is unavailable."""
    bad = abnormal(findings)
    out = []
    if note:
        out.append(f"> {note}\n")
    out.append("## 1. Summary")
    if not findings:
        out.append("No known blood-test values could be detected in this report text.")
    else:
        out.append(f"{len(findings)} known test values were detected; "
                   f"**{len(bad)}** fall outside the typical reference range.")
    out.append("\n## 2. Key Findings")
    if bad:
        for f in bad:
            out.append(f"- **{f['name']}: {_fmt(f['value'])} {f['unit']} ({f['status']})** "
                       f"- reference {f['reference']}. {f['note']}")
    else:
        out.append("- All detected values are within the typical range.")
    out.append("\n## 3. What It May Mean")
    out.append("Out-of-range values are not a diagnosis. They are signals to discuss with a doctor, "
               "who will consider your symptoms, history and repeat tests.")
    out.append("\n## 4. Lifestyle & Diet Suggestions")
    bad_keys = {f["key"] for f in bad}
    tips = []
    for group, spec in GROUP_TIPS.items():
        keys, tip = spec[:-1], spec[-1]
        if bad_keys.intersection(keys):
            tips.append(f"- **{group.title()}:** {tip}")
    out.extend(tips or ["- Keep a balanced diet, stay active, sleep well and stay hydrated."])
    out.append("\n## 5. Questions To Ask Your Doctor")
    out.append("- Which of these results need a repeat test or further investigation?")
    out.append("- Could any of my medicines or habits explain these values?")
    out.append("- What changes should I make before my next check-up?")
    out.append("\n## 6. Disclaimer")
    out.append("This is educational information only and not medical advice.")
    return "\n".join(out)
