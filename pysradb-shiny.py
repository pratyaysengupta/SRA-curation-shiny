from shiny import App, render, ui, reactive
from pysradb import SRAweb
import pandas as pd
import os

# Initialize the SRAweb client
db = SRAweb()

app_ui = ui.page_fluid(
    ui.panel_title("SRA Metadata Fetcher"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_text("project_id", "NCBI Project ID (e.g., SRP098789)", placeholder="SRPXXXXXX"),
            ui.input_text("download_dir", "Designated Save Location", value=os.getcwd()),
            ui.input_action_button("fetch", "Fetch & Save Data", class_="btn-primary"),
            ui.hr(),
            ui.output_text("status_msg")
        ),
        ui.card(
            ui.card_header("Project Run Metadata Preview"),
            ui.output_table("metadata_table")
        )
    )
)

def server(input, output, session):
    # Reactive value to store the dataframe
    fetched_df = reactive.Value(pd.DataFrame())

    @reactive.Effect
    @reactive.event(input.fetch)
    def fetch_data():
        sra_id = input.project_id().strip()
        save_path = input.download_dir().strip()
        
        if not sra_id:
            return

        try:
            # Fetch metadata using pysradb
            # sra_metadata fetches details for all runs in the project
            df = db.sra_metadata(sra_id)
            fetched_df.set(df)
            
            # Create directory if it doesn't exist
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            # Save to CSV
            file_name = f"{sra_id}_metadata.csv"
            full_path = os.path.join(save_path, file_name)
            df.to_csv(full_path, index=False)
            
        except Exception as e:
            print(f"Error: {e}")
            fetched_df.set(pd.DataFrame({"Error": [str(e)]}))

    @render.text
    def status_msg():
        if fetched_df().empty:
            return "Enter an ID and click Fetch."
        if "Error" in fetched_df().columns:
            return f"❌ Error: {fetched_df().iloc[0]['Error']}"
        
        path = os.path.join(input.download_dir(), f"{input.project_id()}_metadata.csv")
        return f"✅ Success! Data saved to: {path}"

    @render.table
    def metadata_table():
        df = fetched_df()
        if df.empty:
            return None
        # Show first 10 rows for preview
        return df.head(10)

app = App(app_ui, server)