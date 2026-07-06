import os
import re
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import MaxNLocator
import matplotlib.colors as mcolors 
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") 

engine_dfsql = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}",
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True
)

# Initialize session state variable to track whether Tab 2 and Tab 3 are activated
if 'tab2_activated' not in st.session_state:
    st.session_state.tab2_activated = False
# if 'tab3_activated' not in st.session_state:
#     st.session_state.tab3_activated = False
if "visibility" not in st.session_state:
    st.session_state.visibility = "visible"
    st.session_state.disabled = False
    st.session_state.placeholder = 'Type your folder path like C:\\\\Users\\Name\\\\...'
if "code_run" not in st.session_state:
    st.session_state.code_run = False
if "transposed_results" not in st.session_state:
    st.session_state.transposed_results = None

def transposed_function(uploaded_files):

    transposed_dfs = []
    processed_dfs = []

    for uploaded_file in uploaded_files:

        try:

            # First read to find the header row
            uploaded_file.seek(0)
            df_init = pd.read_excel(uploaded_file, header=None)

            header_row = df_init[
                df_init.apply(
                    lambda row: row.astype(str).str.contains("NPM").any(),
                    axis=1
                )
            ].index[0]

            # Reset the file pointer before reading again
            uploaded_file.seek(0)
            df_process_1 = pd.read_excel(uploaded_file, header=header_row)

            values_from_C = df_init.iloc[0:3, 2].values

            mata_kuliah = values_from_C[0] if len(values_from_C) > 0 else None

            match = re.match(r'([A-Za-z\s]+)\s\(([^)]+)\)', mata_kuliah) if mata_kuliah else None

            mata_kuliah = match.group(1).strip()
            kode_mata_kuliah = match.group(2).strip()

            dosen_pengampu = values_from_C[1] if len(values_from_C) > 1 else None

            kode_kelas_full = values_from_C[2].split('/')[0] if len(values_from_C) > 2 else None
            kluster = values_from_C[2].split('/')[2] if len(values_from_C) > 2 else None

            match = re.search(
                r"(?:Kls-)?(\d{3})-([A-Za-z]+\d+)-\d+",
                kode_kelas_full,
                re.IGNORECASE
            )

            if match:
                kode_prodi = match.group(1)
                kode_kelas = match.group(2)
            else:
                kode_prodi = None
                kode_kelas = None

            df_process_1['Mata Kuliah'] = mata_kuliah
            df_process_1['Kode'] = kode_mata_kuliah
            df_process_1['Dosen Pengampu'] = dosen_pengampu
            df_process_1['Kode Prodi'] = kode_prodi
            df_process_1['Kode Kelas'] = kode_kelas
            df_process_1['Kluster'] = kluster

            columns = [
                'Mata Kuliah',
                'Kode',
                'Dosen Pengampu',
                'Kode Prodi',
                'Kode Kelas',
                'Kluster'
            ] + [
                col for col in df_process_1.columns
                if col not in [
                    'Mata Kuliah',
                    'Kode',
                    'Dosen Pengampu',
                    'Kode Prodi',
                    'Kode Kelas',
                    'Kluster'
                ]
            ]

            df_process_1 = df_process_1[columns]
            df_process_1 = df_process_1.drop(columns=['No'])
            df_process_1.columns = df_process_1.columns.str.strip()

            processed_dfs.append(df_process_1)

            start_col = 'NPM'
            end_col = 'Nilai Akhri'

            if start_col in df_process_1.columns and end_col in df_process_1.columns:
                start_idx = df_process_1.columns.get_loc(start_col)
                end_idx = df_process_1.columns.get_loc(end_col)
                total_prs_idx = df_process_1.columns.get_loc('Total PRS')
                filtered_df1 = df_process_1.iloc[:, [start_idx, start_idx + 1] + list(range(total_prs_idx + 1, end_idx))]
                filtered_df1 = filtered_df1.loc[:, (filtered_df1 != 0).any(axis=0)]
                el_columns = [f"EL{i+1}" for i in range(filtered_df1.shape[1] - 2)]
                filtered_df1.columns = ['NPM', 'Nama'] + el_columns
                transposed_df1 = filtered_df1.melt(id_vars=['NPM', 'Nama'], var_name='Category', value_name='Value')
                transposed_dfs.append(transposed_df1)
            else:
                print(f"Required columns not found in {uploaded_file.name}")

        except Exception as e:
            print(f"Error processing file '{uploaded_file.name}': {e}")

    if transposed_dfs:
        merged_transposed_df = pd.concat(transposed_dfs, ignore_index=True)
        merged_transposed_df = merged_transposed_df.sort_values(by='Category', ascending=True).reset_index(drop=True)
    else:
        merged_transposed_df = pd.DataFrame()

    if processed_dfs:
        merged_processed_dfs = pd.concat(processed_dfs, ignore_index=True)
    else:
        merged_processed_dfs = pd.DataFrame()

    return merged_processed_dfs, merged_transposed_df

def categorize(CPL_value):
    if CPL_value > 75:
        return 'Excellent'
    elif 60 <= CPL_value <= 75:
        return 'Good'
    elif 50 <= CPL_value < 60:
        return 'Poor'
    else:
        return 'Fail'

def calculate_percentage(df, cpl_columns):
    result = {}
    total_count = len(df)
    for category in categories_criteria:
        category_count = len(df[df[cpl_columns] == category])
        result[category] = round((category_count / total_count) * 100, 0) # Calculate percentage
    return result


# Create tabs using st.tabs()
tabs = st.tabs(["📊 CPMK Tabulation & Evaluation", "📈 CPL Tabulation & Evaluation", "👑 CPL Achievement Report"])

