import streamlit as st
import pandas as pd
from datetime import datetime
import re
from io import StringIO

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
            'tools': ['Wave Route Parser', 'Fiber Sheath Parser', 'XLR Parser']
        }
    }

def extract_field(data, field_names):
    """
    Try to extract the value for any of the field_names from the data.
    Returns the value or None if not found.
    """
    for field in field_names:
        # Regex: field name, optional spaces, then value (until end of line)
        match = re.search(rf"{field}\s*[:=]?\s*(.+)", data, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # If the value is just a dash or empty, skip
            if value and value != "-":
                return value
    return None

def main():
    # Sidebar for navigation
    st.sidebar.title("My Spaces")

    # Tool selection using radio buttons
    selected_tool = st.sidebar.radio(
        "Select Tool",
        options=st.session_state.spaces['Data Processing']['tools']
    )

    # Main content area
    st.title("Data Processing")
    st.write(st.session_state.spaces['Data Processing']['description'])

    # Display different content based on selected tool
    if selected_tool == "Wave Route Parser":
        show_wave_route_parser()
    elif selected_tool == "Fiber Sheath Parser":
        fiber_sheath_parser()
    elif selected_tool == "XLR Parser":
        show_xlr_parser()

def show_xlr_parser():
    st.header("XLR Parser")

    # Initialize session state for multiple XLR parses
    if "xlr_history" not in st.session_state:
        st.session_state.xlr_history = []

    # Show all previous parses
    for idx, (input_text, output_text) in enumerate(st.session_state.xlr_history):
        st.subheader(f"XLR Parse #{idx+1}")
        st.text_area(f"Input #{idx+1}", input_text, height=150, key=f"xlr_input_{idx}", disabled=True)
        st.code(output_text, language="text")
        st.divider()

    # New input box at the bottom
    with st.form(key=f"xlr_form_{len(st.session_state.xlr_history)}"):
        xlr_text = st.text_area("Paste XLR text here:", height=300, key=f"xlr_input_new_{len(st.session_state.xlr_history)}")
        submitted = st.form_submit_button("Parse XLR")
        if submitted and xlr_text.strip():
            fields_to_extract = [
                "Service Name", "Circuit ID", "Account Name",
                "Product Group", "Product", "Product Category", "Rate Code",
                "A-Clli", "A-Address", "Z-Clli", "Z-Address"
            ]
            extracted = {field: "Not found" for field in fields_to_extract}
            for line in xlr_text.splitlines():
                for field in fields_to_extract:
                    if line.startswith(field + "\t"):
                        parts = line.split('\t', 1)
                        if len(parts) > 1:
                            extracted[field] = parts[1].strip()
            a_clli = extracted.get("A-Clli", "").strip()
            z_clli = extracted.get("Z-Clli", "").strip()

            # Find the table header and parse the table
            lines = xlr_text.splitlines()
            table_start = None
            for i, line in enumerate(lines):
                if (
                    "CLLI" in line and "Address" in line
                    and line.count('\t') > 2
                ):
                    table_start = i
                    break

            clli_to_address = {}
            if table_start is not None:
                table_text = "\n".join(lines[table_start:])
                try:
                    df = pd.read_csv(
                        StringIO(table_text),
                        sep='\t',
                        dtype=str,
                        on_bad_lines='skip',
                        skip_blank_lines=True
                    )
                    df.columns = df.columns.str.strip()
                    if "CLLI" in df.columns and "Address" in df.columns:
                        for clli, addr in zip(df["CLLI"], df["Address"]):
                            if pd.notna(clli) and pd.notna(addr) and addr.strip():
                                clli_to_address[clli.strip()] = addr.strip()
                except Exception as e:
                    pass

            def fuzzy_lookup_first(base_clli):
                for clli, addr in clli_to_address.items():
                    if clli.startswith(base_clli):
                        return addr
                return "Not found"

            address_a = fuzzy_lookup_first(a_clli) if a_clli else "Not found"
            address_z = fuzzy_lookup_first(z_clli) if z_clli else "Not found"

            # Network Facilities Extraction
            facilities = []
            facility_pattern = re.compile(
                r'([A-Z0-9]+)?\s*/([0-9A-Z]+(?:G|FIBER))\s*/([A-Z0-9]+)/([A-Z0-9]+)', re.IGNORECASE)
            for line in xlr_text.splitlines():
                m = facility_pattern.search(line)
                if m:
                    facilities.append(f"{m.group(1) or ''} /{m.group(2)} /{m.group(3)}/{m.group(4)}".strip())

            # Output
            output = []
            output.append("=== Key Fields ===")
            output.append(f"Service Name: {extracted['Service Name']}")
            output.append(f"Circuit ID: {extracted['Circuit ID']}")
            output.append(f"Account Name: {extracted['Account Name']}")
            product_summary = f"{extracted['Rate Code']} {extracted['Product']}".replace("Standard Wavelength", "Wavelength").strip()
            output.append(f"Product: {product_summary}")
            output.append(f"A-Clli: {extracted['A-Clli']}")
            output.append(f"A-Address: {extracted['A-Address']}")
            output.append(f"Z-Clli: {extracted['Z-Clli']}")
            output.append(f"Z-Address: {extracted['Z-Address']}")
            output.append("")
            output.append(f"Street Address for A-Clli ({a_clli}): {address_a}")
            output.append(f"Street Address for Z-Clli ({z_clli}): {address_z}")
            output.append("")
            if facilities:
                output.append("=== Network Facilities ===")
                output.extend(facilities)

            result = "\n".join(output)
            # Save this input/output pair to session state
            st.session_state.xlr_history.append((xlr_text, result))
            st.rerun()

def parse_facility_id(line):
    """Parse a network facility ID into its components."""
    match = re.search(r'(\d+)\s+(/FIBER\w+/[A-Z0-9]+/[A-Z0-9]+)', line)
    if not match:
        return None

    seq_num, facility = match.groups()
    parts = facility.split('/')
    if len(parts) != 4:
        return None

    _, fiber_type, loc1, loc2 = parts
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
    if not prev_segment or not curr_segment:
        return False
    for loc in ['loc1', 'loc2']:
        prev_loc = prev_segment[loc]
        curr_loc = curr_segment[loc]
        if prev_loc['code'] == curr_loc['code'] and prev_loc['suffix'] != curr_loc['suffix']:
            return True
    return False

def remove_duplicates(routes):
    seen = set()
    unique_routes = []
    for route in routes:
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
    def get_clli(loc):
        return loc[:8] if len(loc) >= 8 else loc

    def get_suffix_type(loc):
        if len(loc) > 8:
            return loc[8:9]
        return ''

    routes = []
    original_unique_routes = set(output1)
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
    original_routes_count = len(original_unique_routes)

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

    # Initialize session state for multiple wave parses
    if "wave_history" not in st.session_state:
        st.session_state.wave_history = []

    description = """
    The tool extracts fiber route details from ZDAF's Waves Design Tool. It generates an ordered list of the Fiber facilities on your route for a COR form.

    To use the Wave Route Parser:

    1.  In ZDAF, design a wave route and click the 'Fiber' radio button.
    2.  Copy the displayed fiber data.
    3.  Paste the data into the Wave Route Parser.
    4.  Enter a starting CLLI to generate the ordered facility list.
    """
    st.markdown(description)

    # Show all previous parses
    for idx, (input_text, parsed_routes, start_loc, path_result, summary) in enumerate(st.session_state.wave_history):
        st.subheader(f"Wave Parse #{idx+1}")
        st.text_area(f"Input #{idx+1}", input_text, height=150, key=f"wave_input_{idx}", disabled=True)
        
        if parsed_routes:
            st.markdown("#### Parsed Routes (Duplicates Removed)")
            routes_text = "\n".join(parsed_routes)
            st.text_area(f"Parsed Routes #{idx+1}", routes_text, height=200, key=f"wave_parsed_{idx}", disabled=True)
            
            if start_loc and path_result:
                st.markdown(f"#### Starting Location: {start_loc}")
                st.markdown("#### Continuous Path with System Changes")
                path_text = "\n".join(path_result)
                st.text_area(f"Path #{idx+1}", path_text, height=300, key=f"wave_path_{idx}", disabled=True)
                st.markdown("#### Summary")
                st.text(summary)
        st.divider()

    # New input section
    st.markdown("Paste your route data below. After parsing, you'll be prompted for a starting location to build the continuous path.")
    
    with st.form(key=f"wave_form_{len(st.session_state.wave_history)}"):
        input_data = st.text_area("Paste your route data here", height=300, key=f"wave_input_new_{len(st.session_state.wave_history)}")
        parse_submitted = st.form_submit_button("Parse")
        if parse_submitted and input_data.strip():
            routes = parse_wave_routes(input_data)
            if routes:
                # Store the parsed routes temporarily
                st.session_state['temp_wave_data'] = {
                    'input': input_data,
                    'routes': routes
                }
                st.rerun()
            else:
                st.error("No valid routes found in input data")

    # If we have temporary parsed data, show it and ask for starting location
    if 'temp_wave_data' in st.session_state:
        temp_data = st.session_state['temp_wave_data']
        st.markdown("#### Parsed Routes (Duplicates Removed)")
        for route in temp_data['routes']:
            st.text(route)

        with st.form(key=f"wave_start_form_{len(st.session_state.wave_history)}"):
            start_loc = st.text_input("Enter starting location code (8 characters)", key=f"wave_start_new_{len(st.session_state.wave_history)}")
            start_submitted = st.form_submit_button("Build Path")
            if start_submitted and start_loc:
                path, changes, summary = build_wave_path(temp_data['routes'], start_loc)
                
                # Save to history
                st.session_state.wave_history.append((
                    temp_data['input'],
                    temp_data['routes'],
                    start_loc,
                    path,
                    summary
                ))
                
                # Clear temporary data
                del st.session_state['temp_wave_data']
                st.rerun()

def fiber_sheath_parser():
    st.header("Fiber Sheath Parser")

    # Initialize session state for multiple fiber parses
    if "fiber_history" not in st.session_state:
        st.session_state.fiber_history = []

    description = """
    The tool extracts fiber route details from IQGeo. It returns fiber cables, overall distance, cable segments, and segments with fewer than 20 fibers available.

    To use the Fiber Sheath Parser:

    1.  In IQGeo, find a PRM route.
    2.  Click 'Fiber Propagations' and then the grid icon.
    3.  Copy all the data.
    4.  Paste the data into the Fiber Sheath Parser.
    """
    st.markdown(description)

    # Show all previous parses
    for idx, (input_text, result_data) in enumerate(st.session_state.fiber_history):
        st.subheader(f"Fiber Parse #{idx+1}")
        st.text_area(f"Input #{idx+1}", input_text, height=150, key=f"fiber_input_{idx}", disabled=True)
        
        # Display the results
        st.subheader("Total Route Distance")
        st.markdown(f"<p style='color:blue'>Total Footage: <b>{result_data['total_footage']:.2f} FT</b></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:green'>Total Miles: <b>{result_data['total_miles']:.2f} miles</b></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:purple'>Total Kilometers: <b>{result_data['total_km']:.2f} km</b></p>", unsafe_allow_html=True)
        st.markdown(f"Estimated optical distance: <b>{result_data['estimated_optical_km']:.2f} km</b> <span style='color:red'>(13% added for slack, splices, and slack loops)</span>", unsafe_allow_html=True)

        st.subheader("EXPANDED Fiber route as described by Cable Names")
        if result_data['cable_names']:
            for cable in result_data['cable_names']:
                st.write(f"- {cable}")
        else:
            st.write("No cable names found.")

        st.subheader("Detailed Cable Path with Individual Segments")
        if result_data['unique_sheaths']:
            for sheath, footage in result_data['sheath_footage'].items():
                st.write(f"  - {sheath}: {footage:.2f} FT")
        else:
            st.write("No sheaths found.")

        st.subheader("Sheath Fibers Available (<20)")
        if result_data['sheath_fiber_avail']:
            for sheath, avail in result_data['sheath_fiber_avail']:
                st.write(f"- {sheath}: {avail}")
        else:
            st.write("No sheaths with <20 fibers available found.")
        
        st.divider()

    st.markdown("Paste your fiber data below (raw text, as copied):")

    # New input form
    with st.form(key=f"fiber_form_{len(st.session_state.fiber_history)}"):
        data = st.text_area("Paste fiber data here", height=400, key=f"fiber_data_input_{len(st.session_state.fiber_history)}")
        submitted = st.form_submit_button("Parse Fiber Data")

        if submitted and data.strip():
            unique_sheaths = []
            seen_sheaths = set()
            sheath_fiber_avail = []
            cable_names = []
            seen_cables = set()
            sheath_footage = {}
            total_footage = 0.0
            lines = data.splitlines()
            current_sheath = None

            for i, line in enumerate(lines):
                match = re.search(r'Sheath:\s*([^\(]+(?:\([^)]+\))?)', line)
                if match:
                    current_sheath = match.group(1).strip()
                    if current_sheath not in seen_sheaths:
                        unique_sheaths.append(current_sheath)
                        seen_sheaths.add(current_sheath)
                        sheath_footage[current_sheath] = 0.0
                    base_cable = re.sub(r'\s*\([^)]+\)$', '', current_sheath).strip()
                    if base_cable not in seen_cables:
                        cable_names.append(base_cable)
                        seen_cables.add(base_cable)
                footage_match = re.search(r'(\d+\.\d+)\s+FT', line)
                if footage_match and current_sheath:
                    footage = float(footage_match.group(1))
                    sheath_footage[current_sheath] += footage
                    total_footage += footage
                avail_match = re.search(r'Sheath Fibers Available\s*:\s*(\d+)', line)
                if avail_match and current_sheath:
                    avail = int(avail_match.group(1))
                    if avail < 20:
                        sheath_fiber_avail.append((current_sheath, avail))

            total_miles = total_footage / 5280
            total_km = total_footage * 0.0003048
            estimated_optical_km = total_km * 1.13

            # Store results
            result_data = {
                'total_footage': total_footage,
                'total_miles': total_miles,
                'total_km': total_km,
                'estimated_optical_km': estimated_optical_km,
                'cable_names': cable_names,
                'unique_sheaths': unique_sheaths,
                'sheath_footage': sheath_footage,
                'sheath_fiber_avail': sheath_fiber_avail
            }

            # Save to history
            st.session_state.fiber_history.append((data, result_data))
            st.rerun()

if __name__ == "__main__":
    main()