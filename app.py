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

    # Create a sample XLR text for testing
    sample_xlr = """Service Name: ACME-MPLS-001
Circuit ID: CKT-12345
Account Name: ACME Corporation

A-Address: 123 Main St, New York, NY 10001
Building: F20W-123456
OSP EB 456789

Z-Address: 456 Park Ave, Chicago, IL 60601
Building: F16X-654321
OSP EB 987654

Network Facilities:
10 /10G /NYC1/CHI1
20 /1G /NYC2/CHI2
"""

    if st.sidebar.button("Load Sample XLR"):
        st.session_state.sample_xlr = sample_xlr

    xlr_text = ""
    if 'sample_xlr' in st.session_state:
        xlr_text = st.session_state.sample_xlr

    xlr_text = st.text_area("Paste XLR text here:", xlr_text, height=300)

    if st.button("Parse XLR"):
        if not xlr_text:
            st.warning("Please paste XLR text to parse.")
            return

        # Extract fields robustly
        service_name = extract_field(xlr_text, ["Service Name"])
        circuit_id = extract_field(xlr_text, ["Circuit ID"])
        account_name = extract_field(xlr_text, ["Account Name"])
        address_a = extract_field(xlr_text, ["A-Address", "Address A"])
        address_z = extract_field(xlr_text, ["Z-Address", "Address Z"])

        # Extract city from address
        def extract_city(address):
            if not address:
                return "Unknown"
            # Look for pattern like "City Name XX" where XX is state code
            city_match = re.search(r'([A-Za-z\s]+\s[A-Z]{2})', address)
            if city_match:
                return city_match.group(1).strip()
            return "Unknown"

        city_a = extract_city(address_a)
        city_z = extract_city(address_z)

        # Generalized fiber ID regex: F + 2 digits + 1 letter + - + 6+ digits
        fiber_id_pattern = r'F\d{2}[A-Z]-\d{6,}'
        fiber_ids = re.findall(fiber_id_pattern, xlr_text)
        osp_eb_matches = re.findall(r'OSP EB \d+', xlr_text)

        # Split fiber IDs and OSP EBs between A and Z (first half to A, second half to Z)
        mid_fiber = len(fiber_ids) // 2
        mid_osp = len(osp_eb_matches) // 2

        fiber_a = fiber_ids[:mid_fiber] if fiber_ids else []
        fiber_z = fiber_ids[mid_fiber:] if fiber_ids else []

        osp_eb_a = osp_eb_matches[:mid_osp] if osp_eb_matches else []
        osp_eb_z = osp_eb_matches[mid_osp:] if osp_eb_matches else []

        # Output formatting
        output = []
        output.append(f"Service Name  =   {service_name or 'Not found'}")
        output.append(f"Circuit ID   =   {circuit_id or 'Not found'}")
        output.append(f"Account Name =  {account_name or 'Not found'}")
        output.append("")
        output.append(f"Address A  =  {address_a or 'Not found'}")
        output.append(f"OSP = ")
        if fiber_a or osp_eb_a:
            for item in fiber_a:
                output.append(item)
            for item in osp_eb_a:
                output.append(item)
        else:
            output.append("Not found")
        output.append("")
        output.append(f"Address Z =  {address_z or 'Not found'}")
        output.append(f"OSP = ")
        if fiber_z or osp_eb_z:
            for item in fiber_z:
                output.append(item)
            for item in osp_eb_z:
                output.append(item)
        else:
            output.append("Not found")
        output.append("")

        # Network Facilities: find lines that look like "number /something /something/something"
        facilities = []
        for line in xlr_text.splitlines():
            if re.match(r"\d+\s+/\S+", line.strip()):
                facilities.append(line.strip())
        if facilities:
            output.append("Network Facilities:")
            output.extend(facilities)

        st.text_area("Parsed Output:", "\n".join(output), height=400)
        
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
    st.markdown(
        "Paste your route data below. After parsing, you'll be prompted for a starting location to build the continuous path."
    )
    input_data = st.text_area("Paste your route data here", height=300, key="wave_input")

    if st.button("Parse", key="wave_parse"):
        routes = parse_wave_routes(input_data)
        st.session_state['parsed_routes'] = routes

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

