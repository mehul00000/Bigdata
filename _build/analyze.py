import csv, os, sys, collections

BASE = r"C:\Users\sharm\Downloads\powerbi"
FILES = [
    "Commodity MSP Analysis.csv",
    "Daily Rainfall Trend.csv",
    "District Monthly Rainfall.csv",
    "Latest Market Prices.csv",
    "New_Query_2026_11_21_18_14_03.csv",
]

def is_int(v):
    try:
        int(v); return True
    except: return False

def is_float(v):
    try:
        float(v); return True
    except: return False

for fn in FILES:
    path = os.path.join(BASE, fn)
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            delim = dialect.delimiter
        except Exception:
            delim = ","
        f.seek(0)
        r = csv.reader(f, delimiter=delim)
        rows = list(r)
    hdr = rows[0]
    data = rows[1:]
    print(f"\n=== {fn} ===  delim='{delim}'  cols={len(hdr)}  rows={len(data)}")
    ncols = collections.Counter(len(x) for x in rows)
    print("row-length histogram:", dict(ncols))
    for i, col in enumerate(hdr):
        vals = [row[i] if i < len(row) else "" for row in data]
        nonnull = [v for v in vals if v.strip() != ""]
        nullpct = 100 * (len(vals) - len(nonnull)) / max(len(vals), 1)
        nums = [v for v in nonnull if is_float(v)]
        ints = [v for v in nonnull if is_int(v)]
        dates = [v for v in nonnull if len(v) == 10 and v[4] == "-" and is_int(v[:4])]
        t = "text"
        if len(nums) == len(nonnull) and nonnull:
            t = "int" if len(ints) == len(nonnull) else "double"
        elif dates and len(dates) == len(nonnull):
            t = "date"
        distinct = len(set(nonnull))
        info = ""
        if t == "text" and distinct <= 15:
            info = " vals=" + str(collections.Counter(nonnull).most_common(15))
        elif t == "double" or t == "int":
            fvals = [float(v) for v in nums]
            info = f" min={min(fvals):.2f} max={max(fvals):.2f}"
        elif t == "date":
            info = f" min={min(dates)} max={max(dates)}"
        print(f"  [{i:2}] {col!r}: {t} nulls={nullpct:.1f}% distinct={distinct}{info[:180]}")

# Key overlap between Latest Market Prices and New_Query
def load(fn):
    with open(os.path.join(BASE, fn), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

lp = load("Latest Market Prices.csv")
nq = load("New_Query_2026_11_21_18_14_03.csv")

def key_lp(x): return (x["state_name"].strip().lower(), x["district_name"].strip().lower(), x["market_name"].strip().lower(), x["cmdt_name"].strip().lower())
def key_nq(x): return (x["state_name"].strip().lower(), x["district_name"].strip().lower(), x["market_name"].strip().lower(), x["cmdt_name"].strip().lower())

klp = [key_lp(x) for x in lp]
knq = [key_nq(x) for x in nq]
print(f"\n=== KEY OVERLAP ===\nLatest keys: {len(klp)} rows, {len(set(klp))} unique\nNewQuery keys: {len(knq)} rows, {len(set(knq))} unique")
print("Latest in NewQuery:", len(set(klp) & set(knq)), "/", len(set(klp)))
print("NewQuery in Latest:", len(set(klp) & set(knq)), "/", len(set(knq)))

# commodity overlap with MSP table
msp = load("Commodity MSP Analysis.csv")
msp_names = {x["cmdt_name"].strip().lower() for x in msp}
lp_cmdt = {x["cmdt_name"].strip().lower() for x in lp}
print("\nMSP commodities:", len(msp_names), " Latest commodities:", len(lp_cmdt))
print("MSP ∩ Latest:", len(msp_names & lp_cmdt), " in Latest not MSP:", sorted(lp_cmdt - msp_names)[:20])

# rainfall district overlap
dr = load("Daily Rainfall Trend.csv")
dm = load("District Monthly Rainfall.csv")
kd = {(x["state"].strip().lower(), x["district"].strip().lower()) for x in dr}
km = {(x["state"].strip().lower(), x["district"].strip().lower()) for x in dm}
print(f"\n=== RAINFALL ===\nDaily districts: {len(kd)}  Monthly districts: {len(km)}  overlap: {len(kd & km)}")
print("Daily date range:", min(x["date"] for x in dr if x["date"]), "to", max(x["date"] for x in dr if x["date"]))
