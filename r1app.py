import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Set page config
st.set_page_config(
    page_title="My Personal Spaces",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for spaces if it doesn't exist
if 'spaces' not in st.session_state:
    st.session_state.spaces = {
        'Data Processing': {
            'type': 'tool',
            'description': 'Tools for processing different types of data',
            'tools': ['CSV Processor', 'Text Analyzer', 'Wave Route Parser']  # Added Wave Route Parser
        },
        'Medical Research': {
            'type': 'research',
            'description': 'Personal health research and notes',
            'notes': []
        },
        'Study Notes': {
            'type': 'research',
            'description': 'General study and learning notes',
            'notes': []
        }
    }

def main():
    # Sidebar for navigation
    st.sidebar.title("My Spaces")

    # Add new space button
    if st.sidebar.button("+ Create New Space"):
        create_new_space()

    # Space selection
    selected_space = st.sidebar.selectbox(
        "Select Space",
        options=list(st.session_state.spaces.keys())
    )

    # Main content area
    st.title(selected_space)
    st.write(st.session_state.spaces[selected_space]['description'])

    # Display different content based on space type
    if st.session_state.spaces[selected_space]['type'] == 'tool':
        show_tool_space(selected_space)
    else:
        show_research_space(selected_space)

def create_new_space():
    st.sidebar.subheader("Create New Space")
    space_name = st.sidebar.text_input("Space Name")
    space_type = st.sidebar.selectbox("Space Type", ["tool", "research"])
    space_description = st.sidebar.text_area("Description")

    if st.sidebar.button("Create"):
        if space_name and space_name not in st.session_state.spaces:
            st.session_state.spaces[space_name] = {
                'type': space_type,
                'description': space_description,
                'tools' if space_type == 'tool' else 'notes': [] if space_type == 'research' else ['Basic Processor']
            }
            st.sidebar.success(f"Created new space: {space_name}")

def show_tool_space(space_name):
    st.subheader("Available Tools")
    selected_tool = st.selectbox(
        "Select Tool",
        options=st.session_state.spaces[space_name]['tools']
    )

    if selected_tool == "CSV Processor":
        show_csv_processor()
    elif selected_tool == "Text Analyzer":
        show_text_analyzer()
    elif selected_tool == "Wave Route Parser":
        show_wave_route_parser()

def show_research_space(space_name):
    st.subheader("Research Notes")

    # Add new note
    new_note = st.text_area("Add New Note")
    if st.button("Save Note"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.spaces[space_name]['notes'].append({
            'timestamp': timestamp,
            'content': new_note
        })

    # Display existing notes
    for note in st.session_state.spaces[space_name]['notes']:
        with st.expander(f"Note from {note['timestamp']}"):
            st.write(note['content'])

def show_csv_processor():
    st.subheader("CSV Processor")
    uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of your data:")
        st.dataframe(df.head())

        # Basic data processing options
        if st.button("Show Basic Statistics"):
            st.write(df.describe())

        # Add more processing options as needed

def show_text_analyzer():
    st.subheader("Text Analyzer")
    text_input = st.text_area("Enter text to analyze")

    if text_input:
        # Basic text analysis
        word_count = len(text_input.split())
        char_count = len(text_input)

        col1, col2 = st.columns(2)
        col1.metric("Word Count", word_count)
        col2.metric("Character Count", char_count)

        # Add more text analysis features as needed


def parse_wave_routes(input_data):
    filtered_lines = []
    for line in input_data.splitlines():
        parts = line.split()
        if len(parts) > 2 and (parts[1] == '101' or parts[1] == '102') and '/FIBER' in line and not line.endswith('null null'):
            number = parts[1]
            fiber_type, loc1, loc2 = re.findall(r'(/FIBER\w+)/([A-Z0-9]+)/([A-Z0-9]+)', line)[0]
            filtered_lines.append(f"{number} {fiber_type} {loc1}/{loc2}")

    # Remove duplicates
    unique_lines = []
    seen = set()
    for line in filtered_lines:
        if line not in seen:
            unique_lines.append(line)
            seen.add(line)

    return unique_lines

def build_wave_path(output1, start_loc):
    # Parse routes into a list of [number, fiber_type, loc1, loc2, original_line]
    routes = []
    for line in output1:
        parts = line.split()
        number = parts[0]
        fiber_type = parts[1]
        locs = parts[2].split('/')
        if len(locs) != 2:
            continue
        loc1, loc2 = locs
        routes.append([number, fiber_type, loc1, loc2, line])  # Keep original line for output

    final_routes = []
    original_routes_count = len(routes)

    # Find the starting route (either loc1 or loc2 matches start_loc)
    start_route = None
    for i, route in enumerate(routes):
        if route[2] == start_loc or route[3] == start_loc:
            start_route = route
            final_routes.append(route[4])  # Use original line
            routes.pop(i)
            break

    if not start_route:
        return ["Error: Could not find starting location in parsed routes."], [], f"Original Routes: {original_routes_count} | Final Routes: 0 | System Changes: 0"

    # The current location is whichever end of the starting route was not the start_loc
    if start_route[2] == start_loc:
        current_location = start_route[3]
    else:
        current_location = start_route[2]

    while routes:
        found_next = False
        for i, route in enumerate(routes):
            if route[2] == current_location:
                final_routes.append(route[4])  # Use original line
                current_location = route[3]
                routes.pop(i)
                found_next = True
                break
            elif route[3] == current_location:
                final_routes.append(route[4])  # Use original line
                current_location = route[2]
                routes.pop(i)
                found_next = True
                break
        if not found_next:
            break

    final_routes_count = len(final_routes)
    system_changes_count = 0  # Not implemented

    summary = f"Original Routes: {original_routes_count} | Final Routes: {final_routes_count} | System Changes: {system_changes_count}"

    # Output 3: all original routes, formatted
    output3 = [line for line in output1]

    return final_routes, output3, summary

def show_wave_route_parser():
    st.subheader("Wave Route Parser")
    st.markdown(
        "Paste your route data below. After parsing, you'll be prompted for a starting location to build the continuous path."
    )
    input_data = st.text_area("Paste your route data here", height=300, key="wave_input")

    # Parse button
    if st.button("Parse", key="wave_parse"):
        output1 = parse_wave_routes(input_data)
        st.session_state['wave_output1'] = output1  # Store in session state

    # Show Output 1 if it exists
    if 'wave_output1' in st.session_state:
        output1 = st.session_state['wave_output1']
        st.markdown("#### Output 1")
        if output1:
            st.text('\n'.join(output1))
        else:
            st.info("No valid routes found. Please check your input.")

        # Prompt for starting location
        start_loc = st.text_input("Enter starting location code", key="wave_start_loc")
        if start_loc:
            output2, output3, summary = build_wave_path(output1, start_loc)
            st.markdown("#### Output 2 (Continuous Path)")
            st.text('\n'.join(output2))
            st.markdown("#### Output 3 (No System Changes)")
            st.text('\n'.join(output3))
            st.markdown("#### Route Comparison")
            st.text(summary)
            
if __name__ == "__main__":
    main()