# --------------------------
# Tab 1: Password and Button
# --------------------------
with tabs[0]: 
    st.subheader("📘 Lecturer Dashboard")

    st.info("""
    This dashboard helps lecturers monitor and evaluate Capaian Pembelajaran Mata Kuliah (CPMK) achievement to support Continuous Quality Improvement (CQI).**
    """)

    with st.expander("❓ What questions can this dashboard answer?"):

        st.markdown("""
    - Have students successfully achieved each **Capaian Pembelajaran Mata Kuliah (CPMK)**?
    - Which CPMKs have met or failed to meet the **60-point achievement threshold**?
    - How does student performance compare across different **classes** of the same course?
    - Which CPMKs require improvement in the next course offering?
    - Are the current assessment methods effectively measuring the intended learning outcomes?
    """)

    st.write("### 📊 CPMK Tabulation & Evaluation")
    # Prompt the user to enter the key/password
    valid_members = st.secrets["MEMBERS"]
    user_key = st.text_input("🔐 Please type (or paste) your membership unique key, then press Enter:")
    # Define the correct password/key (you can change it as needed)

    # Check if the entered key is correct
    if user_key in valid_members:
        st.write("Congrats! Your unique key is good to go! 🎉🥰")

        uploaded_files = st.file_uploader(
            "1️⃣ Upload one or more Student Grade Excel files",
            type=["xlsx"],
            accept_multiple_files=True
        )

        if st.button("Run the Code!"):

            st.session_state.code_run = True

            # Clear previous result
            st.session_state.transposed_results = None

            if uploaded_files:

                st.session_state.transposed_results = transposed_function(uploaded_files)

            else:
                st.error("Please upload at least one Excel file.")

        if st.session_state.code_run:
            if st.session_state.transposed_results is not None:
                merged_processed_dfs, merged_transposed_df = st.session_state.transposed_results

            if uploaded_files:
                uploaded_file2 = st.file_uploader("2️⃣ Upload your CPMK Excel file", type="xlsx", key="file2")
                if uploaded_file2 is not None:
                    df2 = pd.read_excel(uploaded_file2, engine='openpyxl')
                    df2 = df2.fillna(0)

                    # Ambil kolom CPMK dari df2
                    cpmk_columns = [col for col in df2.columns if str(col).strip().upper().startswith('CPMK')]
                    num_cpmk_columns = len(cpmk_columns)

                    # Hitung total CPMK (penyebut untuk normalisasi)
                    cpmk_sums = df2[cpmk_columns].sum()

                    if 'merged_transposed_df' in locals():
                        # Tambah kolom CPMK ke merged_transposed_df jika belum ada
                        for cpmk_column in cpmk_columns:
                            if cpmk_column not in merged_transposed_df.columns:
                                merged_transposed_df[cpmk_column] = None

                        # Isi nilai CPMK berdasarkan kategori
                        categories = merged_transposed_df['Category'].unique().tolist()
                        for category_index, category in enumerate(categories):
                            filtered_df = merged_transposed_df[merged_transposed_df['Category'] == category].copy()

                            if category_index < len(df2):
                                for cpmk_column in cpmk_columns:
                                    if cpmk_column in df2.columns:
                                        cpmk_value = df2.iloc[category_index][cpmk_column]
                                        filtered_df[cpmk_column] = cpmk_value

                                merged_transposed_df.update(filtered_df)
                            else:
                                print(f"Info: Index {category_index} untuk kategori '{category}' tidak ditemukan di file CPMK.")

                        # Hitung multiplied column
                        for cpmk_column in cpmk_columns:
                            merged_transposed_df[cpmk_column + '_multiplied'] = (
                                merged_transposed_df['Value'] * merged_transposed_df[cpmk_column]
                            )

                        # Hitung nilai akhir per mahasiswa
                        df_fix = merged_transposed_df[['NPM', 'Nama']].drop_duplicates().copy()

                        for cpmk_column in cpmk_columns:
                            df_fix[cpmk_column] = None

                        for npm in df_fix['NPM']:
                            student_df = merged_transposed_df[merged_transposed_df['NPM'] == npm]

                            for cpmk_column in cpmk_columns:
                                vertical_sum = student_df[cpmk_column + '_multiplied'].sum()
                                denominator = cpmk_sums.get(cpmk_column, 1)
                                normalized_value = (vertical_sum / denominator).round(2)
                                df_fix.loc[df_fix['NPM'] == npm, cpmk_column] = normalized_value

                        df_fix = merged_transposed_df[['NPM', 'Nama']].drop_duplicates().copy()

                        for cpmk_column in cpmk_columns:
                            df_fix[cpmk_column] = None  # CPMK3, CPMK4, dst.

                        for npm in df_fix['NPM']:
                            student_df = merged_transposed_df[merged_transposed_df['NPM'] == npm]

                            for cpmk_column in cpmk_columns:
                                cpmk_multiplied_column_name = cpmk_column + '_multiplied'  # ex: CPMK3_multiplied
                                if cpmk_multiplied_column_name in student_df.columns:
                                    vertical_sum = student_df[cpmk_multiplied_column_name].sum()
                                    denominator = cpmk_sums.get(cpmk_column, 1)
                                    normalized_value = (vertical_sum / denominator).round(2)
                                    df_fix.loc[df_fix['NPM'] == npm, cpmk_column] = normalized_value

                        cols_to_lookup = ['NPM', 'Mata Kuliah', 'Kode', 'Dosen Pengampu', 'Kode Prodi', 'Kode Kelas', 'Kluster']

                        if 'NPM' in df_fix.columns and 'NPM' in merged_processed_dfs.columns:
                            df_merged = pd.merge(df_fix, merged_processed_dfs[cols_to_lookup], on='NPM', how='left')
                            new_column_order = ['Mata Kuliah', 'Kode', 'Dosen Pengampu', 'Kode Prodi', 'Kode Kelas', 'Kluster'] + [col for col in df_merged.columns if col not in ['Mata Kuliah', 'Kode', 'Dosen Pengampu', 'Kode Prodi', 'Kode Kelas', 'Kluster']]
                            df_merged = df_merged[new_column_order]
                            # st.write(df_merged)
                        else:
                            st.error("The 'NPM' column is missing in one of the DataFrames.")   

                        # Dropdown to select whether to see all classes or an individual class
                        view_option = st.selectbox(
                            "3️⃣ Choose view option:",
                            ["All Classes", "Individual Class"]
                        )

                        st.session_state.tab2_activated = True

                        # Dynamically filter and display data based on the selection
                        if view_option == "All Classes":
                            # Calculate average for each CPMK column per class
                            cpmk_columns = [col for col in df_merged.columns if "CPMK" in col]
                            averages_mata_kuliah = df_merged.groupby('Mata Kuliah')[cpmk_columns].mean().reset_index()
                            # Round the average values to 2 decimal places
                            averages_mata_kuliah[cpmk_columns] = averages_mata_kuliah[cpmk_columns].round(2)
                            # print(averages_mata_kuliah)

                            # Define the CPMK columns to plot
                            cpmk_cols = [col for col in df_merged.columns if 'CPMK' in col]

                            # Get the values for the first (and only) row
                            values = averages_mata_kuliah.loc[0, cpmk_cols].values

                            # Ensure all values are numeric and handle NaN values
                            values = pd.to_numeric(values, errors='coerce')  # Convert to numeric, invalid parsing will result in NaN
                            values = np.nan_to_num(values, nan=0)  # Replace NaN with 0 (or use another strategy if needed)

                            # Split the data into two groups based on threshold (60)
                            threshold = 60
                            below_threshold = values[values < threshold]
                            above_threshold = values[values >= threshold]

                            # Ensure both groups are non-empty
                            if below_threshold.size > 0:
                                cmap_low = mpl.colors.LinearSegmentedColormap.from_list("low_map", ["#ff5a5f", "#c81d25"], N=256)
                                norm_low = mpl.colors.Normalize(vmin=below_threshold.min(), vmax=threshold)  # Normalizes values below threshold
                            else:
                                cmap_low = mpl.colors.LinearSegmentedColormap.from_list("low_map", ["#D3D3D3", "#D3D3D3"], N=256)  # Grey color if empty
                                norm_low = mpl.colors.Normalize(vmin=0, vmax=1)

                            if above_threshold.size > 0:
                                cmap_high = mpl.colors.LinearSegmentedColormap.from_list("high_map", ["#bbdefb", "#2196f3"], N=256)
                                norm_high = mpl.colors.Normalize(vmin=threshold, vmax=above_threshold.max())  # Normalizes values above threshold
                            else:
                                cmap_high = mpl.colors.LinearSegmentedColormap.from_list("high_map", ["#D3D3D3", "#D3D3D3"], N=256)  # Grey color if empty
                                norm_high = mpl.colors.Normalize(vmin=0, vmax=1)

                            # Create the bar chart
                            fig, ax = plt.subplots(figsize=(13.33,7.5), dpi=96)

                            # Plot bars using the custom colormap: each bar gets a color based on its height
                            if below_threshold.size > 0:
                                bars_low = ax.bar(cpmk_cols[:len(below_threshold)], below_threshold, width=0.6, 
                                                color=cmap_low(norm_low(below_threshold)), label='Below Threshold', zorder=2)
                            if above_threshold.size > 0:
                                bars_high = ax.bar(cpmk_cols[len(below_threshold):], above_threshold, width=0.6, 
                                                color=cmap_high(norm_high(above_threshold)), label='Above Threshold', zorder=2)

                            # Add horizontal line at the threshold (60)
                            ax.axhline(y=threshold, color='red', linewidth=1, linestyle='--', label='Threshold (60)')

                            # Create the grid 
                            ax.grid(which="major", axis='x', color='#DAD8D7', alpha=0.5, zorder=1)
                            ax.grid(which="major", axis='y', color='#DAD8D7', alpha=0.5, zorder=1)

                            # Add label on top of each bar for bars_low
                            if below_threshold.size > 0:
                                for bar in bars_low:
                                    height = bar.get_height()
                                    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,  # Positioning the label
                                            f'{height:.2f}',  # Displaying the height value (rounded to 2 decimal places)
                                            ha='center', va='bottom', fontweight='bold')  # Adjusting label position

                            # Add label on top of each bar for bars_high
                            if above_threshold.size > 0:
                                for bar in bars_high:
                                    height = bar.get_height()
                                    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,  # Positioning the label
                                            f'{height:.2f}',  # Displaying the height value (rounded to 2 decimal places)
                                            ha='center', va='bottom', fontweight='bold')  # Adjusting label position

                            # Set labels and title
                            ax.set_ylabel('Average Values', fontsize=12, labelpad=10)
                            ax.yaxis.set_label_position("left")
                            ax.yaxis.set_major_formatter(lambda s, i: f'{s:,.0f}')
                            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                            ax.yaxis.set_tick_params(pad=2, labeltop=False, labelbottom=True, bottom=False, labelsize=12)

                            # Remove the spines
                            ax.spines[['top', 'left', 'bottom']].set_visible(False)
                            # Make the right spine thicker
                            ax.spines['right'].set_linewidth(1)
                            ax.spines['right'].set_edgecolor('#2196f3')

                            # Add in red line and rectangle on top
                            ax.plot([0.12, .9], [.98, .98], transform=fig.transFigure, clip_on=False, color='#2196f3', linewidth=1)
                            ax.add_patch(plt.Rectangle((0.12, .98), 0.15, -0.02, facecolor='#2196f3', transform=fig.transFigure, clip_on=False, linewidth=1))

                            # Add in title and subtitle
                            ax.text(x=0.12, y=.91, s=f'CPMK Averages for {averages_mata_kuliah.loc[0, "Mata Kuliah"]} ({merged_processed_dfs["Kode"].iloc[0]})', 
                                    transform=fig.transFigure, ha='left', fontsize=12, weight='bold', alpha=.8)
                            ax.text(x=0.12, y=.88, s="CPMK is Course Learning Outcomes in the Semester", 
                                    transform=fig.transFigure, ha='left', fontsize=12, alpha=.8)
                            ax.text(x=0.1, y=0.12, s="The threshold value is set at 60", 
                                    transform=fig.transFigure, ha='left', fontsize=10, alpha=.7)
                            
                            # Add legend with the specified properties
                            ax.legend(loc="best", ncol=3, bbox_to_anchor=[1, 1.10], borderaxespad=0, frameon=False, fontsize=10)

                            # Adjust the margins around the plot area
                            plt.subplots_adjust(left=None, bottom=0.2, right=None, top=0.85, wspace=None, hspace=None)

                            # Set a white background
                            fig.patch.set_facecolor('white')

                            st.pyplot(plt)


                        elif view_option == "Individual Class":
                            # Allow the user to select a specific class
                            class_selected_individual_class = st.selectbox("4️⃣ Select a class:", df_merged['Kode Kelas'].unique())

                            # Group the DataFrame by 'Kode Kelas' and calculate the mean for each CPMK column
                            cpmk_columns_per_class = [col for col in df_merged.columns if "CPMK" in col]
                            # group_by_class = df.groupby('Kode Kelas')[cpmk_columns_per_class].mean().reset_index()
                            group_by_class = df_merged.groupby('Kode Kelas').agg(
                                {'Mata Kuliah': 'first',  # Take the first value of Mata Kuliah for each Kode Kelas group
                                **{col: 'mean' for col in cpmk_columns_per_class}}).reset_index()

                            # Round the average values to 2 decimal places
                            group_by_class[cpmk_columns_per_class] = group_by_class[cpmk_columns_per_class].round(2) 

                            # Filter the DataFrame to only show the selected class
                            selected_class_data = group_by_class[group_by_class['Kode Kelas'] == class_selected_individual_class]

                            # Ensure the values are numeric and handle NaN values
                            selected_class_data = selected_class_data[cpmk_columns_per_class].values.flatten()
                            selected_class_data = pd.to_numeric(selected_class_data, errors='coerce')
                            selected_class_data = np.nan_to_num(selected_class_data, nan=0)

                            # Split the data into two groups based on threshold (60)
                            threshold = 60
                            below_threshold = selected_class_data[selected_class_data < threshold]
                            above_threshold = selected_class_data[selected_class_data >= threshold]

                            # Ensure both groups are non-empty
                            if below_threshold.size > 0:
                                cmap_low = mpl.colors.LinearSegmentedColormap.from_list("low_map", ["#ff5a5f", "#c81d25"], N=256)
                                norm_low = mpl.colors.Normalize(vmin=below_threshold.min(), vmax=threshold)  # Normalizes values below threshold
                            else:
                                cmap_low = mpl.colors.LinearSegmentedColormap.from_list("low_map", ["#D3D3D3", "#D3D3D3"], N=256)  # Grey color if empty
                                norm_low = mpl.colors.Normalize(vmin=0, vmax=1)

                            if above_threshold.size > 0:
                                cmap_high = mpl.colors.LinearSegmentedColormap.from_list("high_map", ["#bbdefb", "#2196f3"], N=256)
                                norm_high = mpl.colors.Normalize(vmin=threshold, vmax=above_threshold.max())  # Normalizes values above threshold
                            else:
                                cmap_high = mpl.colors.LinearSegmentedColormap.from_list("high_map", ["#D3D3D3", "#D3D3D3"], N=256)  # Grey color if empty
                                norm_high = mpl.colors.Normalize(vmin=0, vmax=1)

                            # Create the bar chart
                            fig, ax = plt.subplots(figsize=(13.33,7.5), dpi=96)

                            # Define the CPMK columns to plot
                            cpmk_cols_class = [col for col in df_merged.columns if 'CPMK' in col]

                            # Plot bars using the custom colormap: each bar gets a color based on its height
                            if below_threshold.size > 0:
                                bars_low = ax.bar(cpmk_cols_class[:len(below_threshold)], below_threshold, width=0.6, 
                                                color=cmap_low(norm_low(below_threshold)), label='Below Threshold', zorder=2)
                            if above_threshold.size > 0:
                                bars_high = ax.bar(cpmk_cols_class[len(below_threshold):], above_threshold, width=0.6, 
                                                color=cmap_high(norm_high(above_threshold)), label='Above Threshold', zorder=2)

                            # Add horizontal line at the threshold (60)
                            ax.axhline(y=threshold, color='red', linewidth=1, linestyle='--', label='Threshold (60)')

                            # Create the grid 
                            ax.grid(which="major", axis='x', color='#DAD8D7', alpha=0.5, zorder=1)
                            ax.grid(which="major", axis='y', color='#DAD8D7', alpha=0.5, zorder=1)

                            # Add label on top of each bar for bars_low
                            if below_threshold.size > 0:
                                for bar in bars_low:
                                    height = bar.get_height()
                                    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,  # Positioning the label
                                            f'{height:.2f}',  # Displaying the height value (rounded to 2 decimal places)
                                            ha='center', va='bottom', fontweight='bold')  # Adjusting label position

                            # Add label on top of each bar for bars_high
                            if above_threshold.size > 0:
                                for bar in bars_high:
                                    height = bar.get_height()
                                    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,  # Positioning the label
                                            f'{height:.2f}',  # Displaying the height value (rounded to 2 decimal places)
                                            ha='center', va='bottom', fontweight='bold')  # Adjusting label position

                            # Set labels and title
                            ax.set_ylabel('Average Values', fontsize=12, labelpad=10)
                            ax.yaxis.set_label_position("left")
                            ax.yaxis.set_major_formatter(lambda s, i: f'{s:,.0f}')
                            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                            ax.yaxis.set_tick_params(pad=2, labeltop=False, labelbottom=True, bottom=False, labelsize=12)

                            # Remove the spines
                            ax.spines[['top', 'left', 'bottom']].set_visible(False)
                            # Make the right spine thicker
                            ax.spines['right'].set_linewidth(1)
                            ax.spines['right'].set_edgecolor('#2196f3')

                            # Add in red line and rectangle on top
                            ax.plot([0.12, .9], [.98, .98], transform=fig.transFigure, clip_on=False, color='#2196f3', linewidth=1)
                            ax.add_patch(plt.Rectangle((0.12, .98), 0.15, -0.02, facecolor='#2196f3', transform=fig.transFigure, clip_on=False, linewidth=1))

                            # Add in title and subtitle
                            ax.text(x=0.12, y=.91, s=f'CPMK Averages for {group_by_class.loc[0, "Mata Kuliah"]} ({merged_processed_dfs["Kode"].iloc[0]})', 
                                    transform=fig.transFigure, ha='left', fontsize=12, weight='bold', alpha=.8)
                            ax.text(x=0.12, y=.88, s="CPMK is Course Learning Outcomes in the Semester", 
                                    transform=fig.transFigure, ha='left', fontsize=12, alpha=.8)
                            ax.text(x=0.1, y=0.12, s="The threshold value is set at 60", 
                                    transform=fig.transFigure, ha='left', fontsize=10, alpha=.7)
                            
                            # Add legend with the specified properties
                            ax.legend(loc="best", ncol=3, bbox_to_anchor=[1, 1.10], borderaxespad=0, frameon=False, fontsize=10)

                            # Adjust the margins around the plot area
                            plt.subplots_adjust(left=None, bottom=0.2, right=None, top=0.85, wspace=None, hspace=None)

                            # Set a white background
                            fig.patch.set_facecolor('white')

                            st.pyplot(plt)          
        
                        if st.button("💾 Save Student CPMK Data"):

                            try:

                                df_sql = df_merged.copy()

                                # ======================================
                                # Extract Academic Year & Semester
                                # ======================================

                                cluster = str(df_sql["Kluster"].iloc[0])

                                parts = cluster.split()

                                df_sql["Academic Year"] = parts[0] if len(parts) > 0 else ""
                                df_sql["Semester"] = parts[1] if len(parts) > 1 else ""

                                # ======================================
                                # Rename Columns
                                # ======================================

                                df_sql.rename(columns={
                                    "Mata Kuliah": "course_name",
                                    "Kode": "course_code",
                                    "Dosen Pengampu": "lecturer",
                                    "Kode Prodi": "program_code",
                                    "Kode Kelas": "class_code",
                                    "Kluster": "cluster",
                                    "Academic Year": "academic_year",
                                    "Semester": "semester",
                                    "NPM": "student_id",
                                    "Nama": "student_name",
                                    "CPMK1": "cpmk1",
                                    "CPMK2": "cpmk2",
                                    "CPMK3": "cpmk3",
                                    "CPMK4": "cpmk4",
                                    "CPMK5": "cpmk5",
                                    "CPMK6": "cpmk6",
                                    "CPMK7": "cpmk7",
                                    "CPMK8": "cpmk8",
                                    "CPMK9": "cpmk9",
                                    "CPMK10": "cpmk10",
                                }, inplace=True)

                                rename_dict = {}

                                for col in df_sql.columns:

                                    if str(col).upper().startswith("CPMK"):

                                        number = re.search(r"\d+", str(col)).group()

                                        rename_dict[col] = f"cpmk{number}"

                                df_sql.rename(columns=rename_dict, inplace=True)


                                # ======================================
                                # Reorder Columns
                                # ======================================

                                desired_columns = [
                                    "course_name",
                                    "course_code",
                                    "lecturer",
                                    "program_code",
                                    "class_code",
                                    "cluster",
                                    "academic_year",
                                    "semester",
                                    "student_id",
                                    "student_name"
                                ]

                                # Add CPMK columns automatically
                                cpmk_cols = sorted(
                                    [c for c in df_sql.columns if c.lower().startswith("cpmk")],
                                    key=lambda x: int(x.replace("cpmk", ""))
                                )

                                desired_columns.extend(cpmk_cols)

                                df_sql = df_sql[desired_columns]

                                # ======================================
                                # Save to SQL
                                # ======================================

                                with engine_dfsql.begin() as conn:

                                    delete_result = conn.execute(
                                        text("""
                                            DELETE FROM student_cpmk_result
                                            WHERE course_code = :course_code
                                            AND academic_year = :academic_year
                                            AND semester = :semester
                                            AND class_code = :class_code
                                        """),
                                        {
                                            "course_code": df_sql["course_code"].iloc[0],
                                            "academic_year": df_sql["academic_year"].iloc[0],
                                            "semester": df_sql["semester"].iloc[0],
                                            "class_code": df_sql["class_code"].iloc[0]
                                        }
                                    )

                                    deleted_rows = delete_result.rowcount

                                    df_sql.to_sql(
                                        "student_cpmk_result",
                                        con=conn,
                                        if_exists="append",
                                        index=False
                                    )

                                if deleted_rows == 0:
                                    st.success("✅ Student CPMK data has been uploaded successfully!")
                                else:
                                    st.success("✅ Existing Student CPMK data has been updated successfully!")

                            except Exception as e:

                                st.error(f"❌ Database Error:\n{e}")
        
    else:
        if user_key != "":
            st.write("Oops! That key doesn’t seem to work. Give it another shot! 😊")

