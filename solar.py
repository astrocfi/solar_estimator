import matplotlib.pyplot as plt
import numpy as np
import numpy_financial as npf
import pandas as pd

from read_csv import read_pv_data, read_usage_data, read_nem3_data

DEFAULT_INVERTER_EFFICIENCY = 0.99
DEFAULT_PANEL_WATTS = 1000 # In the analysis files

BASELINE_RATE = 0.09
BASELINE_ALLOWANCE = 810.82 # monthly
# Basic electric:
#   6,7,8,9: 9.8, others 9.7   in kWh/day
# All electric:
#   6,7,8,9: 8.5, others 14.6  in kWh/day
# Add medical baseline 16.438 kWh/day

BASELINE_MEDICAL = 16.438 * 30

if True:
    # Basic electric
    BASELINE_SUMMER_KWH = 9.8 * 365/12 + BASELINE_MEDICAL
    BASELINE_WINTER_KWH = 9.7 * 365/12 + BASELINE_MEDICAL
else:
    # All electric
    BASELINE_SUMMER_KWH = 8.5 * 365/12 + BASELINE_MEDICAL
    BASELINE_WINTER_KWH = 14.6 * 365/12 + BASELINE_MEDICAL

df_monthly_baseline = pd.DataFrame(
    [[BASELINE_WINTER_KWH, BASELINE_RATE], # Jan
     [BASELINE_WINTER_KWH, BASELINE_RATE], # Feb
     [BASELINE_WINTER_KWH, BASELINE_RATE], # Mar
     [BASELINE_WINTER_KWH, BASELINE_RATE], # Apr
     [BASELINE_WINTER_KWH, BASELINE_RATE], # May
     [BASELINE_SUMMER_KWH, BASELINE_RATE], # Jun
     [BASELINE_SUMMER_KWH, BASELINE_RATE], # Jul
     [BASELINE_SUMMER_KWH, BASELINE_RATE], # Aug
     [BASELINE_SUMMER_KWH, BASELINE_RATE], # Sep
     [BASELINE_WINTER_KWH, BASELINE_RATE], # Oct
     [BASELINE_WINTER_KWH, BASELINE_RATE], # Nov
     [BASELINE_WINTER_KWH, BASELINE_RATE]  # Dec
    ],
    index=range(1,13),
    columns=["Baseline_Threshold", "Baseline_Rate"]
)

#XXX NOTE ONLY TOU-C USES BASELINE

