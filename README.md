SRA-curation-shiny App

This repository contains a Python Shiny application for working with SRA metadata using pysradb. The app allows users to filter, view, edit, and export metadata in an interactive interface.

Prerequisites:
Ensure that Python 3.8 or higher is installed on your system.

Install the required Python packages using the following command:
pip install shiny pysradb pandas

Input File Requirement:
The application requires the file SukshmaIndia - Mapping.csv to run successfully. #Make sure if you're changing file name it should reflect in code as well
Place this file in the same directory as the Python code file.
The app will read this file at startup.

Running the Application

Navigate to the project directory and run the Shiny app using:

shiny run filename.py

Once started, the application will launch in your default web browser. or you'll have to paste https code generated in your web browser

Output / Exported Data

Any data exported from the application will be downloaded to the current working directory by default.

You may change the output path in the source code if you want exported files to be saved in a different location.


Notes:

Ensure that the input CSV file name and spelling match exactly.

Edited or filtered data within the app can be exported for downstream analysis.

This application is designed for metadata exploration and curation.

Dependencies : shiny,pysradb,pandas
