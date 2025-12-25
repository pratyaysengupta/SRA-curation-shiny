from shiny import App, render, ui, reactive
from pysradb import SRAweb
import pandas as pd
import os
import re
from shiny.render import DataGrid

# Load the mapping file
mapping_df = pd.read_csv('SukshmaIndia - Mapping.csv')

# Initialize the dictionary
MAPPING_DATA = {}

# Iterate through each row to handle the conditional list logic
for _, row in mapping_df.iterrows():
    key = row['Granular Environment']
    broad = row['Broad Classification']
    # .get() or pd.isna() handles cases where 'Extra' might be empty/NaN
    extra = row.get('Extra')

    # If 'Extra' has a value and is not NaN
    if pd.notna(extra) and str(extra).strip() != "":
        # Create a list containing both values
        MAPPING_DATA[key] = [broad, extra]
    else:
        # Just store the single broad classification string
        MAPPING_DATA[key] = broad

# Usage check
# print(MAPPING_DATA)

SHEET_5_FIELDS = {
    "Built/ Engineered/ Industrial" :['Time Series(Yes/No)','Temperature','pH','Oxygen Level','Humidity','Salinity','Contaminants','Other Notes','Reactor Type','Treatment Stage','Surface Material'],
    "Aquatic/ Marine": ['Time Series(Yes/No)','Temperature','pH','Salinity','Depth','Dissolved Oxygen','Turbidity','Other Notes','Water Body Type','Proximity to Shore','Sediment Type','Season'],
    "Extreme environment": ['Time Series(Yes/No)','Temperature','pH','Salinity','Moisture Level','Radiation Level','Other Notes','Environment Type','Geological Features'],
    "Host animal and insect":['Time Series(Yes/No)','Host Species','Breed/Strain','Host_Weight(kg)','Host_Age(years)','Disease Status','Body Site','Other Notes','Antibiotic Usage(yes/no)','Host_Diet'],
    "Plant/ Fungi":['Time Series(Yes/No)','Temperature','pH','Moisture Level','Nutrient Levels','Other Notes','Host Species','Tissue Type','Disease Status','Disease'],
    "Terrestrial/ soil":['Time Series(Yes/No)','Temperature','pH','Moisture Level','Nutrient Levels','Contaminants','Other Notes','Soil Type','Land Use','Vegetation Cover','Texture','Depth'],
    "Host human":['Time Series(Yes/No)','Host Species','Host_Age(years)','Host_Sex','BMI','Disease Status','Body Site','Other Notes','Host_weight(kg)','Antibiotic Usage(yes/no)','Host_Diet','Smoking Status','Alcohol Consumption(yes/no)'],
    "Other":[]
}

db = SRAweb()