def fiber_sheath_parser():
    import re
    st.header("Fiber Sheath Parser")
    st.markdown("Paste your fiber data below (raw text, as copied):")

    # Wrap the text_area and button in a form
    with st.form(key="fiber_form"):
        data = st.text_area("Paste fiber data here", height=400, key="fiber_data_input")
        submitted = st.form_submit_button("Parse Fiber Data")

        if submitted:
            if not data.strip():
                st.warning("Please paste some data first.")
                return

            unique_sheaths = []
            seen_sheaths = set()
            sheath_fiber_avail = []

            # For cable names with segments removed
            cable_names = []
            seen_cables = set()

            # For tracking footage
            sheath_footage = {}  # Dictionary to store sheath -> footage
            total_footage = 0.0  # Total footage counter

            lines = data.splitlines()
            current_sheath = None  # Track the current sheath being processed

            for i, line in enumerate(lines):
                # Find unique sheaths
                match = re.search(r'Sheath:\s*([^\(]+(?:\([^)]+\))?)', line)
                if match:
                    current_sheath = match.group(1).strip()
                    if current_sheath not in seen_sheaths:
                        unique_sheaths.append(current_sheath)
                        seen_sheaths.add(current_sheath)
                        sheath_footage[current_sheath] = 0.0  # Initialize footage for this sheath

                    # Remove segment in parentheses at the end, if present
                    base_cable = re.sub(r'\s*\([^)]+\)$', '', current_sheath).strip()
                    if base_cable not in seen_cables:
                        cable_names.append(base_cable)
                        seen_cables.add(base_cable)

                # Find footage information
                footage_match = re.search(r'(\d+\.\d+)\s+FT', line)
                if footage_match and current_sheath:
                    footage = float(footage_match.group(1))
                    sheath_footage[current_sheath] += footage
                    total_footage += footage

                # Find "Sheath Fibers Available" (if present)
                avail_match = re.search(r'Sheath Fibers Available\s*:\s*(\d+)', line)
                if avail_match and current_sheath:
                    avail = int(avail_match.group(1))
                    if avail < 20:
                        sheath_fiber_avail.append((current_sheath, avail))

            # Calculate distances
            total_miles = total_footage / 5280
            total_km = total_footage * 0.0003048
            estimated_optical_km = total_km * 1.13

            # Display total footage first
            st.subheader("Total Route Distance")
            st.markdown(f"<p style='color:blue'>Total Footage: <b>{total_footage:.2f} FT</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:green'>Total Miles: <b>{total_miles:.2f} miles</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:purple'>Total Kilometers: <b>{total_km:.2f} km</b></p>", unsafe_allow_html=True)
            st.markdown(f"Estimated optical distance: <b>{estimated_optical_km:.2f} km</b> <span style='color:red'>(13% added for slack, splices, and slack loops)</span>", unsafe_allow_html=True)

            # Print the expanded cable names section
            st.subheader("EXPANDED Fiber route as described by Cable Names")
            if cable_names:
                for cable in cable_names:
                    st.write(f"- {cable}")
            else:
                st.write("No cable names found.")

            # Then print the longer list with footage, indented
            st.subheader("Detailed Cable Path with Individual Segments")
            if unique_sheaths:
                for sheath in unique_sheaths:
                    footage = sheath_footage.get(sheath, 0.0)
                    st.write(f"  - {sheath}: {footage:.2f} FT")
            else:
                st.write("No sheaths found.")

            st.subheader("Sheath Fibers Available (<20)")
            if sheath_fiber_avail:
                for sheath, avail in sheath_fiber_avail:
                    st.write(f"- {sheath}: {avail}")
            else:
                st.write("No sheaths with <20 fibers available found.")

if __name__ == "__main__":
    main()