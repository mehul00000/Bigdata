#!/usr/bin/env python3
"""Generate a complete Power BI Desktop project (.pbip) from the mandi/rainfall CSVs.

Outputs:
  MandiRainfallDashboard.pbip
  MandiRainfallDashboard.SemanticModel/  (TMDL model)
  MandiRainfallDashboard.Report/         (PBIR report)

Formats follow the official json-schemas (fabric/item/report/definition/*) and
field-validated rules (version.json 2.0.0, visualContainer 2.9.0, no selector:null,
UTF-8 no BOM, tabs in TMDL, formatString on every measure).
"""
import json
import os
import uuid

BASE = r"C:\Users\sharm\Downloads\powerbi"
OUT = os.path.join(BASE, "MandiRainfallDashboard")
SM = os.path.join(OUT, "MandiRainfallDashboard.SemanticModel")
REP = os.path.join(OUT, "MandiRainfallDashboard.Report")

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"
SCHEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
SCHEMA_VERSION = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"

_rng = uuid.UUID(int=20261121).int  # deterministic namespace


def guid() -> str:
    """Deterministic GUID."""
    global _rng
    _rng = (_rng * 6364136223846793005 + 1442695040888963407) % (1 << 128)
    h = f"{_rng:032x}"[:32]
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def hexid() -> str:
    return guid().replace("-", "")


# ---------------------------------------------------------------------------
# MODEL SPECIFICATION
# ---------------------------------------------------------------------------
# column spec: (name, m_type, summarize)  m_type: text|number|int|date
# summarize: none|sum

def csv_path(fn: str) -> str:
    """Quoted filename; combined with the shared SourceFolder parameter inside the M template."""
    return fn


def m_replace_null(cols):
    if not cols:
        return ""
    lst = ", ".join(f'"{c}"' for c in cols)
    return f"    ReplacedNulls = Table.ReplaceValue(RemovedBlank, \"null\", null, Replacer.ReplaceValue, {{{lst}}}),"


M_LATEST = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=21, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [state_name] <> null and [state_name] <> ""),
    ReplacedNulls = Table.ReplaceValue(RemovedBlank, "null", null, Replacer.ReplaceValue, {"one_yr_ago", "two_yr_ago", "three_yr_ago", "one_week_ago", "one_month_ago", "msp_price", "deviation_percent", "deviation_from_msp", "commodity_missing"}),
    ReplacedText = Table.ReplaceValue(ReplacedNulls, "null", "Unknown", Replacer.ReplaceValue, {"trend", "cmdt_name"}),
    ChangedType = Table.TransformColumnTypes(ReplacedText, {{"as_on", type number}, {"state_name", type text}, {"trend", type text}, {"cumm_arr", type number}, {"cmdt_name", type text}, {"msp_price", type number}, {"one_yr_ago", type number}, {"two_yr_ago", type number}, {"market_name", type text}, {"one_week_ago", type number}, {"three_yr_ago", type number}, {"cmdt_grp_name", type text}, {"district_name", type text}, {"last_five_day", type number}, {"one_month_ago", type number}, {"reported_date", type date}, {"deviation_percent", type number}, {"deviation_from_msp", type number}, {"commodity_missing", type text}, {"bronze_source", type text}, {"bronze_loaded_at", type text}}),
    RenamedColumns = Table.RenameColumns(ChangedType, {{"as_on", "Latest Price"}, {"trend", "Trend"}, {"cumm_arr", "Cumulative Arrivals"}, {"cmdt_name", "Commodity"}, {"msp_price", "MSP Price"}, {"one_yr_ago", "Price 1 Year Ago"}, {"state_name", "State"}, {"two_yr_ago", "Price 2 Years Ago"}, {"market_name", "Market"}, {"one_week_ago", "Price 1 Week Ago"}, {"three_yr_ago", "Price 3 Years Ago"}, {"cmdt_grp_name", "Commodity Group"}, {"district_name", "District"}, {"last_five_day", "Price 5 Days Ago"}, {"one_month_ago", "Price 1 Month Ago"}, {"reported_date", "Reported Date"}, {"deviation_percent", "Deviation %"}, {"deviation_from_msp", "Deviation from MSP"}, {"commodity_missing", "Commodity Missing"}, {"bronze_source", "Source"}, {"bronze_loaded_at", "Loaded At"}}),
    AddedKey = Table.AddColumn(RenamedColumns, "Price Key", each Text.Combine({Text.Lower([State]), "|", Text.Lower([District]), "|", Text.Lower([Market]), "|", Text.Lower([Commodity])}), type text)
in
    AddedKey""".replace("__CSV__", csv_path("Latest Market Prices.csv"))

M_MARKET = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [state_name] <> null and [state_name] <> ""),
    ReplacedNulls = Table.ReplaceValue(RemovedBlank, "null", "Unknown", Replacer.ReplaceValue, {"cmdt_name"}),
    ChangedType = Table.TransformColumnTypes(ReplacedNulls, {{"state_name", type text}, {"district_name", type text}, {"market_name", type text}, {"cmdt_name", type text}, {"total_records", Int64.Type}, {"average_price", type number}, {"minimum_price", type number}, {"maximum_price", type number}}),
    RenamedColumns = Table.RenameColumns(ChangedType, {{"state_name", "State"}, {"district_name", "District"}, {"market_name", "Market"}, {"cmdt_name", "Commodity"}, {"total_records", "Records"}, {"average_price", "Average Price"}, {"minimum_price", "Minimum Price"}, {"maximum_price", "Maximum Price"}}),
    AddedKey = Table.AddColumn(RenamedColumns, "Price Key", each Text.Combine({Text.Lower([State]), "|", Text.Lower([District]), "|", Text.Lower([Market]), "|", Text.Lower([Commodity])}), type text)
in
    AddedKey""".replace("__CSV__", csv_path("New_Query_2026_11_21_18_14_03.csv"))

M_MSP = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [cmdt_name] <> null and [cmdt_name] <> ""),
    ReplacedNulls = Table.ReplaceValue(RemovedBlank, "null", null, Replacer.ReplaceValue, {"average_msp", "price_difference"}),
    ReplacedCommodity = Table.ReplaceValue(ReplacedNulls, "null", "Unknown", Replacer.ReplaceValue, {"cmdt_name"}),
    ChangedType = Table.TransformColumnTypes(ReplacedCommodity, {{"cmdt_name", type text}, {"average_market_price", type number}, {"average_msp", type number}, {"total_records", Int64.Type}, {"price_difference", type number}}),
    RenamedColumns = Table.RenameColumns(ChangedType, {{"cmdt_name", "Commodity"}, {"average_market_price", "Avg Market Price"}, {"average_msp", "Average MSP"}, {"total_records", "Records"}, {"price_difference", "Price Difference"}})
