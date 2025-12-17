from shiny import App, render, ui, reactive
from pysradb import SRAweb
import pandas as pd
import os

db = SRAweb()

app_ui = ui.page_fluid(
    ui.panel_title("SRA Metadata Filter & Exporter"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.h4("1. Fetch Data"),
            ui.input_text("project_id", "NCBI Project ID", placeholder="e.g., SRP098789"),
            ui.input_action_button("fetch", "Fetch Metadata", class_="btn-primary w-100"),
            ui.hr(),
            ui.h4("2. Filter Rows"),
            ui.output_ui("filter_controls"),
            ui.hr(),
            ui.h4("3. Export"),
            ui.input_text("download_dir", "Save Directory", value=os.getcwd()),
            ui.input_action_button("save", "Save Filtered CSV", class_="btn-success w-100"),
            ui.div(ui.output_text("status_msg"), style="margin-top: 10px;")
        ),
        ui.card(
            ui.card_header("Filtered Results Preview"),
            ui.output_text("row_count"),
            ui.output_table("metadata_table")
        )
    )
)

def server(input, output, session):
    full_df = reactive.Value(pd.DataFrame())
    
    # 1. Fetching logic
    @reactive.Effect
    @reactive.event(input.fetch)
    def fetch_data():
        sra_id = input.project_id().strip()
        if not sra_id: return
        try:
            df = db.sra_metadata(sra_id, detailed=True)
            full_df.set(df)
        except Exception as e:
            full_df.set(pd.DataFrame({"Error": [str(e)]}))

    # 2. Dynamic UI: Create a dropdown for every column
    @output
    @render.ui
    def filter_controls():
        df = full_df()
        if df.empty or "Error" in df.columns:
            return ui.p("No data loaded yet.")
        
        controls = []
        for col in df.columns:
            # Get unique values for the dropdown
            unique_vals = sorted(df[col].dropna().unique().astype(str).tolist())
            controls.append(
                ui.input_selectize(
                    f"filter_{col}", 
                    f"Filter {col}:", 
                    choices=["All"] + unique_vals, 
                    multiple=True,
                    options={"placeholder": "Select items..."}
                )
            )
        return ui.div(*controls, style="max-height: 500px; overflow-y: auto; padding: 5px;")

    # 3. Reactive Filtering Logic
    @reactive.Calc
    def filtered_data():
        df = full_df()
        if df.empty or "Error" in df.columns:
            return df
        
        filtered_df = df.copy()
        for col in df.columns:
            # Access the dynamically created input
            selected_vals = getattr(input, f"filter_{col}")()
            if selected_vals and "All" not in selected_vals:
                # Convert column to string for consistent comparison
                filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_vals)]
        
        return filtered_df

    # 4. Save Logic
    @reactive.Effect
    @reactive.event(input.save)
    def save_data():
        df = filtered_data()
        if not df.empty:
            save_path = input.download_dir().strip()
            if not os.path.exists(save_path): os.makedirs(save_path)
            
            file_name = f"{input.project_id()}_filtered.csv"
            df.to_csv(os.path.join(save_path, file_name), index=False)

    @render.text
    def row_count():
        df = filtered_data()
        return f"Showing {len(df)} rows"

    @render.table
    def metadata_table():
        return filtered_data().head(20)

    @render.text
    def status_msg():
        if "Error" in full_df().columns:
            return "❌ Error fetching ID."
        return "Ready."

app = App(app_ui, server)
