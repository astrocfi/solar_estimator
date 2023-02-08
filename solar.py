import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from read_csv import read_pv_data, read_usage_data

DEFAULT_INVERTER_EFFICIENCY = 0.99
DEFAULT_PANEL_WATTS = 1000 # In the analysis files

BASELINE_RATE = 0.09
BASELINE_ALLOWANCE = 810.82 # monthly

# inverter_type = "current"
# inverter_type = "solaredge"
inverter_type = "enphase"

# panel_type = "none"
# panel_type = "test"
# panel_type = "current"
# panel_type = "starpower"
# panel_type = "earthelectric"
# panel_type = "svce100_bid3"
# panel_type = "svce100_3300_bid3"
panel_type = "mydesign1"

tou_type = "NEM2-TOUC"
# tou_type = "NEM2-TOUD"
# tou_type = "NEM3-TOUC"
# tou_type = "NEM3-TOUD"

# EV_MILES = 0
EV_MILES = 10000
EV_POWER_PER_MILE = 0.346
EV_ANNUAL_POWER = EV_MILES * EV_POWER_PER_MILE
add_daily_ev_amount = EV_ANNUAL_POWER / 365

BATTERY_CAPACITY = 10 # Useable kWh

PANEL_LAYOUTS = {
    "none": {
        "panels": [],
        "total_loss": 0.00,
    },
    "test": {
        "panels": [
            {"panel_watts": 400, "direction": "west", "number": 1, "shading": 0},
        ],
        "total_loss": 0.15,
    },
    "current": {
        "panels": [
            {"panel_watts": 160, "direction": "south", "number":  6, "shading": 0.00},
            {"panel_watts": 160, "direction":  "west", "number": 29, "shading": 0.00},
        ],
        "total_loss": 0.15,
    },
    "starpower": {
        "panels": [
            {"panel_watts": 400, "direction":  "east", "number":  7, "shading": 0.00},
            {"panel_watts": 400, "direction": "south", "number": 19, "shading": 0.00},
            {"panel_watts": 400, "direction":  "west", "number": 20, "shading": 0.00},
        ],
        "total_loss": 0.15,
    },
    "earthelectric": {
        "panels": [
            {"panel_watts": 400, "direction":  "east", "number":  3, "shading": 0.00},
            {"panel_watts": 400, "direction": "south", "number": 12, "shading": 0.00},
            {"panel_watts": 400, "direction":  "west", "number": 29, "shading": 0.00},
        ],
        "total_loss": 0.15,
    },
    "svce100_bid3": {
        "panels": [
            {"panel_watts": 400, "direction":  "east", "number":  6, "shading": 0.00},
            {"panel_watts": 400, "direction": "south", "number": 11, "shading": 0.00},
            {"panel_watts": 400, "direction":  "west", "number": 19, "shading": 0.00},
            {"panel_watts": 400, "direction": "north", "number":  9, "shading": 0.00},
        ],
        "total_loss": 0.22,
    },
    "svce100_3300_bid3": {
        "panels": [
            {"panel_watts": 400, "direction":  "east", "number":  6, "shading": 0.00},
            {"panel_watts": 400, "direction": "south", "number": 11, "shading": 0.00},
            {"panel_watts": 400, "direction":  "west", "number": 19, "shading": 0.00},
            {"panel_watts": 400, "direction": "north", "number": 12, "shading": 0.00},
        ],
        "total_loss": 0.22,
    },
    "mydesign1": {
        "panels": [
            # Second story
            {"panel_watts": 400, "direction":  "east", "number":  3, "shading": 0.10},
            {"panel_watts": 400, "direction": "south", "number":  3, "shading": 0.10},
            {"panel_watts": 400, "direction":  "west", "number": 20, "shading": 0.00},
            # First story
            {"panel_watts": 400, "direction": "south", "number":  1, "shading": 0.30},
            {"panel_watts": 400, "direction":  "west", "number":  4, "shading": 0.30},
            # Garage
            {"panel_watts": 400, "direction": "south", "number": 10, "shading": 0.05},
            {"panel_watts": 400, "direction":  "west", "number":  3, "shading": 0.20},
        ],
        "total_loss": 0.15,
    },
}

