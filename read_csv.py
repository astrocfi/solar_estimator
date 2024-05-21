import csv
import numpy as np
import pandas as pd

YEAR = 2022

def _read_pvwatts_file(filename):
    header_types = {
        "Month": np.int32,
        "Day": np.int32,
        "Hour": np.int32,
        "DC Array Output (W)": np.float64,
        "AC System Output (W)": np.float64
    }

    df = pd.read_csv(filename, skiprows=31, dtype=header_types)
    df = df.set_index(["Month", "Day", "Hour"])
    df = df.filter(["DC Array Output (W)"])
    df.rename(columns={"DC Array Output (W)": "Gen_DCW"}, inplace=True)

    return df

def read_pv_data():
    # Output from NREL PVWatts Calculator (https://pvwatts.nrel.gov/pvwatts.php)
    # "Month","Day","Hour","Beam Irradiance (W/m2)","Diffuse Irradiance (W/m2)",
    # "Ambient Temperature (C)","Wind Speed (m/s)","Albedo",
    # "Plane of Array Irradiance (kW/m2)","Cell Temperature (C)",
    # "DC Array Output (W)","AC System Output (W)"

    df_east = _read_pvwatts_file("data/pvwatts_hourly_east.csv")
    df_south = _read_pvwatts_file("data/pvwatts_hourly_south.csv")
    df_west = _read_pvwatts_file("data/pvwatts_hourly_west.csv")
    df_north = _read_pvwatts_file("data/pvwatts_hourly_north.csv")

    df = df_east.join(df_south, lsuffix="_E", rsuffix="_S")
    df_west.rename(columns={"Gen_DCW": "Gen_DCW_W"}, inplace=True)
    df = df.join(df_west)
    df_north.rename(columns={"Gen_DCW": "Gen_DCW_N"}, inplace=True)
    df = df.join(df_north)

    return df

def read_usage_data(year):
    # DateTime,Device ID,Name,Device Type,Device Make,Device Model,
    # Device Location,Avg Wattage,kWh

    header_types = {
        "Avg Wattage": np.float64
    }

    df = pd.read_csv(f"data/usage_{year}.csv", skiprows=1, dtype=header_types)
    df["Month"] = [int(x[5:7]) for x in df["DateTime"]]
    df["Day"] = [int(x[8:10]) for x in df["DateTime"]]
    df["Hour"] = [int(x[11:13]) for x in df["DateTime"]]
    df = df.set_index(["Month", "Day", "Hour"])
    df_usage = df[df["Name"] == "Total Usage"].copy()
    df_usage.rename(columns={"Avg Wattage": "Used_ACKW"}, inplace=True)
    df_solar = df[df["Name"] == "Solar Production"].copy()
    df_solar["Avg Wattage"] = -df_solar["Avg Wattage"]
    df_solar.rename(columns={"Avg Wattage": "Gen_Cur_ACKW"}, inplace=True)
    df = df_usage.join(df_solar, lsuffix="_1", rsuffix="_2")
    df = df.filter(["Used_ACKW", "Gen_Cur_ACKW"])
    df["Used_ACKW"] = df["Used_ACKW"] / 1000
    df["Gen_Cur_ACKW"] = df["Gen_Cur_ACKW"] / 1000

    return df

def read_monthly_usage_data(year):
    # Month,kWh
    df = pd.read_csv(f"data/monthly_usage_{year}.csv", index_col="Month")
    return df

def read_monthly_gen_data(year):
    # Month,kWh
    df = pd.read_csv(f"data/monthly_generation_{year}.csv", index_col="Month")
    return df

def read_nem3_data():
    # Data from Avoided Cost Calculator at
    # https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/demand-side-management/energy-efficiency/idsm
    # Rows are hours, columns are months; all in $/MWh

    with open("data/nem3_sell_rates.csv", newline='') as csvfile:
        reader = csv.reader(csvfile)
        nem3_data = []
        for row in reader:
            nem3_data.append([float(x)/1000 for x in row])

    return nem3_data
