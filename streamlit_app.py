import streamlit as st
import re
import csv
import io

st.set_page_config(
    page_title="ECO TEXT → CSV (Streaming Mode)",
    page_icon="📄",
    layout="wide"
)

st.title("📄 ECO TEXT → CSV (Memory Safe Streaming)")

uploaded_files = st.file_uploader(
    "Upload ECO TXT File(s)",
    type=["txt"],
    accept_multiple_files=True
)

PREVIEW_LIMIT = 100


# =========================================================
# 1️⃣ SPLIT ECO BLOCKS
# =========================================================
def split_eco_blocks(text):
    blocks = re.split(r'\n\s*Number:\s*', text)
    return ["Number: " + b for b in blocks if b.strip()]


# =========================================================
# 2️⃣ SAFE REGEX FIND
# =========================================================
def find(pattern, text):
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else ""


# =========================================================
# 3️⃣ PARSE ECO HEADER
# =========================================================
def parse_eco_header(block):

    eco = {}

    eco["ecoNumber"] = find(r'Number:\s*(\S+)', block)
    eco["createdDate"] = find(r'Created Date:\s*([0-9A-Z\-]+)', block)
    eco["type"] = find(r'Type:\s*(.*?)\s+CCDR', block)
    eco["status"] = find(r'Status:\s*(.*?)\s+Ver Test', block)
    eco["reason"] = find(r'Reason:\s*(.*?)\s+QA Group', block)
    eco["priority"] = find(r'Priority:\s*(.*?)\s+KEY COMPONENT', block)
    eco["requestor"] = find(r'Requestor:\s*(.*?)\s+ECO Effec', block)
    eco["ecoDepartment"] = find(r'ECO Department:\s*(\S+)', block)

    desc_match = re.search(
        r'ECO DESCRIPTION:(.*?)(Store &|Outstand PO|Vendor WIP|Prod WIP|Final Ass|FG &)',
        block,
        re.S
    )

    eco["description"] = ""
    if desc_match:
        eco["description"] = re.sub(r'\s+', ' ', desc_match.group(1)).strip()

    return eco


# =========================================================
# 4️⃣ PARSE COMPONENT TABLE
# =========================================================
def parse_components(item_block):

    lines = item_block.splitlines()
    capture = False
    current = None

    for line in lines:

        if re.match(r'\s*Action\s+Item\s+', line):
            capture = True
            continue

        if not capture:
            continue

        if re.match(r'\s*(Add|Disabl)', line):

            tail = line[116:].strip()
            buyer = ""
            cost = ""
            comments = ""

            if tail:
                parts = tail.split()

                cost_index = None
                for i, token in enumerate(parts):
                    if re.fullmatch(r'-?\d+(?:,\d{3})*(?:\.\d+)?', token):
                        cost_index = i
                        break

                if cost_index is not None:
                    buyer = " ".join(parts[:cost_index]).strip()
                    cost = parts[cost_index].strip()
                    comments = " ".join(parts[cost_index + 1:]).strip()
                else:
                    buyer = tail

            current = {
                "Action": line[0:7].strip(),
                "Component Item": line[7:18].strip(),
                "Component Description": line[18:59].strip(),
                "Quantity": line[59:68].strip(),
                "UOM": line[68:72].strip(),
                "Seq": line[72:77].strip(),
                "Disable Date": line[77:88].strip(),
                "Component Item Type": line[88:94].strip(),
                "Supply Type": line[94:106].strip(),
                "Make/Buy": line[106:116].strip(),
                "Buyer": buyer,
                "Cost": cost,
                "Comments": comments
            }

            yield current

        else:
            if current and line.strip():
                current["Component Description"] += " " + line.strip()


# =========================================================
# MAIN PROCESS (STREAMING)
# =========================================================
if uploaded_files:

    output = io.StringIO()
    writer = None

    preview_rows = []
    total_rows = 0

    for uploaded_file in uploaded_files:

        text = uploaded_file.read().decode("utf-8", errors="ignore")
        eco_blocks = split_eco_blocks(text)

        for block in eco_blocks:

            eco = parse_eco_header(block)

            item_blocks = re.split(r'\n\s*Revised Items', block)

            for item_block in item_blocks:

                if "Item:" not in item_block:
                    continue

                item_code = find(r'Item:\s*(\S+)', item_block)
                item_desc = find(r'Item:\s*\S+\s+(.*?)\s+Buyer:', item_block)
                effective_date = find(r'Effective Date:\s*([0-9A-Z\-]+)', item_block)

                for comp in parse_components(item_block):

                    row = {
                        # ECO
                        "ECO Number": eco["ecoNumber"],
                        "Created Date": eco["createdDate"],
                        "Status": eco["status"],
                        "Reason": eco["reason"],
                        "Priority": eco["priority"],
                        "Requestor": eco["requestor"],
                        "Department": eco["ecoDepartment"],
                        "ECO Description": eco["description"],

                        # ITEM
                        "Revised Item": item_code,
                        "Item Description": item_desc,
                        "Effective Date": effective_date,

                        # COMPONENT
                        **comp
                    }

                    if writer is None:
                        writer = csv.DictWriter(output, fieldnames=row.keys())
                        writer.writeheader()

                    writer.writerow(row)

                    if len(preview_rows) < PREVIEW_LIMIT:
                        preview_rows.append(row)

                    total_rows += 1

    if total_rows > 0:

        st.success(f"✅ Processed {total_rows:,} rows")

        if preview_rows:
            import pandas as pd
            st.warning(f"Showing first {len(preview_rows)} rows only")
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

        st.download_button(
            "⬇ Download Full CSV",
            output.getvalue().encode("utf-8"),
            "eco_streaming_output.csv",
            "text/csv"
        )

    else:
        st.warning("No ECO detected.")