INVERTERS = {
    "current": {
        "efficiency": 0.9,
        "fudge_factor": 0.55,
        "ac_max": 1e38
    },
    "solaredge": {
        "efficiency": 0.99 * 0.988, # inverter, power optimizers
        "fudge_factor": 0.8715,
        "ac_max": 11400
    },
    "enphase": {
        "efficiency": 0.92,
        "fudge_factor": 0.89,
        "ac_max": 1e38
    },
}

df_pv = read_pv_data()
df_usage = read_usage_data()

usage_2022 = df_usage["Used_ACKW"].sum()

df_usage.loc[pd.IndexSlice[:, :, 1], "Used_ACKW"] += add_daily_ev_amount

panel_layout = PANEL_LAYOUTS[panel_type]
inverter_details = INVERTERS[inverter_type]

total_dckw = 0
rated_dckw = 0
total_panels = 0
for panel_details in panel_layout["panels"]:
    total_panels += panel_details["number"]
    dckw = panel_details["panel_watts"] * panel_details["number"] / 1000
    rated_dckw += dckw
    total_dckw += (dckw / DEFAULT_PANEL_WATTS *
                   (1-panel_details["shading"]) *
                   df_pv["Gen_DCW_"+panel_details["direction"][0].upper()])

df_pv["Total_DCKW"] = total_dckw

df_pv["Gen_ACKW"] = ((df_pv["Total_DCKW"] *
                      (DEFAULT_INVERTER_EFFICIENCY /
                       inverter_details["efficiency"]) *
                       (1-panel_layout["total_loss"]) *
                       inverter_details["fudge_factor"])
                     .clip(0, inverter_details["ac_max"]))

df = df_pv.join(df_usage)

df["Net_Usage"] = df["Used_ACKW"] - df["Gen_ACKW"]

df["Solar_Off_Usage"] = df["Used_ACKW"] * (df["Gen_ACKW"] == 0)

df["Sell_Price"] = 0
df["Buy_Price"] = 0
if tou_type == "NEM2-TOUC" or tou_type == "NEM3-TOUC":
    winter_off_peak_index = pd.IndexSlice[[1, 2, 3, 4, 5, 10, 11, 12], :,
                                          [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,21,22,23]]
    df.loc[winter_off_peak_index, "Sell_Price"] = 0.37 if tou_type == "NEM2-TOUC" else 0.08
    df.loc[winter_off_peak_index, "Buy_Price"] = 0.37
    winter_on_peak_index = pd.IndexSlice[[1, 2, 3, 4, 5, 10, 11, 12], :,
                                         [16,17,18,19,20]]
    df.loc[winter_on_peak_index, "Sell_Price"] = 0.39 if tou_type == "NEM2-TOUC" else 0.08
    df.loc[winter_on_peak_index, "Buy_Price"] = 0.39
    summer_off_peak_index = pd.IndexSlice[[6, 7, 8, 9], :,
                                          [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,21,22,23]]
    df.loc[summer_off_peak_index, "Sell_Price"] = 0.43 if tou_type == "NEM2-TOUC" else 0.08
    df.loc[summer_off_peak_index, "Buy_Price"] = 0.43
    summer_on_peak_index = pd.IndexSlice[[6, 7, 8, 9], :,
                                         [16,17,18,19,20]]
    df.loc[summer_on_peak_index, "Sell_Price"] = 0.49 if tou_type == "NEM2-TOUC" else 0.08
    df.loc[summer_on_peak_index, "Buy_Price"] = 0.49
elif tou_type == "NEM2-TOUD" or tou_type == "NEM3-TOUD":
    winter_off_peak_index = pd.IndexSlice[[1, 2, 3, 4, 5, 10, 11, 12], :,
                                          [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23]]
    df.loc[winter_off_peak_index, "Sell_Price"] = 0.37 if tou_type == "NEM2-TOUD" else 0.08
    df.loc[winter_off_peak_index, "Buy_Price"] = 0.37
    winter_on_peak_index = pd.IndexSlice[[1, 2, 3, 4, 5, 10, 11, 12], :,
                                         [17,18,19]]
    df.loc[winter_on_peak_index, "Sell_Price"] = 0.39 if tou_type == "NEM2-TOUD" else 0.08
    df.loc[winter_on_peak_index, "Buy_Price"] = 0.39
    summer_off_peak_index = pd.IndexSlice[[6, 7, 8, 9], :,
                                          [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23]]
    df.loc[summer_off_peak_index, "Sell_Price"] = 0.43 if tou_type == "NEM2-TOUD" else 0.08
    df.loc[summer_off_peak_index, "Buy_Price"] = 0.43
    summer_on_peak_index = pd.IndexSlice[[6, 7, 8, 9], :,
                                         [17,18,19]]
    df.loc[summer_on_peak_index, "Sell_Price"] = 0.49 if tou_type == "NEM2-TOUD" else 0.08
    df.loc[summer_on_peak_index, "Buy_Price"] = 0.49
