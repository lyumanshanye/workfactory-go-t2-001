import argparse
import json
import logging
import os
import sys
from pathlib import Path
import pandas as pd

def setup_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger("monthly_report")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

def load_config(config_path: str, logger: logging.Logger) -> dict:
    logger.info(f"Loading configuration from {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_parquet(file_path: Path, config: dict, zone_df: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    logger.info(f"Processing parquet file: {file_path.name}")
    df = pd.read_parquet(file_path)
    
    metrics = config.get("metrics", {})
    dt_cols = config.get("datetime_columns", [])
    
    keep_cols = set(["PULocationID"])
    for m in metrics.values():
        keep_cols.add(m["column"])
    keep_cols.update(dt_cols)
    
    existing_cols = [c for c in df.columns if c in keep_cols]
    df = df[existing_cols]
    
    for metric_name, metric_def in metrics.items():
        col = metric_def.get("column")
        if col and col not in df.columns:
            if "default_if_missing" in metric_def:
                default_val = metric_def["default_if_missing"]
                logger.info(f"Column '{col}' missing in {file_path.name}. Filling with default value {default_val}.")
                df[col] = default_val
            else:
                logger.warning(f"Column '{col}' missing and no default value provided.")
                df[col] = None

    for dt_col in dt_cols:
        if dt_col in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df[dt_col]):
                df[dt_col] = pd.to_datetime(df[dt_col])
            if df[dt_col].dt.tz is not None:
                df[dt_col] = df[dt_col].dt.tz_localize(None)
            df[dt_col] = df[dt_col].dt.tz_localize(config["timezone"])
            if dt_col == "lpep_pickup_datetime":
                df["pickup_month"] = df[dt_col].dt.to_period('M').astype(str)

    if "PULocationID" in df.columns:
        df = df.merge(zone_df[["LocationID", "Borough"]], left_on="PULocationID", right_on="LocationID", how="left")
        df["borough"] = df["Borough"].fillna("Unknown").astype(str)
        df.drop(columns=["LocationID", "Borough", "PULocationID"], inplace=True, errors='ignore')
    else:
        df["borough"] = "Unknown"

    return df

def aggregate_data(df: pd.DataFrame, config: dict, logger: logging.Logger) -> pd.DataFrame:
    logger.info("Aggregating data...")
    dimensions = config.get("dimensions", [])
    metrics = config.get("metrics", {})
    
    named_agg = {}
    for metric_name, metric_def in metrics.items():
        col = metric_def["column"]
        agg_type = metric_def["type"]
        named_agg[metric_name] = pd.NamedAgg(column=col, aggfunc=agg_type)
        
    result_df = df.groupby(dimensions).agg(**named_agg).reset_index()
    
    for metric_name, metric_def in metrics.items():
        if metric_def["type"] == "count":
            result_df[metric_name] = result_df[metric_name].astype(int)
        else:
            result_df[metric_name] = result_df[metric_name].astype(float)
            
    return result_df

def main():
    parser = argparse.ArgumentParser(description="Monthly Trip Data Aggregator")
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--zone_file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    logger = setup_logging(args.log)
    logger.info("Starting monthly report generation...")
    
    try:
        config = load_config(args.config, logger)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
        
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"Data directory {data_dir} does not exist.")
        sys.exit(1)
        
    parquet_files = sorted(list(data_dir.glob("*.parquet")))
    if not parquet_files:
        logger.error(f"No parquet files found in {data_dir}.")
        sys.exit(1)
        
    logger.info(f"Found {len(parquet_files)} parquet files.")
    
    try:
        logger.info(f"Loading zone lookup from {args.zone_file}")
        zone_df = pd.read_csv(args.zone_file)
    except Exception as e:
        logger.error(f"Failed to load zone file: {e}")
        sys.exit(1)
        
    dfs = []
    for pf in parquet_files:
        try:
            df_proc = process_parquet(pf, config, zone_df, logger)
            dfs.append(df_proc)
        except Exception as e:
            logger.error(f"Error processing {pf.name}: {e}")
            
    if not dfs:
        logger.error("No data processed successfully.")
        sys.exit(1)
        
    logger.info("Concatenating processed data...")
    full_df = pd.concat(dfs, ignore_index=True)
    result_df = aggregate_data(full_df, config, logger)
    result_df = result_df.sort_values(by=config.get("dimensions", [])).reset_index(drop=True)
    
    logger.info(f"Writing output to {args.output}")
    try:
        result_df.to_csv(args.output, index=False)
        logger.info("Successfully generated monthly report.")
    except Exception as e:
        logger.error(f"Failed to write output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