in
    RenamedColumns""".replace("__CSV__", csv_path("Commodity MSP Analysis.csv"))

M_DIM_COMMODITY = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=21, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [cmdt_name] <> null and [cmdt_name] <> ""),
    ReplacedNulls = Table.ReplaceValue(RemovedBlank, "null", "Unknown", Replacer.ReplaceValue, {"cmdt_name"}),
    SelectedColumns = Table.SelectColumns(ReplacedNulls, {"cmdt_name", "cmdt_grp_name"}),
    RemovedDuplicates = Table.Distinct(SelectedColumns, {"cmdt_name"}),
    ChangedType = Table.TransformColumnTypes(RemovedDuplicates, {{"cmdt_name", type text}, {"cmdt_grp_name", type text}}),
    RenamedColumns = Table.RenameColumns(ChangedType, {{"cmdt_name", "Commodity"}, {"cmdt_grp_name", "Commodity Group"}})
in
    RenamedColumns""".replace("__CSV__", csv_path("Latest Market Prices.csv"))

M_DIM_DISTRICT = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [state] <> null and [state] <> ""),
    SelectedColumns = Table.SelectColumns(RemovedBlank, {"state", "district"}),
    RemovedDuplicates = Table.Distinct(SelectedColumns, {"state", "district"}),
    ChangedType = Table.TransformColumnTypes(RemovedDuplicates, {{"state", type text}, {"district", type text}}),
    AddedKey = Table.AddColumn(ChangedType, "District Key", each Text.Combine({Text.Lower([state]), "|", Text.Lower([district])}), type text),
    RenamedColumns = Table.RenameColumns(AddedKey, {{"state", "State"}, {"district", "District"}})
in
    RenamedColumns""".replace("__CSV__", csv_path("District Monthly Rainfall.csv"))

M_DAILY = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [state] <> null and [state] <> ""),
    ReplacedNulls = Table.ReplaceValue(RemovedBlank, "null", null, Replacer.ReplaceValue, {"daily_departure_per"}),
    ChangedType = Table.TransformColumnTypes(ReplacedNulls, {{"state", type text}, {"district", type text}, {"date", type date}, {"daily_actual", type number}, {"daily_normal", type number}, {"daily_departure_per", type number}, {"daily_category", type text}}),
    AddedCategoryName = Table.AddColumn(ChangedType, "Category Name", each if [daily_category] = "LD" then "Large Deficit" else if [daily_category] = "D" then "Deficit" else if [daily_category] = "N" then "Normal" else if [daily_category] = "E" then "Excess" else if [daily_category] = "LE" then "Large Excess" else if [daily_category] = "NR" then "No Rain" else "Not Defined", type text),
    AddedCategoryOrder = Table.AddColumn(AddedCategoryName, "Category Order", each if [daily_category] = "LD" then 1 else if [daily_category] = "D" then 2 else if [daily_category] = "N" then 3 else if [daily_category] = "E" then 4 else if [daily_category] = "LE" then 5 else 6, Int64.Type),
    AddedKey = Table.AddColumn(AddedCategoryOrder, "District Key", each Text.Combine({Text.Lower([state]), "|", Text.Lower([district])}), type text),
    RenamedColumns = Table.RenameColumns(AddedKey, {{"state", "State"}, {"district", "District"}, {"date", "Date"}, {"daily_actual", "Actual Rainfall"}, {"daily_normal", "Normal Rainfall"}, {"daily_departure_per", "Departure %"}, {"daily_category", "Category"}})
in
    RenamedColumns""".replace("__CSV__", csv_path("Daily Rainfall Trend.csv"))

M_MONTHLY = """let
    Source = Csv.Document(File.Contents(SourceFolder & "/" & "__CSV__"), [Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    RemovedBlank = Table.SelectRows(PromotedHeaders, each [state] <> null and [state] <> ""),
    ChangedType = Table.TransformColumnTypes(RemovedBlank, {{"state", type text}, {"district", type text}, {"year", Int64.Type}, {"month", Int64.Type}, {"total_records", Int64.Type}, {"total_rainfall", type number}, {"average_rainfall", type number}, {"average_normal_rainfall", type number}}),
    AddedMonthStart = Table.AddColumn(ChangedType, "Month Start", each #date([year], [month], 1), type date),
    AddedMonthName = Table.AddColumn(AddedMonthStart, "Month Name", each Date.MonthName([Month Start], "en-US"), type text),
    AddedNormalTotal = Table.AddColumn(AddedMonthName, "Normal Total", each [average_normal_rainfall] * [total_records], type number),
    AddedKey = Table.AddColumn(AddedNormalTotal, "District Key", each Text.Combine({Text.Lower([state]), "|", Text.Lower([district])}), type text),
    RenamedColumns = Table.RenameColumns(AddedKey, {{"state", "State"}, {"district", "District"}, {"year", "Year"}, {"month", "Month"}, {"total_records", "Records"}, {"total_rainfall", "Total Rainfall"}, {"average_rainfall", "Avg Daily Rainfall"}, {"average_normal_rainfall", "Avg Normal Daily Rainfall"}})
in
    RenamedColumns""".replace("__CSV__", csv_path("District Monthly Rainfall.csv"))