PANEL_LAYOUTS = {
    "none": {
        "panels": [],
        "total_loss": 0.00,
    },
    # "test": {
    #     "panels": [
    #         {"panel_watts": 400, "direction": "west", "number": 1, "shading": 0},
    #     ],
    #     "total_loss": 0.15,
    # },
    # "current": {
    #     "panels": [
    #         {"panel_watts": 160, "direction": "south", "number":  6, "shading": 0.00},
    #         {"panel_watts": 160, "direction":  "west", "number": 29, "shading": 0.00},
    #     ],
    #     "total_loss": 0.15,
    # },
    # "starpower": {
    #     "panels": [
    #         {"panel_watts": 400, "direction":  "east", "number":  7, "shading": 0.00},
    #         {"panel_watts": 400, "direction": "south", "number": 19, "shading": 0.00},
    #         {"panel_watts": 400, "direction":  "west", "number": 20, "shading": 0.00},
    #     ],
    #     "total_loss": 0.15,
    # },
    # "earthelectric": {
    #     "panels": [
    #         {"panel_watts": 400, "direction":  "east", "number":  3, "shading": 0.00},
    #         {"panel_watts": 400, "direction": "south", "number": 12, "shading": 0.00},
    #         {"panel_watts": 400, "direction":  "west", "number": 29, "shading": 0.00},
    #     ],
    #     "total_loss": 0.15,
    # },
    # "svce100_bid3": {
    #     "panels": [
    #         {"panel_watts": 400, "direction":  "east", "number":  6, "shading": 0.00},
    #         {"panel_watts": 400, "direction": "south", "number": 11, "shading": 0.00},
    #         {"panel_watts": 400, "direction":  "west", "number": 19, "shading": 0.00},
    #         {"panel_watts": 400, "direction": "north", "number":  9, "shading": 0.00},
    #     ],
    #     "total_loss": 0.22,
    # },
    # "svce100_3300_bid3": {
    #     "panels": [
    #         {"panel_watts": 400, "direction":  "east", "number":  6, "shading": 0.00},
    #         {"panel_watts": 400, "direction": "south", "number": 11, "shading": 0.00},
    #         {"panel_watts": 400, "direction":  "west", "number": 19, "shading": 0.00},
    #         {"panel_watts": 400, "direction": "north", "number": 12, "shading": 0.00},
    #     ],
    #     "total_loss": 0.22,
    # },
    "mydesign1": {
        "panels": [
            # Second story
            {"name": "2E", "panel_watts": 400, "direction":  "east", "number":  3, "shading": 0.10},
            {"name": "2S", "panel_watts": 400, "direction": "south", "number":  3, "shading": 0.10},
            {"name": "2W", "panel_watts": 400, "direction":  "west", "number": 20, "shading": 0.00},
            # First story
            {"name": "1S", "panel_watts": 400, "direction": "south", "number":  1, "shading": 0.30},
            {"name": "1W", "panel_watts": 400, "direction":  "west", "number":  4, "shading": 0.30},
            # Garage
            {"name": "GS", "panel_watts": 400, "direction": "south", "number": 10, "shading": 0.05},
            {"name": "GW", "panel_watts": 400, "direction":  "west", "number":  3, "shading": 0.20},
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


################################################################################


def initialize_rate_schedule(df, tou_type):
    """Initialize the Sell_Price and Buy_Price df fields based on the tou_type."""
    df["Sell_Price"] = 0
    df["Buy_Price"] = 0

    # Handle BUY PRICE
    if tou_type.endswith("TOUC"):
        winter_months = [1, 2, 3, 4, 5, 10, 11, 12]
        summer_months = [6, 7, 8, 9]
        off_peak_hours = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,21,22,23]
        mid_peak_hours = []
        on_peak_hours = [16,17,18,19,20]
    elif tou_type.endswith("TOUD"):
        winter_months = [1, 2, 3, 4, 5, 10, 11, 12]
        summer_months = [6, 7, 8, 9]
        off_peak_hours = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,20,21,22,23]
        mid_peak_hours = []
        on_peak_hours = [17,18,19]
    elif tou_type.endswith("EV2A"):
        winter_months = [1, 2, 3, 4, 5, 10, 11, 12]
        summer_months = [6, 7, 8, 9]
        off_peak_hours = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14]
        mid_peak_hours = [15,21,22,23]
        on_peak_hours = [16,17,18,19,20]
    else:
        assert False, tou_type

    winter_off_peak_index = pd.IndexSlice[winter_months, :, off_peak_hours]
    winter_mid_peak_index = pd.IndexSlice[winter_months, :, mid_peak_hours]
    winter_on_peak_index = pd.IndexSlice[winter_months,  :, on_peak_hours]
    summer_off_peak_index = pd.IndexSlice[summer_months, :, off_peak_hours]
    summer_mid_peak_index = pd.IndexSlice[summer_months, :, mid_peak_hours]
    summer_on_peak_index = pd.IndexSlice[summer_months,  :, on_peak_hours]

    if tou_type.endswith("TOUC"):
        df.loc[winter_off_peak_index, "Buy_Price"] = 0.37
        df.loc[winter_on_peak_index, "Buy_Price"] = 0.39
        df.loc[summer_off_peak_index, "Buy_Price"] = 0.43
        df.loc[summer_on_peak_index, "Buy_Price"] = 0.49
    elif tou_type.endswith("TOUD"):
        df.loc[winter_off_peak_index, "Buy_Price"] = 0.35
        df.loc[winter_on_peak_index, "Buy_Price"] = 0.38
        df.loc[summer_off_peak_index, "Buy_Price"] = 0.34
        df.loc[summer_on_peak_index, "Buy_Price"] = 0.47
    elif tou_type.endswith("EV2A"):
        df.loc[winter_off_peak_index, "Buy_Price"] = 0.24171
        df.loc[winter_mid_peak_index, "Buy_Price"] = 0.41041
        df.loc[winter_on_peak_index, "Buy_Price"] = 0.42711
        df.loc[summer_off_peak_index, "Buy_Price"] = 0.24171
        df.loc[summer_mid_peak_index, "Buy_Price"] = 0.44373
        df.loc[summer_on_peak_index, "Buy_Price"] = 0.5542
    else:
        assert False, tou_type

    if tou_type.startswith("NEM2"):
        df["Sell_Price"] = df["Buy_Price"] # NEM2 is 1-1 net metering
    elif tou_type.startswith("NEM3"):
        for hour in range(24):
            for month in range(12):
                index = pd.IndexSlice[month+1,  :, hour]
                df.loc[index, "Sell_Price"] = nem3_data[hour][month]
    else:
        assert False, tou_type