# --------------------------
# Tab 2: Content
# --------------------------
with tabs[1]:
    if st.session_state.tab2_activated:
        st.subheader("📗 Course Evaluation Dashboard")

        st.info("""
        **This dashboard evaluates how each course contributes to the achievement of Capaian Pembelajaran Lulusan (CPL) through CPMK-CPL mapping.**
        """)

        with st.expander("❓ What questions can this dashboard answer?"):
            st.markdown("""
        - Which **Capaian Pembelajaran Lulusan (CPLs)** are addressed by this course?
        - How strongly does each **CPMK contribute** to the intended CPLs?
        - What percentage of students achieved **Excellent, Good, Poor, and Fail** for each addressed CPL?
        - Are there any CPLs receiving **insufficient contribution** from this course?
        - Does the current CPMK-CPL mapping support the intended graduate competencies?
        """)
                    
        st.write("### 📈 CPL Tabulation & Evaluation")
              
        st.write("✅ Let's match each CPMK with the list of CPL outcomes from the list below! 👀")
    
        df_merged_CPMK_CPL = df_merged.copy()

        cpl_columns = ["CPL1", "CPL2", "CPL3", "CPL4", "CPL5", "CPL6", "CPL7", "CPL8", "CPL9", "CPL10", "CPL11", "CPL12", "CPL13", "CPL14"]
        categories_criteria = ['Excellent', 'Good', 'Poor', 'Fail']

        cpmk_selections = {}

        for col in cpmk_columns:
            cpmk_selections[col] = st.multiselect(f"{col}", cpl_columns, placeholder=f"Choose the CPL of {col}")
        # st.write(cpmk_selections) 

        # Collect only selected CPLs (preserves order and removes duplicates)
        used_cpls = list(dict.fromkeys(
            cpl
            for selections in cpmk_selections.values()
            for cpl in selections
        ))

        used_cpls = sorted(
            used_cpls,
            key=lambda x: int(re.search(r"\d+", x).group())
        )

        if len(used_cpls) == 0:
            st.warning("Please select at least one CPL for a CPMK.")
            st.stop()

        for col in cpl_columns:
            df_merged_CPMK_CPL[col] = 0

        for cpmk, selections in cpmk_selections.items():
            for selection in selections:
                # columns_to_update = [col for col in cpl_columns if selection in col]
                columns_to_update = [selection]

                for col in columns_to_update:
                    df_merged_CPMK_CPL[col] = df_merged_CPMK_CPL.apply(lambda row: categorize(row[cpmk]) if row[cpmk] is not np.nan else 'Fail', axis=1) 

            # Create a new dataframe to hold the result
            result_data = []

            # Iterate over each unique "Mata Kuliah" (course) and calculate percentage for each CPL column
            for mata_kuliah in df_merged_CPMK_CPL['Mata Kuliah'].unique():
                for kriteria in categories_criteria:  # Iterate through categories Excellent, Good, Poor, Fail
                    row = {'Mata Kuliah': mata_kuliah, 'Kriteria': kriteria}
                    
                    # For each CPL column, calculate percentage
                    for cpl_column in cpl_columns:
                        # Calculate percentage for the current CPL column and category
                        percentage_data = calculate_percentage(df_merged_CPMK_CPL[df_merged_CPMK_CPL['Mata Kuliah'] == mata_kuliah], cpl_column)
                        row[cpl_column] = percentage_data.get(kriteria, 0)  # Get the percentage for the current category
                    
                    result_data.append(row)

        # Convert the result_data to a DataFrame
        final_df = pd.DataFrame(result_data)
        cpl_columns_clean = [col for col in final_df.columns if col.startswith('CPL')]
        final_df.rename(columns={col: col.split('_')[0] for col in cpl_columns_clean}, inplace=True)
        st.markdown(f'<h4 style="font-size: 18px; font-weight: bold;">Table CPMK x CPL for {merged_processed_dfs["Mata Kuliah"].iloc[0]} ({merged_processed_dfs["Kode"].iloc[0]})</h4>', unsafe_allow_html=True)
        display_df = final_df[["Mata Kuliah", "Kriteria"] + used_cpls]
        # st.write(display_df)

        # Define categories
        category_names = ['Excellent', 'Good', 'Poor', 'Fail']
        category_colors = ['#2196f3', '#43adfe', '#fa9595', '#f32121']   # Green for Excellent, Red for Fail

        # Create a function to plot the distribution
        def plot_distribution(df, category_names, category_colors, used_cpls):
            # Prepare the data: sum the values for each category
            results = {}
            # for cpl in df.columns[2:]:  # Skip 'Mata Kuliah' and 'Kriteria' columns
            for cpl in used_cpls:
                counts = df.groupby('Kriteria')[cpl].sum().reindex(category_names, fill_value=0)
                results[cpl] = counts.tolist()

            # Convert results to a format for plotting
            labels = list(results.keys())
            data = np.array(list(results.values()))

            data_cum = data.cumsum(axis=1)

            fig, ax = plt.subplots(figsize=(9, 5))
            ax.invert_yaxis()
            ax.xaxis.set_visible(False)
            ax.set_xlim(0, np.sum(data, axis=1).max())

            for i, (colname, color) in enumerate(zip(category_names, category_colors)):
                widths = data[:, i]
                starts = data_cum[:, i] - widths
                rects = ax.barh(labels, widths, left=starts, height=0.5, label=colname, color=color)

                r, g, b = mcolors.hex2color(color)  # Convert hex to RGB
                text_color = 'white' if (r * g * b) < 0.5 else 'black'
                ax.bar_label(rects, label_type='center', color=text_color)

                # Remove the border around the plot
                for spine in ax.spines.values():
                    spine.set_visible(False)

            # Add in red line and rectangle on top
            ax.plot([0.075, 0.91], [.98, .98], transform=fig.transFigure, clip_on=False, color='#2196f3', linewidth=1)
            ax.add_patch(plt.Rectangle((0.075, .98), 0.15, -0.02, facecolor='#2196f3', transform=fig.transFigure, clip_on=False, linewidth=1))
  
            # Add in title and subtitle
            ax.text(x=0.075, y=0.89, s=f'CPMK x CPL for {merged_processed_dfs["Mata Kuliah"].iloc[0]} ({merged_processed_dfs["Kode"].iloc[0]}) - in Percentages', 
                    transform=fig.transFigure, ha='left', fontsize=12, weight='bold', alpha=.8)

            ax.grid(which="major", axis='x', color='#DAD8D7', alpha=0.5, zorder=1)
            ax.grid(which="major", axis='y', color='#DAD8D7', alpha=0.5, zorder=1)

            ax.legend(ncols=len(category_names), bbox_to_anchor=(0.5, -0.005), loc='upper center', fontsize='small', 
                    borderaxespad=0, frameon=False)
            
            return fig, ax

        # Call the function to plot the distribution
        plot_distribution(display_df, category_names, category_colors, used_cpls)
        st.pyplot(plt)

        # =====================================================
        # Prepare SQL DataFrame
        # =====================================================

        sql_df = final_df.copy()

        # Only add new metadata columns

        sql_df["course_code"] = merged_processed_dfs["Kode"].iloc[0]
        cluster = merged_processed_dfs["Kluster"].iloc[0]
        parts = cluster.split()
        academic_year = parts[0]
        semester = parts[1]
        sql_df["academic_year"]=academic_year
        sql_df["semester"]=semester
        kode_prodi = str(df_merged["Kode Prodi"].iloc[0]).strip()

        if kode_prodi == "081":
            program_studi = "Manajemen"
        elif kode_prodi == "082":
            program_studi = "Akuntansi"
        elif kode_prodi == "083":
            program_studi = "Perbankan Syariah"
        else:
            program_studi = "Unknown"

        sql_df["department"] = program_studi

        # Rename existing columns
        sql_df.rename(columns={
            "Mata Kuliah": "course_name",
            "Kriteria": "criteria",
            "CPL1": "cpl1",
            "CPL2": "cpl2",
            "CPL3": "cpl3",
            "CPL4": "cpl4",
            "CPL5": "cpl5",
            "CPL6": "cpl6",
            "CPL7": "cpl7",
            "CPL8": "cpl8",
            "CPL9": "cpl9",
            "CPL10": "cpl10",
            "CPL11": "cpl11",
            "CPL12": "cpl12",
            "CPL13": "cpl13",
            "CPL14": "cpl14",
        }, inplace=True)

        # Reorder columns
        sql_df = sql_df[
            [
                "department",
                "course_code",
                "course_name",
                "academic_year",
                "semester",
                "criteria",
                "cpl1",
                "cpl2",
                "cpl3",
                "cpl4",
                "cpl5",
                "cpl6",
                "cpl7",
                "cpl8",
                "cpl9",
                "cpl10",
                "cpl11",
                "cpl12",
                "cpl13",
                "cpl14",
            ]
        ]


        # Ensure CPL columns are numeric
        cpl_columns = [f"cpl{i}" for i in range(1, 15)]

        sql_df[cpl_columns] = (
            sql_df[cpl_columns]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0)
        )

        # st.subheader("📋 Preview Data to be Saved")

        # st.dataframe(
        #     sql_df,
        #     use_container_width=True
        # )

        # =====================================================
        # Save to MySQL
        # =====================================================

        if st.button("💾 Save to Database"):

            try:

                with engine_dfsql.begin() as conn:

                    delete_result = conn.execute(
                        text("""
                            DELETE FROM course_cpl_summary
                            WHERE course_code = :course_code
                            AND academic_year = :academic_year
                            AND semester = :semester
                        """),
                        {
                            "course_code": sql_df["course_code"].iloc[0],
                            "academic_year": sql_df["academic_year"].iloc[0],
                            "semester": sql_df["semester"].iloc[0]
                        }
                    )

                    deleted_rows = delete_result.rowcount

                    sql_df.to_sql(
                        "course_cpl_summary",
                        con=conn,
                        if_exists="append",
                        index=False
                    )

                if deleted_rows == 0:
                    st.success("✅ Course CPL summary has been uploaded successfully!")
                else:
                    st.success("✅ Existing Course CPL summary has been updated successfully!")

            except Exception as e:

                st.error(f"❌ Database Error:\n{e}")

    else:
        st.write("### 📈 CPL Tabulation & Evaluation is not activated yet ⛔️")