# measures: (name, dax, format, description)
TABLES = [
    {
        "name": "Market Prices",
        "csv": "New_Query_2026_11_21_18_14_03.csv",
        "m": M_MARKET,
        "m_outputs": ["State", "District", "Market", "Commodity", "Records", "Average Price", "Minimum Price", "Maximum Price", "Price Key"],
        "measures": [
            ("Mandi Records", "SUM('Market Prices'[Records])", "#,0", "Total number of price records captured across mandis"),
            ("Avg Market Price", "AVERAGE('Market Prices'[Average Price])", "\u20b9 #,0", "Average traded price across markets"),
            ("Min Market Price", "MIN('Market Prices'[Minimum Price])", "\u20b9 #,0", "Lowest minimum price across markets"),
            ("Max Market Price", "MAX('Market Prices'[Maximum Price])", "\u20b9 #,0", "Highest maximum price across markets"),
            ("Markets Count", "DISTINCTCOUNT('Market Prices'[Market])", "#,0", "Number of distinct mandi markets reporting"),
            ("Commodities Count", "DISTINCTCOUNT('Market Prices'[Commodity])", "#,0", "Number of distinct commodities traded"),
            ("States Count", "DISTINCTCOUNT('Market Prices'[State])", "#,0", "Number of states with reporting markets"),
        ],
        "columns": [
            ("State", "text", "none", False, None, None),
            ("District", "text", "none", False, None, None),
            ("Market", "text", "none", False, None, None),
            ("Commodity", "text", "none", False, None, None),
            ("Records", "int", "sum", False, None, None),
            ("Average Price", "number", "none", False, None, None),
            ("Minimum Price", "number", "none", False, None, None),
            ("Maximum Price", "number", "none", False, None, None),
            ("Price Key", "text", "none", True, None, None),
        ],
    },
    {
        "name": "Latest Prices",
        "csv": "Latest Market Prices.csv",
        "m": M_LATEST,
        "m_outputs": ["State", "District", "Market", "Commodity", "Commodity Group", "Latest Price", "Trend",
                      "Cumulative Arrivals", "MSP Price", "Price 5 Days Ago", "Price 1 Week Ago", "Price 1 Month Ago",
                      "Price 1 Year Ago", "Price 2 Years Ago", "Price 3 Years Ago", "Reported Date",
                      "Deviation %", "Deviation from MSP", "Commodity Missing", "Source", "Loaded At", "Price Key"],
        "measures": [
            ("Markets Reporting", "COUNTROWS('Latest Prices')", "#,0", "Number of market-commodity price rows reported"),
            ("Latest Avg Price", "AVERAGE('Latest Prices'[Latest Price])", "\u20b9 #,0", "Average of the latest reported prices"),
            ("Median Deviation %", "MEDIAN('Latest Prices'[Deviation %]) / 100", "+0.0%;-0.0%;0.0%", "Median deviation of market price from MSP in percent"),
            ("Median Deviation from MSP", "MEDIAN('Latest Prices'[Deviation from MSP])", "\u20b9 #,0", "Median deviation of market price from MSP in rupees"),
            ("Markets Above MSP", "CALCULATE(COUNTROWS('Latest Prices'), 'Latest Prices'[Deviation from MSP] > 0)", "#,0", "Markets trading above MSP"),
            ("Markets Below MSP", "CALCULATE(COUNTROWS('Latest Prices'), 'Latest Prices'[Deviation from MSP] < 0)", "#,0", "Markets trading below MSP"),
            ("% Above MSP", "DIVIDE([Markets Above MSP], [Markets Above MSP] + [Markets Below MSP])", "0.0%;-0.0%", "Share of markets trading above MSP"),
            ("Rising Markets", "CALCULATE(COUNTROWS('Latest Prices'), 'Latest Prices'[Trend] = \"up\")", "#,0", "Markets where price rose vs last week"),
            ("Falling Markets", "CALCULATE(COUNTROWS('Latest Prices'), 'Latest Prices'[Trend] = \"down\")", "#,0", "Markets where price fell vs last week"),
        ],
        "columns": [
            ("State", "text", "none", True, None, None),
            ("District", "text", "none", True, None, None),
            ("Market", "text", "none", True, None, None),
            ("Commodity", "text", "none", True, None, None),
            ("Commodity Group", "text", "none", False, None, None),
            ("Latest Price", "number", "none", False, None, None),
            ("Trend", "text", "none", False, None, None),
            ("Cumulative Arrivals", "number", "sum", False, None, None),
            ("MSP Price", "number", "none", False, None, None),
            ("Price 5 Days Ago", "number", "none", True, None, None),
            ("Price 1 Week Ago", "number", "none", True, None, None),
            ("Price 1 Month Ago", "number", "none", True, None, None),
            ("Price 1 Year Ago", "number", "none", True, None, None),
            ("Price 2 Years Ago", "number", "none", True, None, None),
            ("Price 3 Years Ago", "number", "none", True, None, None),
            ("Reported Date", "date", "none", False, None, None),
            ("Deviation %", "number", "none", False, None, None),
            ("Deviation from MSP", "number", "none", False, None, None),
            ("Commodity Missing", "text", "none", True, None, None),
            ("Source", "text", "none", True, None, None),
            ("Loaded At", "text", "none", True, None, None),
            ("Price Key", "text", "none", True, None, None),
        ],
    },
    {
        "name": "MSP Analysis",
        "csv": "Commodity MSP Analysis.csv",
        "m": M_MSP,
        "m_outputs": ["Commodity", "Avg Market Price", "Average MSP", "Records", "Price Difference"],
        "measures": [
            ("Commodities Tracked", "COUNTROWS('MSP Analysis')", "#,0", "Number of commodities compared against MSP"),
            ("Avg MSP", "AVERAGE('MSP Analysis'[Average MSP])", "\u20b9 #,0", "Average MSP across commodities"),
            ("Avg Commodity Market Price", "AVERAGE('MSP Analysis'[Avg Market Price])", "\u20b9 #,0", "Average market price per commodity"),
            ("Avg Price Gap vs MSP", "AVERAGE('MSP Analysis'[Price Difference])", "\u20b9 #,0", "Average gap between market price and MSP"),
            ("Commodities Above MSP", "CALCULATE(COUNTROWS('MSP Analysis'), 'MSP Analysis'[Price Difference] > 0)", "#,0", "Commodities trading above MSP on average"),
            ("Commodities Below MSP", "CALCULATE(COUNTROWS('MSP Analysis'), 'MSP Analysis'[Price Difference] < 0)", "#,0", "Commodities trading below MSP on average"),
        ],
        "columns": [
            ("Commodity", "text", "none", False, None, None),
            ("Avg Market Price", "number", "none", False, None, None),
            ("Average MSP", "number", "none", False, None, None),
            ("Records", "int", "sum", False, None, None),
            ("Price Difference", "number", "none", False, None, None),
        ],
    },
    {
        "name": "Dim Commodity",
        "csv": "Latest Market Prices.csv",
        "m": M_DIM_COMMODITY,
        "m_outputs": ["Commodity", "Commodity Group"],
        "measures": [],
        "columns": [
            ("Commodity", "text", "none", False, None, None),
            ("Commodity Group", "text", "none", False, None, None),
        ],
    },
    {
        "name": "Dim District",
        "csv": "District Monthly Rainfall.csv",
        "m": M_DIM_DISTRICT,
        "m_outputs": ["State", "District", "District Key"],
        "measures": [
            ("Districts Monitored", "DISTINCTCOUNT('Dim District'[District Key])", "#,0", "Number of districts covered by rainfall monitoring"),
        ],
        "columns": [
            ("State", "text", "none", False, None, "State"),
            ("District", "text", "none", False, None, None),
            ("District Key", "text", "none", True, None, None),
        ],
    },
    {
        "name": "Daily Rainfall",
        "csv": "Daily Rainfall Trend.csv",
        "m": M_DAILY,
        "m_outputs": ["State", "District", "Date", "Actual Rainfall", "Normal Rainfall", "Departure %",
                      "Category", "Category Name", "Category Order", "District Key"],
        "measures": [
            ("Days Count", "COUNTROWS('Daily Rainfall')", "#,0", "Number of district-day rainfall observations"),
            ("Total Actual Rainfall", "SUM('Daily Rainfall'[Actual Rainfall])", "#,0.0", "Sum of actual daily rainfall (mm)"),
            ("Total Normal Rainfall", "SUM('Daily Rainfall'[Normal Rainfall])", "#,0.0", "Sum of normal daily rainfall (mm)"),
            ("Rainfall Departure %", "DIVIDE([Total Actual Rainfall] - [Total Normal Rainfall], [Total Normal Rainfall])", "+0.0%;-0.0%;0.0%", "Overall rainfall departure from normal"),
            ("Deficit Days", "CALCULATE(COUNTROWS('Daily Rainfall'), 'Daily Rainfall'[Category] IN { \"LD\", \"D\" })", "#,0", "District-days in deficit or large deficit"),
            ("Excess Days", "CALCULATE(COUNTROWS('Daily Rainfall'), 'Daily Rainfall'[Category] IN { \"LE\", \"E\" })", "#,0", "District-days in excess or large excess"),
        ],
        "columns": [
            ("State", "text", "none", True, None, None),
            ("District", "text", "none", True, None, None),
            ("Date", "date", "none", False, None, None),
            ("Actual Rainfall", "number", "sum", False, None, None),
            ("Normal Rainfall", "number", "sum", False, None, None),
            ("Departure %", "number", "none", False, None, None),
            ("Category", "text", "none", True, None, None),
            ("Category Name", "text", "none", False, "Category Order", None),
            ("Category Order", "int", "none", True, None, None),
            ("District Key", "text", "none", True, None, None),
        ],
    },
    {
        "name": "Monthly Rainfall",
        "csv": "District Monthly Rainfall.csv",
        "m": M_MONTHLY,
        "m_outputs": ["State", "District", "Year", "Month", "Month Start", "Month Name", "Records",
                      "Total Rainfall", "Avg Daily Rainfall", "Avg Normal Daily Rainfall", "Normal Total", "District Key"],
        "measures": [
            ("Monthly Rainfall Total", "SUM('Monthly Rainfall'[Total Rainfall])", "#,0.0", "Total monthly rainfall across districts (mm)"),
            ("Monthly Normal Total", "SUM('Monthly Rainfall'[Normal Total])", "#,0.0", "Total normal monthly rainfall across districts (mm)"),
            ("Monthly Departure %", "DIVIDE([Monthly Rainfall Total] - [Monthly Normal Total], [Monthly Normal Total])", "+0.0%;-0.0%;0.0%", "Monthly rainfall departure from normal"),
        ],
        "columns": [
            ("State", "text", "none", True, None, None),
            ("District", "text", "none", True, None, None),
            ("Year", "int", "none", False, None, None),
            ("Month", "int", "none", True, None, None),
            ("Month Start", "date", "none", True, None, None),
            ("Month Name", "text", "none", False, "Month Start", None),
            ("Records", "int", "sum", False, None, None),
            ("Total Rainfall", "number", "sum", False, None, None),
            ("Avg Daily Rainfall", "number", "none", False, None, None),
            ("Avg Normal Daily Rainfall", "number", "none", True, None, None),
            ("Normal Total", "number", "sum", True, None, None),
            ("District Key", "text", "none", True, None, None),
        ],
    },
]

