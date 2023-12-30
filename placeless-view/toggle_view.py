import streamlit as st
import sqlite3
import pandas as pd
import mysql.connector
import os

def mysql_conn():
    return mysql.connector.connect(
        host=os.getenv("PLACELESS_MYSQL_HOSTNAME", "localhost"),
        user=os.getenv("PLACELESS_MYSQL_USERNAME", "placeless"),
        password=os.getenv("PLACELESS_MYSQL_PASSWORD", "Aa123456"),
        database='placeless'
    )


class ToggleableTable:

    def __init__(self, workload_name, namespace):
        self.workload_name = workload_name
        self.workload_namespace = namespace
        self.table_name = "Workload_Status"

    def fetch_data(self):
        conn = mysql_conn()
        try:
            query = f"SELECT * FROM Workload_Status WHERE workload_name='{self.workload_name}' and namespace='{self.workload_namespace}'"
            df = pd.read_sql(query, conn, index_col='workload_name')
            print(df.values)
            return df
        finally:
            conn.close()

    # Function to update the 'enabled' status in the database
    def update_status(self, workload_name, status):
        conn = mysql_conn()
        try:
            cursor = conn.cursor()
            update_query = f"""UPDATE Workload_Status SET enabled = {status}  WHERE workload_name='{workload_name}' and namespace='{self.workload_namespace}'"""
            cursor.execute(update_query)
            conn.commit()
        finally:
            conn.close()

    def display_toggleable_table(self):
        # Fetch data from the database
        data = self.fetch_data()
        # Display the data as a custom table with checkboxes
        for index, row in data.iterrows():
            workload_name, enabled = index, row['enabled']
            checkbox_state = st.checkbox(f"{workload_name} Auto Managed by Placeless", value=bool(enabled),
                                         key=f"checkbox_{workload_name}")
            # If the checkbox state is different from the current 'enabled' status, update the database
            if checkbox_state != enabled:
                self.update_status(workload_name, int(checkbox_state))