# --------------------------
# Tab 2: Content
# --------------------------
with tabs[2]:
    st.subheader("📘 Department Dashboard")

    st.info("""
    This dashboard enables evidence-based curriculum monitoring and Continuous Quality Improvement (CQI) by analyzing CPL achievement across all courses.**
    """)

    with st.expander("❓ What questions can this dashboard answer?"):

        st.markdown("""
    - Are all Program Learning Outcomes (CPLs) being achieved?
    - Which CPLs require immediate improvement?
    - Which courses contribute to each CPL?
    - Which courses have the lowest CPL achievement?
    - Which CPLs should become the priority for CQI in the next academic cycle?
    """)

    st.write("### 👑 CPL Achievement")

    st.markdown("""This dashboard summarizes the CPL achievement of all courses within the department. Write your member code, then click **Synchronize**.""")

    unique_code = st.text_input(
        "🔑 Unique Code",
        placeholder="Write your member code here..."
    )

    # ==========================================
    # Synchronize
    # ==========================================

    if st.button("🔄 Synchronize"):

        try:

            with engine_dfsql.connect() as conn:

                member_df = pd.read_sql(
                    text("""
                        SELECT *
                        FROM member_obe
                        WHERE unique_code = :code
                        AND is_active = 1
                    """),
                    conn,
                    params={"code": unique_code}
                )

                if member_df.empty:

                    st.error("❌ Invalid Unique Code.")

                else:

                    role = member_df.loc[0, "role"]
                    department = member_df.loc[0, "department_name"]
                    full_name = member_df.loc[0, "full_name"]

                    st.success(f"👋 Welcome {full_name}... Feel free to set up  to access and review your CPL report.")

                    if role == "DH":

                        course_df = pd.read_sql(
                            text("""
                                SELECT *
                                FROM course_cpl_summary
                                WHERE department = :department
                                ORDER BY academic_year DESC,
                                        semester,
                                        course_name
                            """),
                            conn,
                            params={"department": department}
                        )

                    elif role == "DE":

                        course_df = pd.read_sql(
                            text("""
                                SELECT *
                                FROM course_cpl_summary
                                ORDER BY department,
                                        academic_year DESC,
                                        semester,
                                        course_name
                            """),
                            conn
                        )

                    # ======================================
                    # Save into Session State
                    # ======================================

                    st.session_state.course_df = course_df
                    st.session_state.department = department
                    st.session_state.role = role
                    st.session_state.full_name = full_name

        except Exception as e:

            st.error(e)

    # ==========================================
    # Dashboard
    # ==========================================

    if "course_df" in st.session_state:

        course_df = st.session_state.course_df

        # ------------------------------
        # Academic Year
        # ------------------------------

        academic_years = sorted(
            course_df["academic_year"].dropna().unique(),
            reverse=True
        )

        col1, col2 = st.columns(2)

        with col1:
            selected_year = st.selectbox(
                "📅 Academic Year",
                academic_years
            )

        # ------------------------------
        # Semester
        # ------------------------------

        semester_list = sorted(
            course_df.loc[
                course_df["academic_year"] == selected_year,
                "semester"
            ].dropna().unique()
        )

        with col2:
            selected_semester = st.selectbox(
                "🎓 Semester",
                semester_list
            )

        # ------------------------------
        # Filter
        # ------------------------------

        filtered_df = course_df[
            (course_df["academic_year"] == selected_year) &
            (course_df["semester"] == selected_semester)
        ]

        # =====================================================
        # Calculate Average CPL Achievement Across Courses
        # =====================================================

        cpl_columns = [
            col for col in filtered_df.columns
            if col.lower().startswith("cpl")
        ]

        summary_tab3 = []

        for cpl in cpl_columns:

            excellent = filtered_df.loc[
                (filtered_df["criteria"] == "Excellent") &
                (filtered_df[cpl] > 0),
                cpl
            ].mean()

            good = filtered_df.loc[
                (filtered_df["criteria"] == "Good") &
                (filtered_df[cpl] > 0),
                cpl
            ].mean()

            poor = filtered_df.loc[
                (filtered_df["criteria"] == "Poor") &
                (filtered_df[cpl] > 0),
                cpl
            ].mean()

            fail = filtered_df.loc[
                (filtered_df["criteria"] == "Fail") &
                (filtered_df[cpl] > 0),
                cpl
            ].mean()

            excellent = 0 if pd.isna(excellent) else excellent
            good = 0 if pd.isna(good) else good
            poor = 0 if pd.isna(poor) else poor
            fail = 0 if pd.isna(fail) else fail

            successful = excellent + good
            unsuccessful = poor + fail

            # Skip unused CPL
            if successful + unsuccessful == 0:
                continue

            summary_tab3.append({
                "CPL": cpl.upper(),
                "Successful": round(successful),
                "Unsuccessful": round(unsuccessful)
            })

        summary_df_tab3 = pd.DataFrame(summary_tab3)

        # ==========================================
        # Sort from Highest Intervention Priority
        # ==========================================

        summary_df_tab3["CPL_Number"] = (
            summary_df_tab3["CPL"]
            .str.extract(r"(\d+)")
            .astype(int)
        )

        summary_df_tab3 = (
            summary_df_tab3
            .sort_values("CPL_Number")
            .drop(columns="CPL_Number")
            .reset_index(drop=True)
        )

        # =====================================================
        # Department CPL Achievement Plot
        # =====================================================

        category_colors = [
            "#2196f3",   # Successful
            "#f44336"    # Unsuccessful
        ]

        def plot_department_cpl(df):

            labels = df["CPL"]

            successful = df["Successful"]

            unsuccessful = df["Unsuccessful"]

            # ======================================
            # Figure
            # ======================================

            fig, ax = plt.subplots(figsize=(9, 7))

            ax.invert_yaxis()

            ax.xaxis.set_visible(False)

            ax.set_xlim(0, 100)

            # ======================================
            # Successful
            # ======================================

            bars_success = ax.barh(
                labels,
                successful,
                height=0.8,
                color=category_colors[0],
                label="Successful",
                zorder=2
            )

            # ======================================
            # Unsuccessful
            # ======================================

            bars_fail = ax.barh(
                labels,
                unsuccessful,
                left=successful,
                height=0.8,
                color=category_colors[1],
                label="Unsuccessful",
                zorder=2
            )

            # ======================================
            # Labels
            # ======================================

            for bar in bars_success:

                width = bar.get_width()

                if width >= 5:

                    ax.text(
                        width / 2,
                        bar.get_y() + bar.get_height() / 2,
                        f"{int(round(width))}",
                        ha="center",
                        va="center",
                        color="white",
                        fontsize=10,
                        fontweight="bold"
                    )

            # for bar in bars_fail:

            #     width = bar.get_width()

            #     if width >= 5:

            #         ax.text(
            #             bar.get_x() + width / 2,
            #             bar.get_y() + bar.get_height() / 2,
            #             f"{int(round(width))}",
            #             ha="center",
            #             va="center",
            #             color="white",
            #             fontsize=10,
            #             fontweight="bold"
            #         )

            # ======================================
            # Grid
            # ======================================

            ax.grid(
                which="major",
                axis="x",
                color="#DAD8D7",
                alpha=0.5,
                zorder=1
            )

            ax.grid(
                which="major",
                axis="y",
                color="#DAD8D7",
                alpha=0.5,
                zorder=1
            )

            # ======================================
            # Remove Spines
            # ======================================

            for spine in ax.spines.values():
                spine.set_visible(False)

            # ======================================
            # Top Decoration
            # ======================================

            ax.plot(
                [0.075, 0.91],
                [.98, .98],
                transform=fig.transFigure,
                clip_on=False,
                color="#2196f3",
                linewidth=1
            )

            ax.add_patch(
                plt.Rectangle(
                    (0.075, .98),
                    .15,
                    -.02,
                    transform=fig.transFigure,
                    clip_on=False,
                    facecolor="#2196f3",
                    linewidth=1
                )
            )

            # ======================================
            # Title
            # ======================================

            ax.text(
                x=0.075,
                y=0.89,
                s="CPL Achievement Report in Percentages",
                transform=fig.transFigure,
                ha="left",
                fontsize=12,
                weight="bold",
                alpha=.8
            )

            ax.text(
                x=0.075,
                y=0.855,
                s=f"{st.session_state.department} | Semester {selected_semester} {selected_year}",
                transform=fig.transFigure,
                ha="left",
                fontsize=10,
                alpha=.8
            )

            # ======================================
            # Tick Style
            # ======================================

            ax.tick_params(
                axis="y",
                labelsize=11
            )

            # ======================================
            # Legend
            # ======================================

            ax.legend(
                ncols=2,
                bbox_to_anchor=(0.5, -0.005),
                loc="upper center",
                fontsize="small",
                borderaxespad=0,
                frameon=False
            )

            # ======================================
            # Layout
            # ======================================

            plt.subplots_adjust(
                left=0.12,
                right=0.98,
                top=0.84,
                bottom=0.12
            )

            return fig


        # ======================================
        # Plot
        # ======================================

        fig = plot_department_cpl(summary_df_tab3)

        st.pyplot(fig)

        # st.dataframe(filtered_df)

        # ======================================
        # Course Contribution by CPL
        # ======================================

        available_cpl = summary_df_tab3["CPL"].tolist()

        selected_cpl = st.selectbox(
            "Select CPL to View Course Contribution",
            ["None"] + available_cpl
        )

        if selected_cpl != "None":

            selected_cpl = selected_cpl.lower()

            course_summary = []

            for course in sorted(filtered_df["course_name"].unique()):

                course_data = filtered_df[
                    filtered_df["course_name"] == course
                ]

                excellent = course_data.loc[
                    course_data["criteria"] == "Excellent",
                    selected_cpl
                ].sum()

                good = course_data.loc[
                    course_data["criteria"] == "Good",
                    selected_cpl
                ].sum()

                poor = course_data.loc[
                    course_data["criteria"] == "Poor",
                    selected_cpl
                ].sum()

                fail = course_data.loc[
                    course_data["criteria"] == "Fail",
                    selected_cpl
                ].sum()

                successful = excellent + good
                unsuccessful = poor + fail

                if successful + unsuccessful == 0:
                    continue

                course_summary.append({
                    "Course": course,
                    "Successful": round(successful),
                    "Unsuccessful": round(unsuccessful)
                })

            course_summary_df = pd.DataFrame(course_summary)

            course_summary_df = (
                course_summary_df
                .sort_values("Successful", ascending=False)
                .reset_index(drop=True)
            )

            def plot_course_cpl(df, selected_cpl):

                labels = df["Course"]

                successful = df["Successful"]

                unsuccessful = df["Unsuccessful"]

                # ======================================
                # Figure
                # ======================================

                fig, ax = plt.subplots(figsize=(9, max(5, len(labels)*0.6)))

                ax.invert_yaxis()

                ax.xaxis.set_visible(False)

                ax.set_xlim(0,100)

                # ======================================
                # Successful
                # ======================================

                bars_success = ax.barh(
                    labels,
                    successful,
                    height=0.8,
                    color="#2196f3",
                    label="Successful",
                    zorder=2
                )

                # ======================================
                # Unsuccessful
                # ======================================

                bars_fail = ax.barh(
                    labels,
                    unsuccessful,
                    left=successful,
                    height=0.8,
                    color="#f44336",
                    label="Unsuccessful",
                    zorder=2
                )

                # ======================================
                # Labels
                # ======================================

                for bar in bars_success:

                    width = bar.get_width()

                    if width >= 5:

                        ax.text(
                            width/2,
                            bar.get_y()+bar.get_height()/2,
                            f"{int(round(width))}",
                            ha="center",
                            va="center",
                            color="white",
                            fontsize=10,
                            fontweight="bold"
                        )

                # Uncomment if you also want labels in red bar

                # for bar in bars_fail:
                #
                #     width = bar.get_width()
                #
                #     if width >= 5:
                #
                #         ax.text(
                #             bar.get_x()+width/2,
                #             bar.get_y()+bar.get_height()/2,
                #             f"{int(round(width))}",
                #             ha="center",
                #             va="center",
                #             color="white",
                #             fontsize=10,
                #             fontweight="bold"
                #         )

                # ======================================
                # Grid
                # ======================================

                ax.grid(
                    which="major",
                    axis="x",
                    color="#DAD8D7",
                    alpha=.5,
                    zorder=1
                )

                ax.grid(
                    which="major",
                    axis="y",
                    color="#DAD8D7",
                    alpha=.5,
                    zorder=1
                )

                # ======================================
                # Remove Spines
                # ======================================

                for spine in ax.spines.values():
                    spine.set_visible(False)

                # ======================================
                # Top Decoration
                # ======================================

                ax.plot(
                    [0.075,0.91],
                    [.98,.98],
                    transform=fig.transFigure,
                    clip_on=False,
                    color="#2196f3",
                    linewidth=1
                )

                ax.add_patch(
                    plt.Rectangle(
                        (0.075,.98),
                        .15,
                        -.02,
                        transform=fig.transFigure,
                        clip_on=False,
                        facecolor="#2196f3",
                        linewidth=1
                    )
                )

                # ======================================
                # Title
                # ======================================

                ax.text(
                    x=0.075,
                    y=0.89,
                    s=f"Course Contribution to {selected_cpl.upper()}",
                    transform=fig.transFigure,
                    ha="left",
                    fontsize=12,
                    weight="bold",
                    alpha=.8
                )

                ax.text(
                    x=0.075,
                    y=0.855,
                    s=f"{st.session_state.department} | Semester {selected_semester} {selected_year}",
                    transform=fig.transFigure,
                    ha="left",
                    fontsize=10,
                    alpha=.8
                )

                # ======================================
                # Tick Style
                # ======================================

                ax.tick_params(
                    axis="y",
                    labelsize=10
                )

                # ======================================
                # Legend
                # ======================================

                ax.legend(
                    ncols=2,
                    bbox_to_anchor=(0.5,-0.005),
                    loc="upper center",
                    fontsize="small",
                    borderaxespad=0,
                    frameon=False
                )

                # ======================================
                # Layout
                # ======================================

                plt.subplots_adjust(
                    left=0.25,
                    right=0.98,
                    top=0.84,
                    bottom=0.12
                )

                return fig

            fig = plot_course_cpl(course_summary_df, selected_cpl)
            st.pyplot(fig)


    else:

        st.info("👆 Please enter your unique code and click **Synchronize**.")

