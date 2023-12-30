import os

import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from placelessdb import PDB
from placelessdb.common import close_connection
from mysql import connector

from toggle_view import ToggleableTable

# from constants import PDB_ARGS
pdb_args = dict(db_host=os.getenv("PLACELESS_MYSQL_HOSTNAME", "localhost"),
                db_name=os.getenv("PLACELESS_MYSQL_USERNAME", "placeless"),
                db_user=os.getenv("PLACELESS_MYSQL_DB", "placeless"),
                db_pass=os.getenv("PLACELESS_MYSQL_PASSWORD", "Aa123456")
                )


def get_dates(pred_dates, usage_dates):
    actual_dates = []
    actual_dates_index_usage = []
    actual_dates_index_prediction = []
    for i in range(len(usage_dates)):
        usage_date = usage_dates[i]
        for j in range(len(pred_dates)):
            pred_date = pred_dates[j]
            if sec_between(usage_date, pred_date) < 30:
                actual_dates.append(usage_date)
                actual_dates_index_usage.append(i)
                actual_dates_index_prediction.append(j)
            continue
    return actual_dates, actual_dates_index_usage, actual_dates_index_prediction


def extract_data(results_set, usage_index_list, prediction_index_list, predictions):
    limit_memory = []  # index = 8
    request_memory = []  # index = 6
    limit_cpu = []  # index = 7
    request_cpu = []  # index = 5
    usage_memory = []  # index = 3
    usage_cpu = []  # index = 2
    prediction_memory = []  # index = 0
    prediction_cpu = []  # index = 1

    for index in usage_index_list:
        row = results_set[index]
        limit_memory.append(row[8])
        request_memory.append(row[6])
        limit_cpu.append(row[7])
        request_cpu.append(row[5])
        usage_memory.append(row[3])
        usage_cpu.append(row[2])
    for index in prediction_index_list:
        prediction_memory.append(predictions[index][1])
        prediction_cpu.append(predictions[index][0])

    memory_df = pd.DataFrame({"Usage": usage_memory, "Predictions": prediction_memory,
                              "Request": request_memory, "Limit": limit_memory}).astype(float)
    cpu_df = pd.DataFrame({"Usage": usage_cpu, "Predictions": prediction_cpu,
                           "Request": request_cpu, "Limit": limit_cpu}).astype(float)
    if len(predictions) == 0:
        memory_df = memory_df.drop("Predictions", axis=1)
        cpu_df = cpu_df.drop("Predictions", axis=1)
    return memory_df, cpu_df


def sec_between(d1, d2):
    return (d2 - d1).seconds


def get_data(namespace, workload_name):
    pdb = PDB(**pdb_args)
    num_of_records = 288
    num_of_predictions = 298
    prediction_query = f"""SELECT
                               cpu_pred, mem_pred, predicted_date
                           FROM
                               Predictions
                           WHERE
                               workload_name = '{workload_name}'
                               AND
                               namespace = '{namespace}'
                           ORDER BY
                            predicted_TS DESC LIMIT {num_of_predictions}"""
    try:
        workload_usage = pdb.WorkloadUsagAvg.get_records(worklod_id=(workload_name, namespace),
                                                         num_of_rec=num_of_records)
        usage_dates = [row[1] for row in workload_usage]
        predictions_curr = pdb.Predictions.conn.cursor()
        predictions_curr.execute(prediction_query)
        result_set = predictions_curr.fetchall()
        prediction_result_set = [row for row in result_set]
        if len(prediction_result_set) == 0:
            predictions_curr.close()
            dates_index_usage = [i for i in range(len(workload_usage))]
            dates_index_prediction = []
            dates = usage_dates
        else:

            pred_dates = [predicted_date for cpu_pred, mem_pred, predicted_date in prediction_result_set]
            dates, dates_index_usage, dates_index_prediction = get_dates(usage_dates, pred_dates)
        predictions_curr.close()
        memory_df, cpu_df = extract_data(workload_usage, dates_index_usage, dates_index_prediction,
                                         prediction_result_set)
        memory_df['Date'] = cpu_df['Date'] = dates
        return memory_df.ffill(), cpu_df.ffill()

    except Exception as e:
        close_connection(pdb.connection)
        raise Exception(f"Could not get workloads id's to retrain from DB {e}")