def calculate_usage_and_cost(df_pv, df_usage,
                             panel_layout, inverter_details,
                             battery_capacity,
                             daily_ev_amount, ev_time,
                             tou_type, panel_ratio=1):

    # Add in EV usage at the appropriate hour
    df_usage["Used_ACKW_EV"] = df_usage["Used_ACKW"]
    if daily_ev_amount > 0:
        df_usage.loc[pd.IndexSlice[:, :, ev_time], "Used_ACKW_EV"] += daily_ev_amount

    # Calculate the total generation for the panels, DC
    total_dckw = 0
    rated_dckw = 0
    total_panels = 0
    for panel_details in panel_layout["panels"]:
        total_panels += panel_details["number"]
        dckw = panel_details["panel_watts"] * panel_details["number"] * panel_ratio / 1000
        rated_dckw += dckw
        total_dckw += (dckw / DEFAULT_PANEL_WATTS *
                       (1-panel_details["shading"]) *
                       df_pv["Gen_DCW_"+panel_details["direction"][0].upper()])

    df_pv["Total_DCKW"] = total_dckw

    # Calculate the total generation after the inverter, AC
    df_pv["Gen_ACKW"] = ((df_pv["Total_DCKW"] *
                          (DEFAULT_INVERTER_EFFICIENCY /
                           inverter_details["efficiency"]) *
                          (1-panel_layout["total_loss"]) *
                           inverter_details["fudge_factor"])
                         .clip(0, inverter_details["ac_max"]))

    # Make one DF with usage and generation together
    df = df_pv.join(df_usage)

    df["Net_Usage"] = df["Used_ACKW_EV"] - df["Gen_ACKW"]
    df["Battery_Charge"] = df["Used_ACKW_EV"] * 0
    df["Battery_Delta"] = df["Used_ACKW_EV"] * 0
    df["Solar_Off_Usage"] = df["Used_ACKW_EV"] * (df["Gen_ACKW"] == 0)

    # Handle battery charging
    # We give preference to using the battery over using the grid without regard
    # to time of day. This may not be optimal.
    if battery_capacity > 0:
        charge = 0.
        for index, row in df.iterrows():
            net_usage = row["Net_Usage"]
            battery_delta = 0.
            if net_usage > 0:
                # Pull from battery
                battery_delta = -min(charge, net_usage)
            elif net_usage < 0:
                # Charge battery
                battery_delta = min(battery_capacity-charge, -net_usage)
            charge += battery_delta
            net_usage += battery_delta
            # print(index, battery_delta, charge)
            df["Net_Usage"][*index] = net_usage
            df["Battery_Delta"][*index] = battery_delta
            df["Battery_Charge"][*index] = charge
            # print(df.loc[*index]["Battery_Charge"], charge)

    # Insert columns for the Buy and Sell price based on tou_type
    initialize_rate_schedule(df, tou_type)

    # Cost has to be computed hourly, the baseline applied monthly
    df["Net_Cost"] = 0
    df.loc[df["Net_Usage"] < 0, "Net_Cost"] = (df.loc[df["Net_Usage"] < 0, "Net_Usage"] *
                                               df.loc[df["Net_Usage"] < 0, "Sell_Price"])
    df.loc[df["Net_Usage"] > 0, "Net_Cost"] = (df.loc[df["Net_Usage"] > 0, "Net_Usage"] *
                                               df.loc[df["Net_Usage"] > 0, "Buy_Price"])

    return df, total_panels, rated_dckw