# --------------------------
# Tab 2
# --------------------------
with tabs[1]:


    st.write("### 🚀 Melesat Generative AI")
    st.success(
        """
        Ask anything regarding OBE assessment, CPMK achievement,
        CPL achievement, student performance, or department performance.
        The AI will only answer based on the selected database table(s).
        """
    )

    # ==========================================================
    # Initialize Session State
    # ==========================================================

    if "ai_datasets" not in st.session_state:
        st.session_state.ai_datasets = {}

    if "analysis_scope" not in st.session_state:
        st.session_state.analysis_scope = None

    # ==========================================================
    # Analysis Scope
    # ==========================================================

    analysis_scope = st.selectbox(
        "🧠 AI Knowledge Source",
        [
            "None",
            "Student CPMK/CPL Performance",
            "CPMK x CPL Mapping Analysis",
            "Comprehensive Analysis"
        ],
        index=0
    )

    # ==========================================================
    # Academic Year
    # ==========================================================

    academic_years = []

    if analysis_scope != "None":

        with engine_dfsql.connect() as conn:

            if analysis_scope == "Student CPMK/CPL Performance":

                year_df = pd.read_sql(
                    text("""
                        SELECT DISTINCT academic_year
                        FROM student_cpmk_result
                        WHERE department=:department
                        ORDER BY academic_year DESC
                    """),
                    conn,
                    params={
                        "department": st.session_state.department
                    }
                )

            elif analysis_scope == "CPMK x CPL Mapping Analysis":

                year_df = pd.read_sql(
                    text("""
                        SELECT DISTINCT academic_year
                        FROM course_cpl_summary
                        WHERE department=:department
                        ORDER BY academic_year DESC
                    """),
                    conn,
                    params={
                        "department": st.session_state.department
                    }
                )

            else:

                year_df = pd.read_sql(
                    text("""
                        SELECT DISTINCT academic_year
                        FROM (
                            SELECT academic_year
                            FROM student_cpmk_result
                            WHERE department=:department

                            UNION

                            SELECT academic_year
                            FROM course_cpl_summary
                            WHERE department=:department
                        ) x
                        ORDER BY academic_year DESC
                    """),
                    conn,
                    params={
                        "department": st.session_state.department
                    }
                )

        academic_years = year_df["academic_year"].tolist()

    selected_year = st.selectbox(
        "📅 Academic Year",
        ["None"] + academic_years,
        index=0
    )

    # ==========================================================
    # Semester
    # ==========================================================

    semesters = []

    if selected_year != "None":

        with engine_dfsql.connect() as conn:

            if analysis_scope == "Student CPMK/CPL Performance":

                semester_df = pd.read_sql(
                    text("""
                        SELECT DISTINCT semester
                        FROM student_cpmk_result
                        WHERE department=:department
                        AND academic_year=:year
                        ORDER BY semester
                    """),
                    conn,
                    params={
                        "department": st.session_state.department,
                        "year": selected_year
                    }
                )

            elif analysis_scope == "CPMK x CPL Mapping Analysis":

                semester_df = pd.read_sql(
                    text("""
                        SELECT DISTINCT semester
                        FROM course_cpl_summary
                        WHERE department=:department
                        AND academic_year=:year
                        ORDER BY semester
                    """),
                    conn,
                    params={
                        "department": st.session_state.department,
                        "year": selected_year
                    }
                )

            else:

                semester_df = pd.read_sql(
                    text("""
                        SELECT DISTINCT semester
                        FROM (
                            SELECT semester
                            FROM student_cpmk_result
                            WHERE department=:department
                            AND academic_year=:year

                            UNION

                            SELECT semester
                            FROM course_cpl_summary
                            WHERE department=:department
                            AND academic_year=:year
                        ) x
                        ORDER BY semester
                    """),
                    conn,
                    params={
                        "department": st.session_state.department,
                        "year": selected_year
                    }
                )

        semesters = semester_df["semester"].tolist()

    selected_semester = st.selectbox(
        "🎓 Semester",
        ["None"] + semesters,
        index=0
    )

    # ==========================================================
    # Load Dataset
    # ==========================================================

    load_clicked = st.button(
        "🚀 Load Dataset",
        use_container_width=True,
        disabled=(
            analysis_scope == "None"
            or selected_year == "None"
            or selected_semester == "None"
        )
    )

    if load_clicked:

        datasets = {}

        with st.spinner("Preparing dataset for AI analysis..."):

            with engine_dfsql.connect() as conn:

                # ======================================================
                # Student CPMK/CPL Performance
                # ======================================================

                if analysis_scope == "Student CPMK/CPL Performance":

                    student_df = pd.read_sql(
                        text("""
                            SELECT *
                            FROM student_cpmk_result
                            WHERE department=:department
                            AND academic_year=:academic_year
                            AND semester=:semester
                            ORDER BY course_name, student_name
                        """),
                        conn,
                        params={
                            "department": st.session_state.department,
                            "academic_year": selected_year,
                            "semester": selected_semester
                        }
                    )

                    datasets["student_cpmk_result"] = student_df

                # ======================================================
                # CPMK x CPL Mapping Analysis
                # ======================================================

                elif analysis_scope == "CPMK x CPL Mapping Analysis":

                    course_df = pd.read_sql(
                        text("""
                            SELECT *
                            FROM course_cpl_summary
                            WHERE department=:department
                            AND academic_year=:academic_year
                            AND semester=:semester
                            ORDER BY course_name
                        """),
                        conn,
                        params={
                            "department": st.session_state.department,
                            "academic_year": selected_year,
                            "semester": selected_semester
                        }
                    )

                    datasets["course_cpl_summary"] = course_df

                # ======================================================
                # Comprehensive Analysis
                # ======================================================

                else:

                    student_df = pd.read_sql(
                        text("""
                            SELECT *
                            FROM student_cpmk_result
                            WHERE department=:department
                            AND academic_year=:academic_year
                            AND semester=:semester
                            ORDER BY course_name, student_name
                        """),
                        conn,
                        params={
                            "department": st.session_state.department,
                            "academic_year": selected_year,
                            "semester": selected_semester
                        }
                    )

                    course_df = pd.read_sql(
                        text("""
                            SELECT *
                            FROM course_cpl_summary
                            WHERE department=:department
                            AND academic_year=:academic_year
                            AND semester=:semester
                            ORDER BY course_name
                        """),
                        conn,
                        params={
                            "department": st.session_state.department,
                            "academic_year": selected_year,
                            "semester": selected_semester
                        }
                    )

                    datasets["student_cpmk_result"] = student_df
                    datasets["course_cpl_summary"] = course_df

        st.session_state.ai_datasets = datasets
        st.session_state.analysis_scope = analysis_scope

        st.session_state.ai_context = {
            "analysis_scope": analysis_scope,
            "department": st.session_state.department,
            "academic_year": selected_year,
            "semester": selected_semester,
            "datasets": datasets
        }

        st.success("✅ Dataset successfully loaded.")

    # ==========================================================
    # Dataset Preview
    # ==========================================================

    if "ai_datasets" in st.session_state and st.session_state.ai_datasets:

        st.divider()

        st.subheader("📋 Dataset Preview")

        for dataset_name, df in st.session_state.ai_datasets.items():

            with st.expander(
                f"{dataset_name} ({len(df):,} rows)",
                expanded=True
            ):

                col1, col2 = st.columns(2)

                col1.metric("Rows", len(df))
                col2.metric("Columns", len(df.columns))

                st.dataframe(
                    df.head(20),
                    use_container_width=True,
                    hide_index=True
                )


