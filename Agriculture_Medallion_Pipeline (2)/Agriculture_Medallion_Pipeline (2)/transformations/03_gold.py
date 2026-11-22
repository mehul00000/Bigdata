
# ============================================================
# AGRICULTURE MEDALLION PIPELINE
# GOLD LAYER - ANALYTICS
# ============================================================

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window

SCHEMA = "mandi_analysis.mandi_raw"


# ------------------------------------------------------------
# 1. MARKET AND COMMODITY PRICE SUMMARY
# ------------------------------------------------------------

@dp.materialized_view(
    name="gold_market_commodity_price_summary"
)
def gold_market_commodity_price_summary():

    df = spark.read.table(
        f"{SCHEMA}.silver_mandi_prices"
    )

    required = [
        "state_name",
        "district_name",
        "market_name",
        "cmdt_name",
        "as_on"
    ]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"Missing column: {column}. "
                f"Available columns: {df.columns}"
            )

    return (
        df.groupBy(
            "state_name",
            "district_name",
            "market_name",
            "cmdt_name"
        )
        .agg(
            F.count("*").alias("total_records"),
            F.round(F.avg("as_on"), 2).alias("average_price"),
            F.min("as_on").alias("minimum_price"),
            F.max("as_on").alias("maximum_price")
        )
    )


# ------------------------------------------------------------
# 2. COMMODITY MSP ANALYSIS
# ------------------------------------------------------------

@dp.materialized_view(
    name="gold_commodity_msp_analysis"
)
def gold_commodity_msp_analysis():

    df = spark.read.table(
        f"{SCHEMA}.silver_mandi_prices"
    )

    required = [
        "cmdt_name",
        "as_on",
        "msp_price"
    ]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"Missing column: {column}. "
                f"Available columns: {df.columns}"
            )

    return (
        df.groupBy("cmdt_name")
        .agg(
            F.round(F.avg("as_on"), 2)
                .alias("average_market_price"),

            F.round(F.avg("msp_price"), 2)
                .alias("average_msp"),

            F.count("*")
                .alias("total_records")
        )
        .withColumn(
            "price_difference",
            F.round(
                F.col("average_market_price")
                - F.col("average_msp"),
                2
            )
        )
    )


# ------------------------------------------------------------
# 3. LATEST MARKET PRICES
# ------------------------------------------------------------

@dp.materialized_view(
    name="gold_latest_market_prices"
)
def gold_latest_market_prices():

    df = spark.read.table(
        f"{SCHEMA}.silver_mandi_prices"
    )

    keys = [
        "state_name",
        "district_name",
        "market_name",
        "cmdt_name"
    ]

    required = keys + ["reported_date"]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"Missing column: {column}. "
                f"Available columns: {df.columns}"
            )

    window_spec = (
        Window
        .partitionBy(*keys)
        .orderBy(
            F.col("reported_date").desc_nulls_last()
        )
    )

    return (
        df.withColumn(
            "row_number",
            F.row_number().over(window_spec)
        )
        .filter(F.col("row_number") == 1)
        .drop("row_number")
    )


# ------------------------------------------------------------
# 4. DISTRICT MONTHLY RAINFALL
# ------------------------------------------------------------

@dp.materialized_view(
    name="gold_district_monthly_rainfall"
)
def gold_district_monthly_rainfall():

    df = spark.read.table(
        f"{SCHEMA}.silver_rainfall_daily"
    )

    required = [
        "state",
        "district",
        "date"
    ]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"Missing column: {column}. "
                f"Available columns: {df.columns}"
            )

    aggregations = [
        F.count("*").alias("total_records")
    ]

    if "daily_actual" in df.columns:

        aggregations.append(
            F.round(F.sum("daily_actual"), 2)
            .alias("total_rainfall")
        )

        aggregations.append(
            F.round(F.avg("daily_actual"), 2)
            .alias("average_rainfall")
        )

    if "daily_normal" in df.columns:

        aggregations.append(
            F.round(F.avg("daily_normal"), 2)
            .alias("average_normal_rainfall")
        )

    return (
        df.withColumn("year", F.year("date"))
        .withColumn("month", F.month("date"))
        .groupBy(
            "state",
            "district",
            "year",
            "month"
        )
        .agg(*aggregations)
    )


# ------------------------------------------------------------
# 5. DAILY RAINFALL TREND
# ------------------------------------------------------------

@dp.materialized_view(
    name="gold_daily_rainfall_trend"
)
def gold_daily_rainfall_trend():

    df = spark.read.table(
        f"{SCHEMA}.silver_rainfall_daily"
    )

    selected_columns = [
        column for column in [
            "state",
            "district",
            "date",
            "daily_actual",
            "daily_normal",
            "daily_departure_per",
            "daily_category"
        ]
        if column in df.columns
    ]

    required = ["state", "district", "date"]

    for column in required:
        if column not in df.columns:
            raise ValueError(
                f"Missing column: {column}. "
                f"Available columns: {df.columns}"
            )

    return df.select(*selected_columns)