################################################################################


def run_one_scenario(panel_type, inverter_type, battery_capacity,
                     daily_ev_amount, ev_time, tou_type, show_output=False,
                     panel_ratio=1):
    panel_layout = PANEL_LAYOUTS[panel_type]
    inverter_details = INVERTERS[inverter_type]

    df, total_panels, rated_dckw = calculate_usage_and_cost(
                                    df_pv, df_usage,
                                    panel_layout, inverter_details,
                                    battery_capacity,
                                    daily_ev_amount, ev_time,
                                    tou_type, panel_ratio=panel_ratio)

    df_daily = df.groupby(level=(0,-2)).sum()
    df_monthly = df.groupby(level=0).sum()

    # Baseline is only for TOU-C
    if tou_type.endswith("TOUC"):
        df_monthly["Net_Cost"] -= (df_monthly["Net_Usage"]
                                .clip(lower=0, upper=df_monthly_baseline["Baseline_Threshold"]) *
                                df_monthly_baseline["Baseline_Rate"])

    total_annual_kwh_gen = df["Gen_ACKW"].sum()
    total_annual_kwh_use = df["Used_ACKW_EV"].sum()
    total_annual_kwh_net_use = df["Net_Usage"].sum()
    total_annual_kwh_from_grid = df["Net_Usage"].loc[df["Net_Usage"] > 0].sum()
    total_cost = df_monthly["Net_Cost"].sum()
    solar_off_usage_max = df_daily["Solar_Off_Usage"].max()
    solar_off_usage_mean = df_daily["Solar_Off_Usage"].mean()
    solar_off_usage_std = df_daily["Solar_Off_Usage"].std()
    usage_max = df["Used_ACKW"].max()

    if battery_capacity == 0:
        install_cost = rated_dckw * 1000 * 2.69 + 6626
    else:
        install_cost = rated_dckw * 1000 * 2.66 + 23044

    if show_output:
        usage_2022 = df_usage["Used_ACKW"].sum()

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
        print(f"  Max:         {usage_max:,.2f} kWh/hr")
        print("Potential Battery Draw:")
        print(f"  Max:       {solar_off_usage_max:,.2f} kWh/day")
        print(f"  Mean:      {solar_off_usage_mean:,.2f} kWh/day")
        print(f"  Std:       {solar_off_usage_std:,.2f} kWh/day")
        print(f"  From Grid: {total_annual_kwh_from_grid:,.2f} kWh/yr")
        print("Summary:")
        print(f"  Net usage:  {total_annual_kwh_net_use:,.2f} kWh/yr")
        print(f"  Total cost: ${total_cost:,.2f}")

    if True:
        plt.figure()
        df_monthly["Gen_ACKW"].plot(color="orange", lw=2, label="Modeled System Gen")
        df_monthly["Battery_Delta"].plot(color="orange", lw=1, ls="-",
                                        label="Modeled Battery Delta")
        df_monthly["Used_ACKW_EV"].plot(color="red", lw=3, label="2022 Usage")
        df_monthly["Net_Usage"].plot(color="black", lw=3, label="Net Usage")
        plt.legend()
        plt.ylabel("kWh/month")
        plt.xlabel("Month")
        plt.xticks(range(1,13))
        plt.show()

    if True:
        plt.figure()
        df_monthly["Net_Cost"].plot(color="black", lw=2, label="Net Cost")
        plt.legend()
        plt.ylabel("$/month")
        plt.xlabel("Month")
        plt.xticks(range(1,13))
        plt.show()

    if True:
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

    if True:
        plt.figure()
        df_monthly["Gen_ACKW"].plot()
        plt.ylabel("Generated kWh/month")
        plt.xlabel("Month")
        plt.xticks(range(1,13))
        plt.show()

    if True:
        plt.figure()
        df["Gen_ACKW"].plot(color="orange", lw=2, label="Modeled System Gen")
        df["Battery_Charge"].plot(color="orange", lw=1, ls="-",
                                label="Modeled Battery Charge")
        df["Used_ACKW_EV"].plot(color="red", lw=3, label="2022 Usage")
        df["Net_Usage"].plot(color="black", lw=3, label="Net Usage")
        plt.legend()
        plt.show()

    return total_cost, install_cost