RELATIONSHIPS = [
    ("Market Prices to Dim Commodity", "Market Prices", "Commodity", "Dim Commodity", "Commodity"),
    ("MSP Analysis to Dim Commodity", "MSP Analysis", "Commodity", "Dim Commodity", "Commodity"),
    ("Latest Prices to Market Prices", "Latest Prices", "Price Key", "Market Prices", "Price Key"),
    ("Daily Rainfall to Dim District", "Daily Rainfall", "District Key", "Dim District", "District Key"),
    ("Monthly Rainfall to Dim District", "Monthly Rainfall", "District Key", "Dim District", "District Key"),
]

MODEL_REGISTRY = {}  # table -> {"columns": set, "measures": set}


# ---------------------------------------------------------------------------
# TMDL GENERATION
# ---------------------------------------------------------------------------
def tmdl_quote(name: str) -> str:
    if any(ch in name for ch in " .=':"):
        return "'" + name.replace("'", "''") + "'"
    return name


M_TYPE_DAX = {"text": "string", "number": "double", "int": "int64", "date": "dateTime"}
M_TYPE_M = {"text": "type text", "number": "type number", "int": "Int64.Type", "date": "type date"}


def tmdl_table(t: dict) -> str:
    name = t["name"]
    lines = [f"table {tmdl_quote(name)}", ""]
    for m in t["measures"]:
        mname, dax, fmt, desc = m[0], m[1], m[2], m[3]
        datacat = m[4] if len(m) > 4 else None
        if desc:
            lines.append(f"\t/// {desc}")
        if "\n" in dax:
            lines.append(f"\tmeasure {tmdl_quote(mname)} = ```")
            for dl in dax.split("\n"):
                lines.append("\t\t" + dl if dl.strip() else "")
            lines.append("\t\t```")
        else:
            lines.append(f"\tmeasure {tmdl_quote(mname)} = {dax}")
        if datacat:
            lines.append(f"\t\tdataCategory: {datacat}")
        lines.append(f"\t\tformatString: {fmt}")
        lines.append("")
    for cname, ctype, summarize, hidden, sortby, datacat in t["columns"]:
        lines.append(f"\tcolumn {tmdl_quote(cname)}")
        lines.append(f"\t\tdataType: {M_TYPE_DAX[ctype]}")
        if ctype == "date":
            lines.append("\t\tformatString: dd MMM yyyy")
        if datacat:
            lines.append(f"\t\tdataCategory: {datacat}")
        if hidden:
            lines.append("\t\tisHidden")
        if sortby:
            lines.append(f"\t\tsortByColumn: {tmdl_quote(sortby)}")
        lines.append(f"\t\tsummarizeBy: {summarize}")
        if t.get("partition_kind") == "calculated":
            lines.append(f"\t\tsourceColumn: [{cname}]")
        else:
            lines.append(f"\t\tsourceColumn: {tmdl_quote(cname)}")
        lines.append("")
    if t.get("partition_kind") == "calculated":
        lines.append(f"\tpartition {tmdl_quote(name)} = calculated")
        lines.append("\t\tmode: import")
        lines.append(f"\t\tsource = {t['m']}")
    else:
        lines.append(f"\tpartition {tmdl_quote(name)} = m")
        lines.append("\t\tmode: import")
        lines.append("\t\tsource =")
        for mline in t["m"].split("\n"):
            lines.append("\t\t\t" + mline if mline.strip() else "")
    lines.append("")
    return "\n".join(lines)


def tmdl_relationships() -> str:
    out = []
    for name, ft, fc, tt, tc in RELATIONSHIPS:
        out.append(f"relationship {tmdl_quote(name)}")
        out.append(f"\tfromColumn: {tmdl_quote(ft)}.{tmdl_quote_nodot(fc)}")
        out.append(f"\ttoColumn: {tmdl_quote(tt)}.{tmdl_quote_nodot(tc)}")
        out.append("")
    return "\n".join(out)