def clean_id(name):
    """Helper to make column names valid Shiny IDs."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(name))

def make_unique_columns(cols):
    """
    Make column names unique by appending __1, __2, ...
    Preserves first occurrence as-is.
    """
    seen = {}
    new_cols = []

    for col in cols:
        if col not in seen:
            seen[col] = 0
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}__{seen[col]}")

    return new_cols


app_ui = ui.page_fluid(
    ui.panel_title("SukshmaIndia Metadata Curator"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.h4("1. Fetch Data"),
            ui.input_text("project_id", "NCBI Project ID", placeholder="SRP098789"),
            ui.input_action_button("fetch", "Fetch Data", class_="btn-primary w-100"),
            ui.hr(),
            
            ui.input_checkbox(
                "filter_bases",
                "Keep runs with Bases ≥ 1e9",
                value=True
            ),


            ui.h4("2. Edit Columns"),
            ui.input_text("custom_col", "Add Column:"),
            ui.input_action_button("add_col_btn", "Add", class_="btn-sm"),
            ui.hr(),
            ui.output_ui("remove_col_ui"),
            ui.input_action_button("remove_col_btn", "Remove Selected", class_="btn-danger btn-sm"),
            ui.hr(),

            ui.h4("3. Environment Suggestions"),
            ui.output_ui("env_suggestion_ui"),
            ui.output_ui("field_checkboxes_ui"),
            ui.input_action_button("apply_fields", "Inject Fields", class_="btn-info w-100"),
            ui.hr(),
            
            ui.h4("4. Export"),
            ui.input_text("download_dir", "Save Path", value=os.getcwd()),
            ui.input_action_button("save", "Save CSV", class_="btn-success w-100"),
        ),
        ui.card(
            ui.card_header("Metadata Workbench"),
            ui.accordion(
                ui.accordion_panel("Global Filters (Apply only if needed)", ui.output_ui("filter_controls_ui")),
                open=False # Keep closed so it doesn't break the initial load
            ),
            ui.output_data_frame("metadata_grid")
        )
    )
)

def server(input, output, session):
    # The 'Master' data is stored here
    master_data = reactive.Value(pd.DataFrame())
    suggested_env = reactive.Value("Other")

    # --- 1. Fetching Logic (Direct and Simple) ---
    @reactive.Effect
    @reactive.event(input.fetch)
    def _():
        sid = input.project_id().strip()
        if not sid: return
        
        try:
            df = db.sra_metadata(sid, detailed=True)

            if df.empty:
                ui.notification_show("No data found.", type="warning")
                return
            # Check for duplicate columns
            dupes = pd.Series(df.columns).duplicated().sum()
            if dupes > 0:
                ui.notification_show(
                    f"{dupes} duplicate column names detected and auto-renamed.",
                    type="warning",
                    duration=5
                )

            # Enforce unique column names immediately
            df.columns = make_unique_columns(df.columns)
            

            #Remove all the unnecessary columns
            cols_to_remove = ['organism_taxid','library_name','library_source','library_selection','biosample','instrument_model','instrument_model_desc',
                              'total_spots','total_size','run_total_spots','run_alias','public_filename','public_size','insdc first public','insdc last update','insdc status',
                              'public_date','public_md5','public_version','public_semantic_name','public_supertype','public_sratoolkit','submitter id',
                              'aws_url','aws_free_egress','aws_access_type','public_url','ncbi_url','ncbi_free_egress','ncbi_access_type','ebi_url','ebi_free_egress','ebi_access_type',
                              'gcp_url','gcp_access_type','experiment_alias','collection_date','biosamplemodel','ena_fastq_http','ena_fastq_http_1',
                              'ena_fastq_http_2','ena_fastq_ftp','ena_fastq_ftp_1','ena_fastq_ftp_2','gcp_free_egress','ena-first-public','ena-last-update','external id']
            
            for col in cols_to_remove:
                if col in df.columns:
                    df.drop(columns=[col], inplace=True)

            #List of mandatory columns to be added if not present already
            mandatory_cols = ['study_accession','sample_accession','run_accession','Environment_Broad_Scale','Specific_Environment','instrument','library_layout','run_total_bases']
            for col in mandatory_cols:
                if col not in df.columns:
                    df[col] = ""
                    df[col] = df[col].fillna("")

            # Simple Case-Insensitive Mapping
            org_col = 'organism_name' if 'organism_name' in df.columns else 'organism'
            sample_val = str(df[org_col].iloc[0]).lower() if org_col in df.columns else ""
            
            matched = "Other"
            for key, val in MAPPING_DATA.items():
                if key.lower() in sample_val:
                    matched = ", ".join(val) if isinstance(val, list) else val
                    break
            
            suggested_env.set(matched)
            df['Broader Category'] = matched
            master_data.set(df) # This triggers the table display immediately
            ui.notification_show(f"Loaded {len(df)} samples.")
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error")

    # --- 2. Column Management ---
    @output
    @render.ui
    def remove_col_ui():
        df = master_data()
        if df.empty: return None
        return ui.input_selectize("to_drop", "Drop Columns:", choices=df.columns.tolist(), multiple=True)

    @reactive.Effect
    @reactive.event(input.remove_col_btn)
    def _():
        df = master_data().copy()
        if input.to_drop():
            df.drop(columns=list(input.to_drop()), inplace=True)
            master_data.set(df)

    @reactive.Effect
    @reactive.event(input.add_col_btn)
    def _():
        df = master_data().copy()
        new = input.custom_col().strip()
        if new and new not in df.columns:
            df[new] = ""
            master_data.set(df)

    # --- 3. Filtering Logic (Isolated to prevent blanking) ---
    @output
    @render.ui
    def filter_controls_ui():
        df = master_data()
        if df.empty: return ui.p("Fetch data first.")
        
        # Limit filters to the most useful columns to avoid UI lag
        core_cols = ['organism_name', 'library_strategy','geo_loc_name','geographic location (country and/or sea)']
        available = [c for c in core_cols if c in df.columns]
        
        controls = [] 
        for col in available:
            safe_id = f"f_{clean_id(col)}"
            choices = sorted(df[col].dropna().unique().astype(str).tolist())
            controls.append(ui.input_selectize(safe_id, f"Filter {col}:", choices=["All"] + choices, multiple=True))
        return ui.div(*controls)

    @reactive.Calc
    def display_df():
        df = master_data()
        if df.empty: return df
        
        filtered = df.copy()

        # -----------------------------
        # Bases filter (run_total_bases ≥ 1e9)
        # -----------------------------
        if "run_total_bases" in filtered.columns and input.filter_bases():
            filtered["run_total_bases"] = pd.to_numeric(
                filtered["run_total_bases"],
                errors="coerce"
            )
            filtered = filtered[filtered["run_total_bases"] >= 1e9] 
        # Only apply a filter if the input exists AND the user has interacted with it
        core_cols = ['organism_name', 'library_strategy','geo_loc_name','geographic location (country and/or sea)']
        for col in [c for c in core_cols if c in df.columns]:
            safe_id = f"f_{clean_id(col)}"
            if hasattr(input, safe_id):
                selection = getattr(input, safe_id)()
                if selection and "All" not in selection:
                    filtered = filtered[filtered[col].astype(str).isin(selection)]
        return filtered

    # --- 4. Environment Injection ---
    @output
    @render.ui
    def env_suggestion_ui():
        return ui.div(ui.strong("Suggested: "), ui.span(suggested_env()))

    @output
    @render.ui
    def field_checkboxes_ui():
        cat = suggested_env()
        fields = SHEET_5_FIELDS.get(cat, SHEET_5_FIELDS["Other"])
        return ui.input_checkbox_group("chk_fields", "Inject Fields:", choices=fields, selected=fields)

    @reactive.Effect
    @reactive.event(input.apply_fields)
    def _():
        df = master_data().copy()
        if input.chk_fields():
            for f in input.chk_fields():
                if f not in df.columns: df[f] = ""
            master_data.set(df)

    # --- 5. Rendering & Save ---
    @output
    @render.data_frame
    def metadata_grid():
        # Always use display_df() to ensure filters apply but don't break the initial load
        return DataGrid(display_df(), editable=True)

    @reactive.Effect
    @reactive.event(input.metadata_grid_cell_edit)
    def _():
        edit = input.metadata_grid_cell_edit()
        if edit is None:
            return
        #copy of master data
        df = master_data().copy()

        #The view shown in the grid
        view_df = display_df()

        # Map back from filtered view to master data
        row_idx = view_df.index[edit["row"]]
        col_name = view_df.columns[edit["col"]]

        #apply the edit
        df.at[row_idx, col_name] = edit["value"]
        master_data.set(df)

        # SANITY CHECK (TEMPORARY)
        print(
            "[EDIT SAVED]",
            "Row:", row_idx,
            "Column:", col_name,
            "Value:", master_data().loc[row_idx, col_name]
        )
    @reactive.Effect
    @reactive.event(input.save)
    def _():
        df = display_df() #This is to save only what is being seen after putting all the filters.
        if not df.empty:
            path = os.path.join(input.download_dir(), f"{input.project_id()}_curated.csv")
            df.to_csv(path, index=False)
            ui.notification_show("Export Successful!", type="success")

app = App(app_ui, server)