else:
    assert False, tou_type



# Cost has to be computed hourly, the baseline applied monthly
df["Net_Cost"] = 0
df.loc[df["Net_Usage"] < 0, "Net_Cost"] = (df.loc[df["Net_Usage"] < 0, "Net_Usage"] *
                                           df.loc[df["Net_Usage"] < 0, "Sell_Price"])
df.loc[df["Net_Usage"] > 0, "Net_Cost"] = (df.loc[df["Net_Usage"] > 0, "Net_Usage"] *
                                           df.loc[df["Net_Usage"] > 0, "Buy_Price"])


df_daily = df.groupby(level=(0,-2)).sum()
df_monthly = df.groupby(level=0).sum()

df_monthly["Net_Cost"] -= (df_monthly["Net_Usage"]
                           .clip(lower=0, upper=BASELINE_ALLOWANCE) *
                           BASELINE_RATE)

total_annual_kwh_gen = df["Gen_ACKW"].sum()
total_annual_kwh_gen_cur = df["Gen_Cur_ACKW"].sum()
total_annual_kwh_use = df["Used_ACKW"].sum()
total_annual_kwh_net_use = df["Net_Usage"].sum()
total_cost = df_monthly["Net_Cost"].sum()
solar_off_usage_max = df_daily["Solar_Off_Usage"].max()
solar_off_usage_mean = df_daily["Solar_Off_Usage"].mean()
solar_off_usage_std = df_daily["Solar_Off_Usage"].std()

print("System design:")
print("  Rate plan:", tou_type)
print("  Panel layout:", panel_type, f"({total_panels} panels)")
print("  Inverter:", inverter_type)
print(f"  DC rating: {rated_dckw:,.2f} kW")
print(f"  Total generation: {total_annual_kwh_gen:,.2f} kWh/yr")
print("Usage:")
print(f"  2022 usage:  {usage_2022:,.2f} kWh/yr")
print(f"  Added EV:    {EV_MILES} miles/yr")
print(f"  Total usage: {total_annual_kwh_use:,.2f} kWh/yr")
print("Potential Battery Draw:")
print(f"  Max:  {solar_off_usage_max:,.2f} kWh/day")
print(f"  Mean: {solar_off_usage_mean:,.2f} kWh/day")
print(f"  Std:  {solar_off_usage_std:,.2f} kWh/day")
print("Summary:")
print(f"  Net usage:  {total_annual_kwh_net_use:,.2f} kWh/yr")
print(f"  Total cost: ${total_cost:,.2f}")

if False:
    plt.figure()
    df_monthly["Gen_ACKW"].plot(color="orange", lw=2, label="Modeled System Gen")
    df_monthly["Used_ACKW"].plot(color="red", lw=3, label="2022 Usage")
    df_monthly["Net_Usage"].plot(color="black", lw=3, label="Net Usage")
    plt.legend()
    plt.show()


    if panel_type == "current":
        label = "Modeled System Gen"
    else:
        label = "New System Gen"
    df_daily["Gen_ACKW"].plot(color="orange", lw=2, label=label)
    df_daily["Used_ACKW"].plot(color="black", lw=3, label="2022 Usage")
    df_daily["Gen_Cur_ACKW"].plot(color="green", lw=1, label="2022 Gen Cur Sys")

    scale = df_daily["Gen_ACKW"].mean() / df_daily["Gen_Cur_ACKW"].mean()
    # print(f"New/Old Gen Scale: {scale:.3f}")
    # if system != "current":
    #     (df_daily["Total_Gen_Cur_ACKW"]*scale).plot(color="green", lw=1, ls="dashed",
    #                                                 label="2022 Gen Scaled")

    plt.legend()
    plt.ylabel("kWh/day")

    plt.figure()
    df_monthly["Gen_ACKW"].plot()
    plt.show()