def tmdl_quote_nodot(name: str) -> str:
    # column name inside dotted reference: quote only if it contains chars needing it
    if any(ch in name for ch in " ='"):
        return "'" + name.replace("'", "''") + "'"
    return name


def write_utf8(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def write_json(path: str, obj) -> None:
    write_utf8(path, json.dumps(obj, indent=2, ensure_ascii=False))


def build_model() -> None:
    tables_dir = os.path.join(SM, "definition", "tables")
    # database.tmdl
    write_utf8(os.path.join(SM, "definition", "database.tmdl"),
               "database\n\tcompatibilityLevel: 1567\n")
    # model.tmdl
    lines = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US",
        "",
    ]
    lines += [f"ref table {tmdl_quote(t['name'])}" for t in TABLES]
    lines += ["", "annotation __PBI_TimeIntelligenceEnabled = 1", ""]
    write_utf8(os.path.join(SM, "definition", "model.tmdl"), "\n".join(lines))
    # relationships
    write_utf8(os.path.join(SM, "definition", "relationships.tmdl"), tmdl_relationships())
    # shared SourceFolder parameter - the ONE value a downloader must repoint to their CSV folder
    write_utf8(os.path.join(SM, "definition", "expressions.tmdl"),
               'expression SourceFolder = "C:/Users/sharm/Downloads/powerbi" '
               'meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n')
    # tables
    for t in TABLES:
        write_utf8(os.path.join(tables_dir, f"{t['name']}.tmdl"), tmdl_table(t))
        MODEL_REGISTRY[t["name"]] = {
            "columns": {c[0] for c in t["columns"]},
            "measures": {m[0] for m in t["measures"]},
        }
    # definition.pbism
    write_json(os.path.join(SM, "definition.pbism"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {"qnaEnabled": False},
    })




# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# PBIR GENERATION
# ---------------------------------------------------------------------------
def col_field(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas_field(entity, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def projection(field, entity, prop, active=False):
    p = {
        "field": field,
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }
    if active:
        p["active"] = True
    return p


def title_vco(text):
    if text is None:
        return {"title": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}]}
    return {"title": [{
        "properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": f"'{text}'"}}},
        }
    }]}


def literal(v):
    return {"expr": {"Literal": {"Value": v}}}


VISUALS_BY_PAGE = {}  # page guid -> list of visual dicts (checked at end)
CHECK_REGISTRY = []   # (entity, property) used in visuals


def topn_filter(entity, column, measure, top_n=10):
    """TopN visual filter: keep top N values of `column` ordered by `measure` descending."""
    alias = "v"
    return {
        "name": "Filter" + hexid()[:24],
        "field": col_field(entity, column),
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {
                    "Name": "subquery",
                    "Expression": {
                        "Subquery": {
                            "Query": {
                                "Version": 2,
                                "From": [{"Name": alias, "Entity": entity, "Type": 0}],
                                "Select": [
                                    {
                                        "Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": column},
                                        "Name": "field",
                                    }
                                ],
                                "OrderBy": [
                                    {
                                        "Direction": 2,
                                        "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": alias}}, "Property": measure}},
                                    }
                                ],
                                "Top": top_n,
                            }
                        }
                    },
                    "Type": 2,
                },
                {"Name": alias + "2", "Entity": entity, "Type": 0},
            ],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {"Column": {"Expression": {"SourceRef": {"Source": alias + "2"}}, "Property": column}}
                            ],
                            "Table": {"SourceRef": {"Source": "subquery"}},
                        }
                    }
                }
            ],
        },
        "howCreated": "User",
    }


def make_visual(visual_type, x, y, w, h, query_state, objects=None, vco=None, sort_definition=None, filter_config=None):
    v = {
        "$schema": SCHEMA_VISUAL,
        "name": hexid(),
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "visual": {"visualType": visual_type},
    }
    if query_state:
        # register fields for cross-check
        for role, ps in query_state.items():
            for p in ps.get("projections", []):
                fld = p["field"]
                for kind, spec in fld.items():
                    src = spec.get("Expression", {})
                    ent = src.get("SourceRef", {}).get("Entity")
                    prop = spec.get("Property")
                    CHECK_REGISTRY.append((ent, prop))
        q = {"queryState": query_state}
        if sort_definition:
            q["sortDefinition"] = sort_definition
        v["visual"]["query"] = q
    if objects:
        v["visual"]["objects"] = objects
    if vco:
        v["visual"]["visualContainerObjects"] = vco
    if filter_config:
        v["filterConfig"] = {"filters": filter_config}
    return v


def chart_cat(entity, col, active=True):
    return {"Category": {"projections": [projection(col_field(entity, col), entity, col, active)]}}


def chart_y(entity, props):
    # props: list of (kind, name) where kind is 'measure' or 'column'
    ps = []
    for kind, name in props:
        if kind == "measure":
            ps.append(projection(meas_field(entity, name), entity, name))
        else:
            ps.append(projection(col_field(entity, name), entity, name))
    return {"Y": {"projections": ps}}


def sort_by(entity, kind, name, direction="Descending"):
    fld = meas_field(entity, name) if kind == "measure" else col_field(entity, name)
    return {"sort": [{"field": fld, "direction": direction}], "isDefaultSort": False}


AXIS = {
    "categoryAxis": [{"properties": {"showAxisTitle": literal("false"), "show": literal("true")}}],
    "valueAxis": [{"properties": {"showAxisTitle": literal("false"), "show": literal("false")}}],
}

LABELS = {"labels": [{
    "properties": {
        "show": literal("true"),
        "labelPrecision": literal("0L"),
        "enableValueDataLabel": literal("true"),
        "labelDisplayUnits": literal("1D"),
    }
}]}

DONUT_LABELS = {"labels": [{
    "properties": {
        "show": literal("true"),
        "labelStyle": literal("'Data'"),
        "labelPrecision": literal("0L"),
        "labelDisplayUnits": literal("1D"),
    }
}]}

TABLE_HEADERS = {"columnHeaders": [{
    "properties": {
        "columnAdjustment": literal("'growToFit'"),
        "autoSizeColumnWidth": literal("true"),
    }
}]}


def card(entity, measure, x, y, w=236, h=112):
    """KPI card = the whole frame: cardVisual paints its own white surface, label and value."""
    qs = {"Data": {"projections": [projection(meas_field(entity, measure), entity, measure)]}}
    return make_visual("cardVisual", x, y, w, h, qs,
                       objects={
                           "value": [{"properties": {
                               "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#17202B'"}}}}},
                               "fontSize": {"expr": {"Literal": {"Value": "26D"}}},
                               "labelDisplayUnits": {"expr": {"Literal": {"Value": "1D"}}},
                               "labelPrecision": {"expr": {"Literal": {"Value": "0L"}}},
                           }, "selector": {"id": "default"}}],
                       })


