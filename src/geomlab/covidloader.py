import pandas as pd
import numpy as np
import re
from datetime import datetime

# Date Pattern
date_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{2}")


def reformat_dates(col_name: str) -> str:
    # for columns which are dates, I'd much rather they were in day/month/year format
    try:
        return date_pattern.sub(
            datetime.strptime(col_name, "%m/%d/%y").strftime("%d/%m/%Y"),
            col_name,
            count=1,
        )
    except ValueError:
        return col_name


print()
print("Downloading most recent COVID-19 data...")
print()

# Get most recent confirmed cases, recovered and deaths
confirmed_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
recovered_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv"
deaths_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

renamed_columns_map = {
    "Country/Region": "country",
    "Province/State": "location",
    "Lat": "latitude",
    "Long": "longitude",
}

cols_to_drop = ["location", "latitude", "longitude"]

print("1/3: All confirmed cases...")

confirmed_cases_df = (
    pd.read_csv(confirmed_url)
    .rename(columns=renamed_columns_map)
    .rename(columns=reformat_dates)
    .drop(columns=cols_to_drop)
)

print("2/3: All death cases...")

deaths_df = (
    pd.read_csv(deaths_url)
    .rename(columns=renamed_columns_map)
    .rename(columns=reformat_dates)
    .drop(columns=cols_to_drop)
)

print("3/3: Recovered cases...")

recovered_df = (
    pd.read_csv(recovered_url)
    .rename(columns=renamed_columns_map)
    .rename(columns=reformat_dates)
    .drop(columns=cols_to_drop)
)

print()
print("✨  COVID-19 downloads from John Hopkins University successful. ✨")
print()

geo_data_df = confirmed_cases_df[["country"]].drop_duplicates()
country_codes_df = pd.read_csv(
    "data/country_code_mapping.csv",
    usecols=["country", "alpha-3_code"],
    index_col="country",
)
geo_data_df = geo_data_df.join(country_codes_df, how="left", on="country").set_index(
    "country"
)

dates_list = deaths_df.filter(regex=r"(\d{2}/\d{2}/\d{4})", axis=1).columns.to_list()

# create a mapping of date -> DataFrame, where each df holds the daily counts of cases and deaths per country
# TODO: Shift all of this into one df later on
for date in dates_list:

    confirmed_cases_day_df = confirmed_cases_df.filter(like=date, axis=1).rename(
        columns=lambda col: "confirmed_cases"
    )

    deaths_day_df = deaths_df.filter(like=date, axis=1).rename(
        columns=lambda col: "deaths"
    )
    cases_df = confirmed_cases_day_df.join(deaths_day_df).set_index(
        confirmed_cases_df["country"]
    )

    date_df = (
        geo_data_df.join(cases_df)
        .groupby("country")
        .agg({"confirmed_cases": "sum", "deaths": "sum", "alpha-3_code": "first"})
    )

    date_df = date_df[date_df["confirmed_cases"] > 0].reset_index()

renamed_columns_map = {
    "Country/Region": "country",
    "Province/State": "location",
    "Lat": "latitude",
    "Long": "longitude",
}

confirmed_cases_df = (
    pd.read_csv(confirmed_url)
    .rename(columns=renamed_columns_map)
    .rename(columns=reformat_dates)
    .fillna(method="bfill", axis=1)
)

deaths_df = (
    pd.read_csv(deaths_url)
    .rename(columns=renamed_columns_map)
    .rename(columns=reformat_dates)
    .fillna(method="bfill", axis=1)
)

recovered_df = (
    pd.read_csv(recovered_url)
    .rename(columns=renamed_columns_map)
    .rename(columns=reformat_dates)
    .fillna(method="bfill", axis=1)
)

geo_data_cols = ["country", "location", "latitude", "longitude"]

geo_data_df = confirmed_cases_df[geo_data_cols]

# Rewrite date to European style
dates_list = confirmed_cases_df.filter(
    regex=r"(\d{2}/\d{2}/\d{4})", axis=1
).columns.to_list()

# We'll use this data dict to connect to the symbolic page display
cases_by_date = {}

for date in dates_list:

    confirmed_cases_day_df = confirmed_cases_df[["country", "location", date]].copy()
    confirmed_cases_day_df.rename(
        columns={"country": "country", date: "confirmed_cases"}, inplace=True
    )
    confirmed_cases_day_df["confirmed_cases"] = pd.to_numeric(
        confirmed_cases_day_df["confirmed_cases"]
    )

    recovered_day_df = recovered_df[["country", "location", date]].copy()
    recovered_day_df.rename(columns={date: "recovered"}, inplace=True)
    recovered_day_df["recovered"] = pd.to_numeric(recovered_day_df["recovered"])

    deaths_day_df = deaths_df[["country", "location", date]].copy()
    deaths_day_df.rename(columns={"country": "country", date: "deaths"}, inplace=True)
    deaths_day_df["deaths"] = pd.to_numeric(deaths_day_df["deaths"])

    cases_df = geo_data_df.merge(
        confirmed_cases_day_df, how="left", on=["country", "location"]
    )
    cases_df = cases_df.merge(recovered_day_df, how="left", on=["country", "location"])
    cases_df = cases_df.merge(deaths_day_df, how="left", on=["country", "location"])

    # TODO: collecting zeroes nevertheless, watch out when drawing
    # cases_df = cases_df[cases_df["confirmed_cases"] > 0]

    # TODO: This is quite dangerous and might mask other errors
    cases_df.replace(np.nan, 0)

    cases_by_date[date] = cases_df