#===============================================================================

def plot_nem3():
    plt.figure()
    plt.contour(nem3_data)
    plt.show()

def panels_vs_cost():
    EV_MILES = 10000
    EV_POWER_PER_MILE = 0.346
    EV_ANNUAL_POWER = EV_MILES * EV_POWER_PER_MILE
    daily_ev_amount = EV_ANNUAL_POWER / 365
    ev_time = 1 # Hour in 24-hour format

    INFLATION_RATE = 1.04
    NUM_YEARS = 20

    plt.figure()

    for batt in (False, True):
    # for batt in (False,):
        battery_capacity = 13.6 if batt else 0
        for tou_type in ("NEM2-TOUC", "NEM2-TOUD", "NEM2-EV2A", "NEM3-TOUC", "NEM3-TOUD", "NEM3-EV2A"):
        # for tou_type in ("NEM2-TOUC",):
            print("Batt", batt, tou_type)
            base_cost = None
            panel_list = []
            ratio_list = []
            for num_panels in range(0, 45):
                total_cost, install_cost = run_one_scenario("mydesign1", "enphase", battery_capacity,
                                                            daily_ev_amount, ev_time, tou_type,
                                                            panel_ratio=num_panels/44)
                total_cost = max(total_cost, 0)
                if num_panels == 0:
                    base_cost = total_cost
                saved_amt = base_cost-total_cost
                ratio = install_cost / saved_amt

                irr_list = [-install_cost]
                cur_saved_amt = saved_amt
                for i in range(NUM_YEARS):
                    irr_list.append(cur_saved_amt)
                    cur_saved_amt *= INFLATION_RATE
                irr = npf.irr(irr_list)
                if num_panels > 0:
                    panel_list.append(num_panels)
                    # ratio_list.append(ratio)
                    ratio_list.append(irr)
                print(f'{num_panels:2d} ${total_cost:6.0f} ${saved_amt:6.0f} ${install_cost:6.0f} {ratio:.2f} {irr:.2f}')

            if tou_type.endswith("TOUC"):
                color = "red"
            elif tou_type.endswith("TOUD"):
                color = "green"
            elif tou_type.endswith("EV2A"):
                color = "blue"
            else:
                assert False, tou_type
            if tou_type.startswith("NEM2"):
                style = "-"
            elif tou_type.startswith("NEM3"):
                style = "--"
            else:
                assert False, tou_type
            label = tou_type
            lw = 1
            if batt:
                label = "BATT/"+tou_type
                lw = 2
            plt.plot(panel_list, ratio_list, label=label, color=color, lw=lw, ls=style)
    plt.xlabel("# of Panels")
    # plt.ylabel("Install cost / amount saved")
    plt.ylabel("IRR")
    # plt.ylim(0, .3)
    plt.legend(ncols=2)
    plt.show()

# Initialize global data
df_pv = read_pv_data()
df_usage = read_usage_data()
nem3_data = read_nem3_data()


# plot_nem3()

# panels_vs_cost()



# inverter_type = "current"
# inverter_type = "solaredge"
inverter_type = "enphase"

panel_type = "none"
# panel_type = "test"
# panel_type = "current"
# panel_type = "starpower"
# panel_type = "earthelectric"
# panel_type = "svce100_bid3"
# panel_type = "svce100_3300_bid3"
# panel_type = "mydesign1"

tou_type = "NEM2-TOUC"
# tou_type = "NEM2-TOUD"
# tou_type = "NEM3-TOUC"
# tou_type = "NEM3-TOUD"

# EV_MILES = 0
EV_MILES = 10000
EV_POWER_PER_MILE = 0.346
EV_ANNUAL_POWER = EV_MILES * EV_POWER_PER_MILE
daily_ev_amount = EV_ANNUAL_POWER / 365
ev_time = 1 # Hour in 24-hour format

# battery_capacity = 0
battery_capacity = 13.6 # Franklin
# battery_capacity = 13.6 * 5

run_one_scenario(panel_type, inverter_type, battery_capacity,
                 daily_ev_amount, ev_time, tou_type, show_output=True)