def column_chart(title, entity, cat_col, y_props, x, y, w, h, sort=None, labels=True, y_entity=None):
    qs = chart_cat(entity, cat_col)
    qs.update(chart_y(y_entity or entity, y_props))
    objects = dict(AXIS)
    if labels:
        objects.update(LABELS)
    return make_visual("clusteredColumnChart", x, y, w, h, qs,
                       objects=objects, vco=title_vco(title),
                       sort_definition=sort)


def bar_chart(title, entity, cat_col, y_props, x, y, w, h, sort=None, y_entity=None, filter_config=None):
    qs = chart_cat(entity, cat_col)
    qs.update(chart_y(y_entity or entity, y_props))
    objects = dict(AXIS)
    objects.update(LABELS)
    return make_visual("clusteredBarChart", x, y, w, h, qs,
                       objects=objects, vco=title_vco(title),
                       sort_definition=sort, filter_config=filter_config)


def line_chart(title, entity, cat_col, y_props, x, y, w, h, y_entity=None):
    qs = chart_cat(entity, cat_col)
    qs.update(chart_y(y_entity or entity, y_props))
    objects = dict(AXIS)
    return make_visual("lineChart", x, y, w, h, qs, objects=objects, vco=title_vco(title))


def donut(title, entity, cat_col, y_props, x, y, w, h, y_entity=None):
    qs = chart_cat(entity, cat_col)
    qs.update(chart_y(y_entity or entity, y_props))
    return make_visual("donutChart", x, y, w, h, qs, objects=dict(DONUT_LABELS), vco=title_vco(title))


def table(title, projections_list, x, y, w, h):
    ps = []
    for entity, prop, kind in projections_list:
        fld = meas_field(entity, prop) if kind == "measure" else col_field(entity, prop)
        ps.append(projection(fld, entity, prop))
    qs = {"Values": {"projections": ps}}
    return make_visual("tableEx", x, y, w, h, qs, objects=dict(TABLE_HEADERS), vco=title_vco(title))


def slicer(entity, col, x, y, w=204, h=56):
    qs = {"Values": {"projections": [projection(col_field(entity, col), entity, col)]}}
    objects = {
        "data": [{"properties": {"mode": literal("'Dropdown'")}}],
        "header": [{"properties": {"show": literal("false")}}],
    }
    return make_visual("slicer", x, y, w, h, qs, objects=objects,
                       vco={"background": [{"properties": {"show": literal("false")}}],
                            "border": [{"properties": {"show": literal("false")}}],
                            "title": [{"properties": {"show": literal("false")}}]})


# ---------------------------------------------------------------------------
# PAGES
# ---------------------------------------------------------------------------
MP = "Market Prices"
LP = "Latest Prices"
MS = "MSP Analysis"
DC = "Dim Commodity"
DD = "Dim District"
DR = "Daily Rainfall"
MR = "Monthly Rainfall"


CANVASES = []  # (svg filename, svg content) collected by build_pages, written by build_report_root


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def canvas_svg(title, subtitle, kpi_frames, section_frames):
    """Page background: warm paper canvas, navy header band, KPI frames, white section frames."""
    p = []
    p.append("<svg width='1280' height='720' viewBox='0 0 1280 720' xmlns='http://www.w3.org/2000/svg'>")
    p.append("<rect width='1280' height='720' fill='#F2EFE6'/>")
    p.append("<rect width='1280' height='72' fill='#1B2A38'/>")
    p.append("<rect x='0' y='68' width='240' height='4' fill='#FDBF11'/>")
    p.append("<text x='28' y='32' font-family='Segoe UI Semibold' font-size='20' letter-spacing='1' fill='#FFFFFF'>" + esc(title) + "</text>")
    p.append("<text x='28' y='54' font-family='Segoe UI' font-size='11' fill='#A9B6C2'>" + esc(subtitle) + "</text>")
    for x, y, t in kpi_frames:
        p.append("<rect x='%d' y='%d' width='236' height='112' rx='10' fill='#FFFFFF' stroke='#E2DCCC' stroke-width='1'/>" % (x, y))
        p.append("<rect x='%d' y='%d' width='5' height='112' fill='#FDBF11'/>" % (x, y))
        p.append("<text x='%d' y='%d' font-family='Segoe UI' font-size='10' letter-spacing='1.2' fill='#5B6B7B'>" % (x + 18, y + 24) + esc(t) + "</text>")
    for x, y, w, h, t in section_frames:
        p.append("<rect x='%d' y='%d' width='%d' height='%d' rx='10' fill='#FFFFFF' stroke='#E2DCCC' stroke-width='1'/>" % (x, y, w, h))
        p.append("<text x='%d' y='%d' font-family='Segoe UI Semibold' font-size='12.5' fill='#17202B'>" % (x + 16, y + 26) + esc(t) + "</text>")
    p.append("<text x='1256' y='712' text-anchor='end' font-family='Segoe UI' font-size='9' fill='#9AA08F'>DATA: AGMARKNET + IMD | BUILT 21 NOV 2026</text>")
    p.append("</svg>")
    return "".join(p)


