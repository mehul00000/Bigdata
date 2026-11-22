
# ============================================================
# 02_silver.py
# Databricks Lakeflow Medallion Pipeline - SILVER LAYER
# Catalog: mandi_analysis
# Schema : mandi_raw
# ============================================================

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql import types as T
import re

CURATED = "mandi_analysis.mandi_raw"


# ------------------------------------------------------------
# 1. HELPER FUNCTIONS
# ------------------------------------------------------------

def _standardize_columns(df):
    """Convert column names into lowercase snake_case."""
    new_names = []
    used = {}

    for old in df.columns:
        new = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            old.strip().lower()
        ).strip("_")

        if not new:
            new = "unnamed_column"

        count = used.get(new, 0)
        used[new] = count + 1

        if count:
            new = f"{new}_{count + 1}"

        new_names.append(new)

    return df.toDF(*new_names)


def _trim_strings(df):
    """Remove unnecessary spaces from string columns."""
    for field in df.schema.fields:
        if isinstance(field.dataType, T.StringType):
            df = df.withColumn(
                field.name,
                F.trim(F.col(field.name))
            )

    return df


def _parse_date(df, column, formats):
    """Convert string date columns into DATE format."""
    if column not in df.columns:
        return df

    raw = F.trim(F.col(column).cast("string"))

    candidates = [
        F.to_date(raw, fmt)
        for fmt in formats
    ]

    candidates.append(F.to_date(raw))

    return df.withColumn(
        column,
        F.coalesce(*candidates)
    )


def _cast_double(df, column, percent=False):
    """Convert numeric string columns into DOUBLE."""
    if column not in df.columns:
        return df

    value = F.trim(F.col(column).cast("string"))

    value = F.regexp_replace(value, ",", "")

    if percent:
        value = F.regexp_replace(value, "%", "")

    return df.withColumn(
        column,
        value.cast("double")
    )


def _remove_metadata_and_deduplicate(df):
    """
    Remove Google Drive metadata columns before deduplication.

    These metadata structures contain VARIANT fields.
    Spark does not support using those fields in
    dropDuplicates() operations.
    """

    metadata_columns = [
        "gdrive_metadata",
        "file_metadata",
        "_gdrive_metadata",
        "_file_metadata"
    ]

    existing_columns = [
        column
        for column in metadata_columns
        if column in df.columns
    ]

    if existing_columns:
        df = df.drop(*existing_columns)

    return df.dropDuplicates()


# ------------------------------------------------------------
# 2. SILVER - MANDI DAILY PARQUET
# ------------------------------------------------------------

@dp.materialized_view(
    name="silver_mandi_daily",
    comment="Cleaned and standardized daily mandi Parquet data."
)
def silver_mandi_daily():

    df = spark.read.table(
        f"{CURATED}.bronze_mandi_daily"
    )

    # Standardize column names
    df = _standardize_columns(df)

    # Trim string values
    df = _trim_strings(df)

    # Parse date columns
    date_columns = [
        "date",
        "arrival_date",
        "reported_date",
        "market_date",
        "price_date"
    ]

    for column in date_columns:
        df = _parse_date(
            df,
            column,
            [
                "yyyy-MM-dd",
                "dd-MM-yyyy",
                "dd/MM/yyyy"
            ]
        )

    # Remove metadata and duplicates
    df = _remove_metadata_and_deduplicate(df)

    return df


# ------------------------------------------------------------
# 3. SILVER - RAINFALL DAILY
# Source: csv_rainfall_daily_temp
# ------------------------------------------------------------

@dp.materialized_view(
    name="silver_rainfall_daily",
    comment="Cleaned and standardized IMD district-wise rainfall data."
)
def silver_rainfall_daily():

    df = spark.read.table(
        f"{CURATED}.bronze_rainfall_daily"
    )

    # Standardize column names
    df = _standardize_columns(df)

    # Trim string values
    df = _trim_strings(df)

    # Parse date columns
    date_columns = [
        "date",
        "cumulative_date",
        "monthly_date"
    ]

    for column in date_columns:
        df = _parse_date(
            df,
            column,
            [
                "yyyy-MM-dd",
                "dd-MM-yyyy",
                "dd/MM/yyyy"
            ]
        )

    # Convert rainfall measurements into DOUBLE
    numeric_columns = [
        "daily_actual",
        "daily_normal",
        "weekly_actual",
        "weekly_normal",
        "cumulative_actual",
        "cumulative_normal",
        "monthly_actual",
        "monthly_normal"
    ]

    for column in numeric_columns:
        df = _cast_double(df, column)

    # Convert departure percentages into DOUBLE
    percent_columns = [
        "daily_departure_per",
        "weekly_departure_per",
        "cumulative_departure_per",
        "monthly_departure_per"
    ]

    for column in percent_columns:
        df = _cast_double(
            df,
            column,
            percent=True
        )

    # Standardize state and district names
    for column in ["state", "district"]:
        if column in df.columns:
            df = df.withColumn(
                column,
                F.upper(F.trim(F.col(column)))
            )

    # Standardize rainfall categories
    category_columns = [
        "daily_category",
        "weekly_category",
        "cumulative_category",
        "monthly_category"
    ]

    for column in category_columns:
        if column in df.columns:
            df = df.withColumn(
                column,
                F.upper(F.trim(F.col(column)))
            )

    # Remove invalid records
    required_columns = {
        "state",
        "district",
        "date"
    }

    if required_columns.issubset(set(df.columns)):

        df = df.filter(
            F.col("state").isNotNull()
            & (F.col("state") != "")
            & F.col("district").isNotNull()
            & (F.col("district") != "")
            & F.col("date").isNotNull()
        )

    # IMPORTANT:
    # Remove metadata columns before dropDuplicates()
    df = _remove_metadata_and_deduplicate(df)

    return df


# ------------------------------------------------------------
# 4. SILVER - MANDI MARKET PRICES
# ------------------------------------------------------------

@dp.materialized_view(
    name="silver_mandi_prices",
    comment="Cleaned mandi market prices with numeric fields."
)
def silver_mandi_prices():

    df = spark.read.table(
        f"{CURATED}.bronze_mandi_prices"
    )

    # Standardize column names
    df = _standardize_columns(df)

    # Trim string values
    df = _trim_strings(df)

    # Parse reported date
    if "reported_date" in df.columns:

        df = _parse_date(
            df,
            "reported_date",
            [
                "dd-MM-yyyy",
                "yyyy-MM-dd",
                "dd/MM/yyyy"
            ]
        )

    # Convert price and quantity columns into DOUBLE
    numeric_columns = [
        "as_on",
        "cumm_arr",
        "msp_price",
        "one_yr_ago",
        "two_yr_ago",
        "three_yr_ago",
        "one_week_ago",
        "last_five_day",
        "one_month_ago",
        "deviation_percent",
        "deviation_from_msp"
    ]

    for column in numeric_columns:
        df = _cast_double(df, column)

    # Clean descriptive columns
    string_columns = [
        "state_name",
        "district_name",
        "market_name",
        "cmdt_name",
        "cmdt_grp_name",
        "trend"
    ]

    for column in string_columns:
        if column in df.columns:
            df = df.withColumn(
                column,
                F.trim(F.col(column))
            )

    # Remove metadata before deduplication
    df = _remove_metadata_and_deduplicate(df)

    return df
