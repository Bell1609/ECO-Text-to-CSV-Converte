import streamlit as st
import pandas as pd
import re

st.set_page_config(
    page_title="ECO TEXT → CSV",
    page_icon="📄",
    layout="wide"
)

st.title("📄 ECO TEXT → CSV")

uploaded_files = st.file_uploader(
    "Upload ECO TXT File(s)",
    type=["txt"],
    accept_multiple_files=True
)

all_rows = []


# =========================================================
# 1️⃣ SPLIT ECO BLOCKS
# =========================================================
def split_eco_blocks(text):
    blocks = re.split(r'\n\s*Number:\s*', text)
    result = []

    for b in blocks:
        if not b.strip():
            continue
        result.append("Number: " + b)

    return result


# =========================================================
# 2️⃣ PARSE ECO HEADER (FULL)
# =========================================================
def parse_eco_header(block):

    def find(pattern):
        m = re.search(pattern, block, re.S)
        return m.group(1).strip() if m else ""

    eco = {}

    eco["ecoNumber"] = find(r'Number:\s*(\S+)')
    eco["createdDate"] = find(r'Created Date:\s*([0-9A-Z\-]+)')
    eco["type"] = find(r'Type:\s*(.*?)\s+CCDR')
    eco["status"] = find(r'Status:\s*(.*?)\s+Ver Test')
    eco["reason"] = find(r'Reason:\s*(.*?)\s+QA Group')
    eco["priority"] = find(r'Priority:\s*(.*?)\s+KEY COMPONENT')
    eco["requestor"] = find(r'Requestor:\s*(.*?)\s+ECO Effec')
    eco["ecoDepartment"] = find(r'ECO Department:\s*(.*)')
    eco["approveStatus"] = find(r'Approve Status:\s*(.*)')

    desc_match = re.search(
        r'ECO DESCRIPTION:(.*?)(Store &|Outstand PO|Vendor WIP|Prod WIP|Final Ass|FG &)',
        block,
        re.S
    )

    eco["description"] = ""
    if desc_match:
        eco["description"] = re.sub(r'\s+', ' ', desc_match.group(1)).strip()

    eco["revisedItems"] = []

    return eco


# =========================================================
# 3️⃣ SPLIT ITEM BLOCKS
# =========================================================
def split_revised_items(block):
    parts = re.split(r'\n\s*Revised Items', block)
    return [p for p in parts if "Item:" in p]


# =========================================================
# 4️⃣ PARSE ITEM HEADER (FULL)
# =========================================================
def parse_item_block(item_block):

    def find(pattern):
        m = re.search(pattern, item_block, re.S)
        return m.group(1).strip() if m else ""

    item = {}

    item["item"] = find(r'Item:\s*(\S+)')
    item["itemDescription"] = find(r'Item:\s*\S+\s+(.*?)\s+Buyer:')
    item["upLevelItem"] = find(r'Up Level Item:\s*(.*?)\s+Cur Rev')
    item["topModel"] = find(r'Top Model:\s*(.*?)\s+New Rev')
    item["effectiveDate"] = find(r'Effective Date:\s*([0-9A-Z\-]+)')
    item["itemStatus"] = find(r'Status:\s*(.*?)\s+Use Up')
    item["itemType"] = find(r'Item Type:\s*(.*?)\s+Update WIP')
    item["updateWIP"] = find(r'Update WIP:\s*(\S+)')
    item["mrpActive"] = find(r'MRP Active:\s*(\S+)')

    item["components"] = parse_components(item_block)

    return item


# =========================================================
# 5️⃣ PARSE COMPONENT TABLE (ALL COLUMNS)
# =========================================================
def parse_components(item_block):

    components = []
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

            current = {
                "action": line[0:7].strip(),
                "componentItem": line[7:18].strip(),
                "description": line[18:59].strip(),
                "quantity": line[59:68].strip(),
                "uom": line[68:72].strip(),
                "seq": line[72:77].strip(),
                "disableDate": line[77:88].strip(),
                "itemType": line[88:94].strip(),
                "supplyType": line[94:106].strip(),
                "makeBuy": line[106:116].strip(),
                "buyer": line[116:132].strip(),
                "cost": line[132:140].strip(),
                "comments": line[140:].strip()
            }

            components.append(current)

        else:
            if current and line.strip():
                current["description"] += " " + line.strip()

    return components


# =========================================================
# MAIN
# =========================================================
if uploaded_files:

    for uploaded_file in uploaded_files:

        text = uploaded_file.read().decode("utf-8", errors="ignore")
        eco_blocks = split_eco_blocks(text)

        for block in eco_blocks:

            eco = parse_eco_header(block)
            item_blocks = split_revised_items(block)

            for item_block in item_blocks:

                item = parse_item_block(item_block)
                eco["revisedItems"].append(item)

            # ---------------- FLATTEN ----------------
            for item in eco["revisedItems"]:
                if item["components"]:
                    for comp in item["components"]:

                        row = {
                            # ECO LEVEL
                            "ECO Number": eco["ecoNumber"],
                            "Created Date": eco["createdDate"],
                            "Type": eco["type"],
                            "Status": eco["status"],
                            "Reason": eco["reason"],
                            "Priority": eco["priority"],
                            "Requestor": eco["requestor"],
                            "Department": eco["ecoDepartment"],
                            "Approve Status": eco["approveStatus"],
                            "ECO Description": eco["description"],

                            # ITEM LEVEL
                            "Revised Item": item["item"],
                            "Item Description": item["itemDescription"],
                            "Up Level Item": item["upLevelItem"],
                            "Top Model": item["topModel"],
                            "Effective Date": item["effectiveDate"],
                            "Item Status": item["itemStatus"],
                            "Item Type": item["itemType"],
                            "Update WIP": item["updateWIP"],
                            "MRP Active": item["mrpActive"],

                            # COMPONENT LEVEL
                            "Action": comp["action"],
                            "Component Item": comp["componentItem"],
                            "Component Description": comp["description"],
                            "Quantity": comp["quantity"],
                            "UOM": comp["uom"],
                            "Seq": comp["seq"],
                            "Disable Date": comp["disableDate"],
                            "Component Item Type": comp["itemType"],
                            "Supply Type": comp["supplyType"],
                            "Make/Buy": comp["makeBuy"],
                            "Buyer": comp["buyer"],
                            "Cost": comp["cost"],
                            "Comments": comp["comments"]
                        }

                        all_rows.append(row)

                else:
                    all_rows.append({
                        "ECO Number": eco["ecoNumber"],
                        "Revised Item": item["item"]
                    })

    if all_rows:
        df = pd.DataFrame(all_rows)
        st.success(f"Flatten completed: {len(df)} rows")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Download CSV",
            csv,
            "eco_enterprise_output.csv",
            "text/csv"
        )
    else:
        st.warning("No ECO detected.")