def build_pages():
    pages = []
    page_order = []
    pages_json = {"$schema": SCHEMA_PAGES}

    def new_page(display, svg_name, svg):
        pid = hexid()
        page_order.append(pid)
        CANVASES.append((svg_name, svg))
        return pid

    # ---------------- Page 1: Overview ----------------
    p1 = new_page("Overview", "overview_bg.svg", canvas_svg(
        "MANDI MARKET INTELLIGENCE", "Prices - markets and commodity coverage across India",
        [],
        [(16, 214, 624, 240, "AVG MARKET PRICE BY COMMODITY"), (656, 214, 608, 240, "SHARE OF RECORDS BY GROUP"),
         (16, 466, 624, 238, "AVG MARKET PRICE BY STATE"), (656, 466, 608, 238, "COMMODITY PRICE SUMMARY")]))
    v = [
        card(MP, "States Count", 16, 88),
        card(MP, "Markets Count", 262, 88),
        card(MP, "Commodities Count", 508, 88),
        card(MP, "Mandi Records", 754, 88),
        card(MP, "Avg Market Price", 1000, 88),
        column_chart(None, MP, "Commodity", [("measure", "Avg Market Price")],
                     24, 246, 608, 200, sort=sort_by(MP, "measure", "Avg Market Price")),
        donut(None, DC, "Commodity Group", [("measure", "Mandi Records")],
              664, 246, 592, 200, y_entity=MP),
        bar_chart(None, MP, "State", [("measure", "Avg Market Price")],
                  24, 498, 608, 198, sort=sort_by(MP, "measure", "Avg Market Price")),
        table(None, [
            (DC, "Commodity", "column"),
            (MP, "Avg Market Price", "measure"),
            (MP, "Min Market Price", "measure"),
            (MP, "Max Market Price", "measure"),
            (LP, "Latest Avg Price", "measure"),
        ], 664, 498, 592, 198),
    ]
    pages.append((p1, "Overview", v))

    # ---------------- Page 2: Prices vs MSP ----------------
    p2 = new_page("Prices vs MSP", "mspbp_bg.svg", canvas_svg(
        "PRICE VS MSP ANALYSIS", "Where markets trade against government support prices",
        [],
        [(16, 214, 812, 240, "MARKET PRICE VS MSP BY COMMODITY"), (844, 214, 420, 240, "WEEK-ON-WEEK TREND"),
         (16, 466, 624, 238, "PRICE GAP VS MSP BY COMMODITY"), (656, 466, 608, 238, "MSP COMPARISON DETAIL")]))
    v = [
        card(MS, "Commodities Tracked", 16, 88),
        card(MS, "Avg MSP", 262, 88),
        card(LP, "% Above MSP", 508, 88),
        card(LP, "Median Deviation %", 754, 88),
        card(LP, "Median Deviation from MSP", 1000, 88),
        column_chart(None, MS, "Commodity",
                     [("measure", "Avg Commodity Market Price"), ("measure", "Avg MSP")],
                     24, 246, 796, 200),
        donut(None, LP, "Trend", [("measure", "Markets Reporting")], 852, 246, 404, 200),
        bar_chart(None, MS, "Commodity", [("measure", "Avg Price Gap vs MSP")],
                  24, 498, 608, 198, sort=sort_by(MS, "measure", "Avg Price Gap vs MSP")),
        table(None, [
            (DC, "Commodity Group", "column"),
            (MS, "Commodity", "column"),
            (MS, "Avg Market Price", "column"),
            (MS, "Average MSP", "column"),
            (MS, "Price Difference", "column"),
            (MS, "Records", "column"),
        ], 664, 498, 592, 198),
    ]
    pages.append((p2, "Prices vs MSP", v))

    # ---------------- Page 3: Market Explorer ----------------
    p3 = new_page("Market Explorer", "explorer_bg.svg", canvas_svg(
        "MARKET EXPLORER", "Every mandi, every commodity - slice and search",
        [],
        [(16, 88, 220, 96, "COMMODITY"), (16, 196, 220, 96, "COMMODITY GROUP"), (16, 304, 220, 96, "STATE"),
         (16, 412, 220, 292, "PRICE TREND"), (252, 88, 504, 296, "TOP 10 MARKETS BY AVG PRICE"),
         (772, 88, 492, 296, "MIN VS MAX PRICE BY COMMODITY"), (252, 396, 1012, 308, "ALL MARKET PRICES")]))
    v = [
        slicer(DC, "Commodity", 24, 120),
        slicer(DC, "Commodity Group", 24, 228),
        slicer(MP, "State", 24, 336),
        donut(None, LP, "Trend", [("measure", "Markets Reporting")], 24, 444, 204, 252),
        bar_chart(None, MP, "Market", [("measure", "Avg Market Price")],
                  260, 120, 488, 256, sort=sort_by(MP, "measure", "Avg Market Price"),
                  filter_config=[topn_filter(MP, "Market", "Avg Market Price", 10)]),
        column_chart(None, MP, "Commodity",
                     [("measure", "Min Market Price"), ("measure", "Max Market Price")],
                     780, 120, 476, 256, labels=False),
        table(None, [
            (MP, "State", "column"),
            (MP, "District", "column"),
            (MP, "Market", "column"),
            (MP, "Commodity", "column"),
            (MP, "Records", "column"),
            (MP, "Avg Market Price", "measure"),
            (MP, "Min Market Price", "measure"),
            (MP, "Max Market Price", "measure"),
            (LP, "Latest Avg Price", "measure"),
            (LP, "Median Deviation %", "measure"),
        ], 260, 428, 996, 268),
    ]
    pages.append((p3, "Market Explorer", v))

    # ---------------- Page 4: Rainfall ----------------
    p4 = new_page("Rainfall", "rainfall_bg.svg", canvas_svg(
        "RAINFALL MONITOR", "District-level rainfall against long-term normals",
        [],
        [(1000, 88, 264, 112, "FILTER BY STATE"),
         (16, 214, 812, 240, "DAILY RAINFALL - ACTUAL VS NORMAL"), (844, 214, 420, 240, "DISTRICT-DAYS BY CATEGORY"),
         (16, 466, 624, 238, "MONTHLY RAINFALL VS NORMAL"), (656, 466, 608, 238, "ACTUAL RAINFALL BY STATE")]))
    v = [
        card(DR, "Total Actual Rainfall", 16, 88),
        card(DR, "Total Normal Rainfall", 262, 88),
        card(DR, "Rainfall Departure %", 508, 88),
        card(DD, "Districts Monitored", 754, 88),
        slicer(DD, "State", 1008, 120, 248, 68),
        line_chart(None, DR, "Date",
                   [("measure", "Total Actual Rainfall"), ("measure", "Total Normal Rainfall")],
                   24, 246, 796, 200),
        donut(None, DR, "Category Name", [("measure", "Days Count")], 852, 246, 404, 200),
        column_chart(None, MR, "Month Name",
                     [("measure", "Monthly Rainfall Total"), ("measure", "Monthly Normal Total")],
                     24, 498, 608, 198, labels=True),
        bar_chart(None, DD, "State", [("measure", "Total Actual Rainfall")],
                  664, 498, 592, 198, y_entity=DR,
                  sort=sort_by(DR, "measure", "Total Actual Rainfall")),
    ]
    pages.append((p4, "Rainfall", v))

    # ---------------- write ----------------
    pages_dir = os.path.join(REP, "definition", "pages")
    for idx, (pid, display, visuals) in enumerate(pages):
        pdir = os.path.join(pages_dir, pid)
        page_json = {
            "$schema": SCHEMA_PAGE,
            "name": pid,
            "displayName": display,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
            "objects": {"background": [{
                "properties": {
                    "transparency": {"expr": {"Literal": {"Value": "0D"}}},
                    "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#F2EFE6'"}}}}},
                    "image": {"image": {
                        "name": {"expr": {"Literal": {"Value": "'%s'" % CANVASES[idx][0]}}},
                        "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources",
                                                                 "PackageType": 1,
                                                                 "ItemName": CANVASES[idx][0]}}},
                        "scaling": {"expr": {"Literal": {"Value": "'Fill'"}}},
                    }},
                }
            }]},
        }
        write_json(os.path.join(pdir, "page.json"), page_json)
        for vis in visuals:
            VISUALS_BY_PAGE.setdefault(pid, []).append(vis)
            vid = vis["name"]
            write_json(os.path.join(pdir, "visuals", vid, "visual.json"), vis)
    pages_json["pageOrder"] = page_order
    pages_json["activePageName"] = page_order[0]
    write_json(os.path.join(pages_dir, "pages.json"), pages_json)


