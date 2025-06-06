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
            'tools': ['CSV Processor', 'Text Analyzer', 'Wave Route Parser']
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

        if st.button("Show Basic Statistics"):
            st.write(df.describe())

def show_text_analyzer():
    st.subheader("Text Analyzer")
    text_input = st.text_area("Enter text to analyze")

    if text_input:
        word_count = len(text_input.split())
        char_count = len(text_input)

        col1, col2 = st.columns(2)
        col1.metric("Word Count", word_count)
        col2.metric("Character Count", char_count)

def parse_facility_id(line):
    """Parse a network facility ID into its components."""
    # Regular expression to match the pattern: number /FIBERL/LOCATION1/LOCATION2
    match = re.search(r'(\d+)\s+(/FIBER\w+/[A-Z0-9]+/[A-Z0-9]+)', line)
    if not match:
        return None

    seq_num, facility = match.groups()

    # Split facility into components
    parts = facility.split('/')
    if len(parts) != 4:  # Should be ['', 'FIBERL', 'LOC1', 'LOC2']
        return None

    _, fiber_type, loc1, loc2 = parts

    # Extract location code (first 8 chars) and equipment suffix
    loc1_code = loc1[:8]
    loc1_suffix = loc1[8:]
    loc2_code = loc2[:8]
    loc2_suffix = loc2[8:]

    return {
        'seq_num': seq_num,
        'full_facility': facility,
        'fiber_type': fiber_type,
        'loc1': {
            'code': loc1_code,
            'suffix': loc1_suffix,
            'full': loc1
        },
        'loc2': {
            'code': loc2_code,
            'suffix': loc2_suffix,
            'full': loc2
        }
    }

def detect_system_change(prev_segment, curr_segment):
    """Detect if there's a system change between two segments."""
    if not prev_segment or not curr_segment:
        return False

    # Check if geographical prefixes match but suffixes differ
    for loc in ['loc1', 'loc2']:
        prev_loc = prev_segment[loc]
        curr_loc = curr_segment[loc]

        if prev_loc['code'] == curr_loc['code'] and prev_loc['suffix'] != curr_loc['suffix']:
            return True

    return False

def remove_duplicates(routes):
    """Remove duplicate routes while preserving order."""
    seen = set()
    unique_routes = []

    for route in routes:
        # Create a unique key for the route based on facility ID
        route_key = f"{route['seq_num']} {route['full_facility']}"
        if route_key not in seen:
            seen.add(route_key)
            unique_routes.append(route)

    return unique_routes

def parse_wave_routes(input_data):
    filtered_lines = []
    for line in input_data.splitlines():
        parts = line.split()
        if len(parts) > 2:
            facility_parts = [p for p in parts if p.startswith('/')]
            if not facility_parts:
                continue
            facility = facility_parts[0]
            if '/FIBER' in facility.upper() and not line.endswith('null null'):
                try:
                    number = parts[1]
                    path_parts = facility.split('/')
                    if len(path_parts) == 4:
                        _, fiber_type, loc1, loc2 = path_parts
                        filtered_lines.append(f"{number} {facility}")
                except:
                    continue
    unique_lines = []
    seen = set()
    for line in filtered_lines:
        if line not in seen:
            unique_lines.append(line)
            seen.add(line)
    return unique_lines

def build_wave_path(output1, start_loc):
    # Helper functions remain the same
    def get_clli(loc):
        return loc[:8] if len(loc) >= 8 else loc

    def get_suffix_type(loc):
        if len(loc) > 8:
            return loc[8:9]
        return ''

    # Parse all routes into a list of dicts, both directions
    routes = []
    # Store original unique routes for accurate counting
    original_unique_routes = set(output1)  # This gives us the true count of input routes

    for line in output1:
        parts = line.split()
        if len(parts) < 2:
            continue
        number = parts[0]
        facility = parts[1]
        path_parts = facility.split('/')
        if len(path_parts) != 4:
            continue
        _, fiber_type, loc1, loc2 = path_parts
        routes.append({
            'number': number,
            'fiber_type': fiber_type,
            'loc1': loc1,
            'loc2': loc2,
            'line': line,
            'loc1_clli': get_clli(loc1),
            'loc2_clli': get_clli(loc2)
        })
        routes.append({
            'number': number,
            'fiber_type': fiber_type,
            'loc1': loc2,
            'loc2': loc1,
            'line': line,
            'loc1_clli': get_clli(loc2),
            'loc2_clli': get_clli(loc1)
        })

    used_lines = set()
    final_routes = []
    system_changes = 0
    original_routes_count = len(original_unique_routes)  # Use the actual count from input

    # Rest of the function remains the same...
    start_loc = get_clli(start_loc.strip().upper())
    current_loc = None
    prev_suffix = None

    for route in routes:
        if route['loc1_clli'] == start_loc:
            final_routes.append(route['line'])
            used_lines.add(route['line'])
            current_loc = route['loc2_clli']
            prev_suffix = get_suffix_type(route['loc1'])
            break

    if not final_routes:
        return ["Error: Could not find starting location in parsed routes."], [], f"Original Routes: {original_routes_count} | Final Routes: 0 | System Changes: 0"

    while True:
        found = False
        for route in routes:
            if route['line'] in used_lines:
                continue

            if route['loc1_clli'] == current_loc:
                curr_suffix = get_suffix_type(route['loc1'])
                if prev_suffix and curr_suffix and prev_suffix != curr_suffix:
                    final_routes.append('--- SYSTEM CHANGE ---')
                    system_changes += 1

                final_routes.append(route['line'])
                used_lines.add(route['line'])
                current_loc = route['loc2_clli']
                prev_suffix = get_suffix_type(route['loc2'])
                found = True
                break

        if not found:
            break

    final_routes_count = len([line for line in final_routes if not line.startswith('---')])
    summary = f"Original Routes: {original_routes_count} | Final Routes: {final_routes_count} | System Changes: {system_changes}"
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
        routes = parse_wave_routes(input_data)
        st.session_state['parsed_routes'] = routes  # Store in session state

    # Only show parsed routes if they exist in session state
    if 'parsed_routes' in st.session_state and st.session_state['parsed_routes']:
        routes = st.session_state['parsed_routes']
        st.markdown("#### Parsed Routes (Duplicates Removed)")
        for route in routes:
            st.text(route)

        start_loc = st.text_input("Enter starting location code (8 characters)", key="wave_start_loc")
        if start_loc:
            path, changes, summary = build_wave_path(routes, start_loc)
            st.markdown("#### Continuous Path with System Changes")
            for line in path:
                st.text(line)
            st.markdown("#### Summary")
            st.text(summary)
    elif 'parsed_routes' in st.session_state and not st.session_state['parsed_routes']:
        st.error("No valid routes found in input data")

if __name__ == "__main__":
    main()