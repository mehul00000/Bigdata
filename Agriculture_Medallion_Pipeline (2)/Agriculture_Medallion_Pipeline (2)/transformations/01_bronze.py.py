
# ============================================================
# AGRICULTURE MEDALLION PIPELINE
# BRONZE LAYER - STREAMING TABLE INGESTION
# ============================================================

from pyspark import pipelines as dp
from pyspark.sql import functions as F

RAW = "mandi_analysis.mandi_raw"

PARQUET_SOURCE = f"{RAW}.parquet_data"
RAINFALL_SOURCE = f"{RAW}.csv_rainfall_daily"
PRICE_SOURCE = f"{RAW}.mandi_price"


# ------------------------------------------------------------
# 1. BRONZE MANDI DAILY
# ------------------------------------------------------------

@dp.table(name="bronze_mandi_daily")
def bronze_mandi_daily():

    df = spark.readStream.table(PARQUET_SOURCE)

    return (
        df.withColumn(
            "_bronze_source",
            F.lit(PARQUET_SOURCE)
        )
        .withColumn(
            "_bronze_loaded_at",
            F.current_timestamp()
        )
    )


# ------------------------------------------------------------
# 2. BRONZE RAINFALL DAILY
# ------------------------------------------------------------

@dp.table(name="bronze_rainfall_daily")
def bronze_rainfall_daily():

    df = spark.readStream.table(RAINFALL_SOURCE)

    return (
        df.withColumn(
            "_bronze_source",
            F.lit(RAINFALL_SOURCE)
        )
        .withColumn(
            "_bronze_loaded_at",
            F.current_timestamp()
        )
    )


# ------------------------------------------------------------
# 3. BRONZE MANDI PRICES
# ------------------------------------------------------------

@dp.table(name="bronze_mandi_prices")
def bronze_mandi_prices():

    df = spark.readStream.table(PRICE_SOURCE)

    return (
        df.withColumn(
            "_bronze_source",
            F.lit(PRICE_SOURCE)
        )
        .withColumn(
            "_bronze_loaded_at",
            F.current_timestamp()
        )
    )