THEME_JSON = {
    "name": "MandiPremiumV2.json",
    "dataColors": ["#E3120B", "#0098A6", "#FFD700", "#2C2C2C", "#8A8B8C", "#005F83", "#B51D60", "#FDBF11"],
    "background": "#FFFFFF",
    "foreground": "#2C2C2C",
    "tableAccent": "#0098A6",
    "textClasses": {
        "label": {"color": "#5B6B7B", "fontSize": 10, "fontFace": "Segoe UI"},
        "callout": {"color": "#17202B", "fontSize": 26, "fontFace": "Segoe UI Semibold", "fontWeight": "bold"},
        "title": {"color": "#17202B", "fontSize": 13, "fontFace": "Segoe UI Semibold", "fontWeight": "semibold"},
        "header": {"color": "#FFFFFF", "fontSize": 11, "fontFace": "Segoe UI Semibold", "fontWeight": "semibold"},
        "largeTitle": {"color": "#17202B", "fontSize": 16, "fontFace": "Segoe UI Semibold", "fontWeight": "bold"},
    },
    "visualStyles": {
        "page": {"*": {
            "background": [{"color": {"solid": {"color": "#F2EFE6"}}, "transparency": 0}],
            "outspace": [{"color": {"solid": {"color": "#E4DECF"}}}],
        }},
        "*": {"*": {
            "background": [{"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 100}],
            "visualHeader": [{"transparency": 100}],
        }},
        "tableEx": {"*": {
            "columnHeaders": [{"fontColor": {"solid": {"color": "#FFFFFF"}}, "backColor": {"solid": {"color": "#1B2A38"}}, "fontSize": 10}],
        }},
    },
}


def build_report_root():
    # theme (v2 filename to defeat Desktop's theme cache) + page canvas SVGs
    write_utf8(os.path.join(REP, "StaticResources", "RegisteredResources", "MandiPremiumV2.json"),
               json.dumps(THEME_JSON, indent=2, ensure_ascii=False))
    for svg_name, svg in CANVASES:
        write_utf8(os.path.join(REP, "StaticResources", "RegisteredResources", svg_name), svg)
    report = {
        "$schema": SCHEMA_REPORT,
        "themeCollection": {
            "baseTheme": {
                "name": "CY26SU02",
                "reportVersionAtImport": {"visual": "2.9.0", "report": "3.2.0", "page": "2.0.0"},
                "type": "SharedResources",
            },
            "customTheme": {
                "name": "MandiPremiumV2.json",
                "reportVersionAtImport": {"visual": "2.9.0", "report": "3.2.0", "page": "2.0.0"},
                "type": "RegisteredResources",
            },
        },
        "resourcePackages": [
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": (
                    [{"name": "MandiPremiumV2.json", "path": "MandiPremiumV2.json", "type": "CustomTheme"}]
                    + [{"name": name, "path": name, "type": "Image"} for name, _ in CANVASES]
                ),
            }
        ],
    }
    write_json(os.path.join(REP, "definition", "report.json"), report)
    write_json(os.path.join(REP, "definition", "version.json"), {
        "$schema": SCHEMA_VERSION,
        "version": "2.0.0",
    })
    write_json(os.path.join(REP, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../MandiRainfallDashboard.SemanticModel"}},
    })
    write_json(os.path.join(REP, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "MandiRainfallDashboard"},
        "config": {"version": "2.0", "logicalId": guid()},
    })
    write_json(os.path.join(SM, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "MandiRainfallDashboard"},
        "config": {"version": "2.0", "logicalId": guid()},
    })
    write_json(os.path.join(OUT, "MandiRainfallDashboard.pbip"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": "MandiRainfallDashboard.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })


# ---------------------------------------------------------------------------
# CROSS-CHECKS
# ---------------------------------------------------------------------------
def cross_checks() -> list:
    errors = []
    # visual fields must exist in model
    for ent, prop in CHECK_REGISTRY:
        reg = MODEL_REGISTRY.get(ent)
        if reg is None:
            errors.append(f"Unknown table in visual: {ent}")
            continue
        if prop not in reg["columns"] and prop not in reg["measures"]:
            errors.append(f"Unknown field in visual: {ent}.{prop}")
    # TMDL sourceColumns must match M outputs
    for t in TABLES:
        tmdl_cols = {c[0] for c in t["columns"]}
        if tmdl_cols != set(t["m_outputs"]):
            missing = tmdl_cols - set(t["m_outputs"])
            extra = set(t["m_outputs"]) - tmdl_cols
            errors.append(f"Table {t['name']}: TMDL/M mismatch missing={missing} extra={extra}")
    # relationships endpoints
    for name, ft, fc, tt, tc in RELATIONSHIPS:
        if fc not in MODEL_REGISTRY.get(ft, {}).get("columns", set()):
            errors.append(f"Relationship {name}: bad from column {ft}.{fc}")
        if tc not in MODEL_REGISTRY.get(tt, {}).get("columns", set()):
            errors.append(f"Relationship {name}: bad to column {tt}.{tc}")
        # one side must be unique-grain: simple sanity for known dims
    # measure name collisions
    all_m = {}
    for t in TABLES:
        for m in t["measures"]:
            if m[0] in all_m:
                errors.append(f"Duplicate measure name: {m[0]}")
            all_m[m[0]] = t["name"]
    # measure vs column collision in same table
    for t in TABLES:
        cols = {c[0] for c in t["columns"]}
        for m in t["measures"]:
            if m[0] in cols:
                errors.append(f"Measure/column collision in {t['name']}: {m[0]}")
    # sortByColumn targets exist
    for t in TABLES:
        cols = {c[0]: c for c in t["columns"]}
        for c in t["columns"]:
            if c[4] and c[4] not in cols:
                errors.append(f"sortByColumn target missing in {t['name']}: {c[3]} -> {c[4]}")
    return errors


def main() -> None:
    import shutil
    if os.path.isdir(OUT):
        shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)
    build_model()
    build_pages()
    build_report_root()
    errors = cross_checks()
    if errors:
        print("CROSS-CHECK ERRORS:")
        for e in errors:
            print("  -", e)
        raise SystemExit(1)
    # BOM check
    for root, _, files in os.walk(SM):
        for f in files:
            p = os.path.join(root, f)
            with open(p, "rb") as fh:
                if fh.read(3) == b"\xef\xbb\xbf":
                    raise SystemExit(f"BOM found: {p}")
    n_visuals = sum(len(v) for v in VISUALS_BY_PAGE.values())
    print(f"OK: model tables={len(TABLES)} relationships={len(RELATIONSHIPS)} "
          f"pages={len(VISUALS_BY_PAGE)} visuals={n_visuals}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