def get_namespaces():
    pdb = PDB(**pdb_args)
    try:
        workloads = pdb.Workload.get_all_workloads(trained=False)
        namespaces = list(set([namespace for workload_name, namespace in workloads]))
        close_connection(pdb.connection)
        print(namespaces)
        return namespaces
    except Exception as err:
        st.error("Failed to retrieve data")
        close_connection(pdb.connection)


def get_workloads(workloads_namespace):
    pdb = PDB(**pdb_args)
    try:
        workloads = pdb.Workload.get_all_workloads(trained=False)
        workloads = list(set([workload_name for workload_name, namespace in workloads
                              if workloads_namespace == namespace]))
        close_connection(pdb.connection)
        return workloads
    except Exception as err:
        st.error("Failed to retrieve data")
        close_connection(pdb.connection)



st.title("PlaceLess Dashboard")

namespaces = get_namespaces()
namespace = st.selectbox(
    "What namespace would you like?",
    get_namespaces(),
    index=None,
    placeholder="Select namespace..."
)

st.write('You selected:', namespace)
if namespace:
    workloads = get_workloads(namespace)
    workload = st.selectbox(
        "What workload would you like?",
        get_workloads(namespace),
        index=None,
        placeholder="Select workload..."
    )
    st.write('You selected:', workload)
    # workload_to_present = st.sidebar.multiselect('Select workload', workloads)
    if workload:
        toggleable_table = ToggleableTable(workload_name=workload, namespace=namespace)
        toggleable_table.display_toggleable_table()

        tab_cpu, tab_memory = st.tabs(["CPU", "Memory"])
        data_memory, data_cpu = get_data(namespace, workload)
        selected_categories1 = st.sidebar.multiselect('Select categories', data_cpu.columns[:-1])
        selected_categories2 = st.sidebar.multiselect('Select categories for diff', data_cpu.columns[:-1])
        color_map = {
            1: ["#F63366"],
            2: ["#F63366", '#FFA500'],
            3: ["#F63366", '#FFC0CB', '#FFD700'],
            4: ["#F63366", '#FFC0CB', '#FFD700', '#800080']
        }

        def display(data, selected_categories1, selected_categories2, is_predictions):
            if not selected_categories1:
                selected_categories1.append("Usage")
            if len(selected_categories1) > 0:
                st.title("Data over time")
                st.line_chart(data, x='Date', y=selected_categories1,
                              color=list(color_map[len(selected_categories1)]))

            st.title(f"Difference Graph")
            if len(selected_categories2) < 2:
                st.write("You must select two categories, default categories otherwise")
                if is_predictions:
                    selected_categories2 = ['Usage', 'Predictions']
                else:
                    selected_categories2 = ['Usage', 'Request']
            if len(selected_categories2) == 2:
                st.subheader(f"{selected_categories2[0]} - {selected_categories2[1]}".strip("'"))

                # Create a copy of the data for calculations
                diff_category_1_2 = data.copy()

                diff_category_1_2[selected_categories2[0]] -= data[selected_categories2[1]]
                diff_category_1_2["Request%"] = round(
                    abs(diff_category_1_2[selected_categories2[0]] / (data['Request'] + 10 ** -6)), 5)

                # Create an Altair chart
                chart = alt.Chart(diff_category_1_2).mark_bar().encode(
                    x='Date',
                    y=alt.Y(selected_categories2[0], stack=None),
                    # Use altair.Y to specify the encoding for the y-axis
                    tooltip=["Request%"],
                    color="Request%"
                ).interactive()

                st.altair_chart(chart, theme="streamlit", use_container_width=True)
            if len(selected_categories2) > 2:
                st.error("Please select only two categories")

        # Default: only Usage selected
        with tab_cpu:
            if data_cpu.empty:
                st.error("There is not data for your request")
            is_predictions = 'Predictions' in data_cpu.columns

            display(data_cpu, selected_categories1, selected_categories2, is_predictions)

        with tab_memory:
            if data_memory.empty:
                st.error("There is not data for your request")
            is_predictions = 'Predictions' in data_memory.columns
            display(data_memory, selected_categories1, selected_categories2, is_predictions)
