import streamlit as st
st.set_page_config(page_title="Fiberco KMZ Length Cleaner", layout="wide")

st.markdown("""
<style>
.main {
    background: #f7f9fc;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

.hero {
    background: linear-gradient(135deg, #1f4e79, #2f80ed);
    color: white;
    padding: 2rem;
    border-radius: 18px;
    margin-bottom: 1.5rem;
}

.hero h1 {
    margin-bottom: 0.25rem;
}

.card {
    background: white;
    padding: 1.25rem;
    border-radius: 16px;
    border: 1px solid #e6eaf0;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}

.small-muted {
    color: #667085;
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)
import zipfile
import tempfile
import os
import re
import math
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO



st.markdown("""
<div class="hero">
    <h1>Fiberco KMZ Length Cleaner</h1>
    <p>Extract entered footage from placemark descriptions, calculate true coordinate geometry length, and export cleaned KML/KMZ files.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="card">
    <h3>Upload KMZ or KML</h3>
    <p class="small-muted">The tool reads placemarks, extracts distance text, calculates geometry length, and compares both values.</p>
</div>
""", unsafe_allow_html=True)

def haversine_ft(lon1, lat1, lon2, lat2):
    r_ft = 20925524.9
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return r_ft * c


def parse_coords(coord_text):
    coords = []
    if not coord_text:
        return coords

    for part in coord_text.strip().split():
        pieces = part.split(",")
        if len(pieces) >= 2:
            try:
                lon = float(pieces[0])
                lat = float(pieces[1])
                alt = float(pieces[2]) if len(pieces) > 2 else 0
                coords.append((lon, lat, alt))
            except ValueError:
                pass

    return coords


def geometry_length_ft(coords):
    total = 0
    for i in range(len(coords) - 1):
        lon1, lat1, _ = coords[i]
        lon2, lat2, _ = coords[i + 1]
        total += haversine_ft(lon1, lat1, lon2, lat2)
    return total


def extract_entered_distance(description):
    if not description:
        return None

    text = re.sub(r"<[^>]+>", " ", description)
    text = text.replace("&nbsp;", " ")

    patterns = [
        r"feet\s*[:=]+\s*([0-9,.]+)",
        r"footage\s*[:=]+\s*([0-9,.]+)",
        r"length\s*[:=]+\s*([0-9,.]+)\s*ft",
        r"([0-9,.]+)\s*ft",
        r"miles\s*[:=]+\s*([0-9,.]+)",
        r"([0-9,.]+)\s*mi\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(",", ""))
            if "mile" in pattern or r"\s*mi" in pattern:
                return value * 5280
            return value

    return None


def get_kml_from_upload(uploaded_file):
    filename = uploaded_file.name.lower()
    data = uploaded_file.read()

    if filename.endswith(".kmz"):
        with zipfile.ZipFile(BytesIO(data), "r") as kmz:
            kml_names = [name for name in kmz.namelist() if name.lower().endswith(".kml")]
            if not kml_names:
                raise ValueError("No KML file found inside KMZ.")
            return kmz.read(kml_names[0])

    if filename.endswith(".kml"):
        return data

    raise ValueError("Please upload a .kmz or .kml file.")


def find_text(element, tag_name):
    for child in element.iter():
        if child.tag.endswith(tag_name):
            return child.text
    return None


def process_kml(kml_bytes):
    root = ET.fromstring(kml_bytes)

    placemarks = []
    for elem in root.iter():
        if elem.tag.endswith("Placemark"):
            placemarks.append(elem)

    rows = []
    cleaned_placemarks = []

    for index, pm in enumerate(placemarks, start=1):
        name = find_text(pm, "name") or f"Placemark {index}"
        description = find_text(pm, "description") or ""

        coord_text = None
        for child in pm.iter():
            if child.tag.endswith("coordinates"):
                coord_text = child.text
                break

        coords = parse_coords(coord_text)
        calc_ft = geometry_length_ft(coords) if len(coords) > 1 else 0
        entered_ft = extract_entered_distance(description)

        rows.append({
            "placemark": name,
            "entered_ft": entered_ft,
            "entered_mi": entered_ft / 5280 if entered_ft is not None else None,
            "calculated_ft": calc_ft,
            "calculated_mi": calc_ft / 5280,
            "difference_ft": entered_ft - calc_ft if entered_ft is not None else None,
            "points": len(coords),
        })

        if len(coords) > 1:
            coord_lines = " ".join([f"{lon},{lat},{alt}" for lon, lat, alt in coords])
            clean_desc = (
                f"Entered feet: {entered_ft if entered_ft is not None else 'Not found'}<br>"
                f"Calculated feet: {calc_ft:.3f}<br>"
                f"Calculated miles: {calc_ft / 5280:.6f}"
            )

            cleaned_placemarks.append(f"""
    <Placemark>
      <name>{name}</name>
      <description><![CDATA[{clean_desc}]]></description>
      <Style>
        <LineStyle>
          <width>4</width>
        </LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{coord_lines}</coordinates>
      </LineString>
    </Placemark>
""")

    clean_kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Cleaned KMZ Length Routes</name>
    {''.join(cleaned_placemarks)}
  </Document>
</kml>
"""

    df = pd.DataFrame(rows)
    return df, clean_kml


def make_kmz(kml_text):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr("doc.kml", kml_text)
    buffer.seek(0)
    return buffer.getvalue()


uploaded_file = st.file_uploader("Upload KMZ or KML", type=["kmz", "kml"])

if uploaded_file:
    try:
        kml_bytes = get_kml_from_upload(uploaded_file)
        df, cleaned_kml = process_kml(kml_bytes)

        st.success("File processed successfully.")

        entered_total = df["entered_ft"].sum(skipna=True)
        calculated_total = df["calculated_ft"].sum(skipna=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Entered Total Feet", f"{entered_total:,.3f}")
        col2.metric("Calculated Total Feet", f"{calculated_total:,.3f}")
        col3.metric("Difference Feet", f"{entered_total - calculated_total:,.3f}")

        st.subheader("Comparison Table")
        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        kmz_data = make_kmz(cleaned_kml)

        st.download_button(
            "Download Comparison CSV",
            data=csv_data,
            file_name="length_comparison.csv",
            mime="text/csv",
        )

        st.download_button(
            "Download Cleaned KML",
            data=cleaned_kml.encode("utf-8"),
            file_name="cleaned_routes.kml",
            mime="application/vnd.google-earth.kml+xml",
        )

        st.download_button(
            "Download Cleaned KMZ",
            data=kmz_data,
            file_name="cleaned_routes.kmz",
            mime="application/vnd.google-earth.kmz",
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")