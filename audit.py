import pandas as pd
import streamlit as st
from datetime import datetime

# -----------------------------
# CONFIGURATION
# -----------------------------

SESSION_EXPIRY_MAP = {
    "MJ25": "2025-06-30",
    "ON25": "2025-11-30",
    "MJ26": "2026-06-30",
    "ON26": "2026-11-30"
}

PRODUCT_TAG_MAP = {
    # Plus Plans (autorenewing)
    "Plus Plans [A Level] - per month": (["Plus User"], "30 Days"),
    "Plus Plans [A Level] - Quarterly": (["Plus User"], "90 Days"),
    "Plus Plans [A Level] - Yearly": (["Plus User"], "365 Days"),

    # Solo Passes (30 Days)
    "Solo Pass - Chemistry": (["Solo Pass", "Chemistry"], "30 Days"),
    "Solo Pass - Physics": (["Solo Pass", "Physics"], "30 Days"),
    "Solo Pass - Mathematics": (["Solo Pass", "Mathematics"], "30 Days"),
    "Solo Pass - Biology": (["Solo Pass", "Biology"], "30 Days"),
    "Solo Pass - Accounting": (["Solo Pass", "Accounting"], "30 Days"),
    "Solo Pass - Business": (["Solo Pass", "Business"], "30 Days"),
    "Solo Pass - Economics": (["Solo Pass", "Economics"], "30 Days"),
    "Solo Pass - Psychology": (["Solo Pass", "Psychology"], "30 Days"),

    # Solo Exam Pass MJ25
    "Solo Exam Pass - Chemistry, M/J 25": (["Solo EP MJ25", "Chemistry"], "Will Last May/June 25"),
    "Solo Exam Pass - Physics, M/J 25": (["Solo EP MJ25", "Physics"], "Will Last May/June 25"),
    "Solo Exam Pass - Mathematics, M/J 25": (["Solo EP MJ25", "Mathematics"], "Will Last May/June 25"),
    "Solo Exam Pass - Business, M/J 25": (["Solo EP MJ25", "Business"], "Will Last May/June 25"),
    "Solo Exam Pass - Economics, M/J 25": (["Solo EP MJ25", "Economics"], "Will Last May/June 25"),
    "Solo Exam Pass - Accounting, M/J 25": (["Solo EP MJ25", "Accounting"], "Will Last May/June 25"),
    "Solo Exam Pass - Biology, M/J 25": (["Solo EP MJ25", "Biology"], "Will Last May/June 25"),
    "Solo Exam Pass - Psychology, M/J 25": (["Solo EP MJ25", "Psychology"], "Will Last May/June 25"),

    # Solo Exam Pass ON25
    "Solo Exam Pass - Chemistry, O/N 25": (["Solo EP ON25", "Chemistry"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Physics, O/N 25": (["Solo EP ON25", "Physics"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Mathematics, O/N 25": (["Solo EP ON25", "Mathematics"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Business, O/N 25": (["Solo EP ON25", "Business"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Economics, O/N 25": (["Solo EP ON25", "Economics"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Accounting, O/N 25": (["Solo EP ON25", "Accounting"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Biology, O/N 25": (["Solo EP ON25", "Biology"], "Will Last Oct/Nov 25"),
    "Solo Exam Pass - Psychology, O/N 25": (["Solo EP ON25", "Psychology"], "Will Last Oct/Nov 25"),

    # Solo Exam Pass MJ26
    "Solo Exam Pass - Chemistry, M/J 26": (["Solo EP MJ26", "Chemistry"], "Will Last May/June 26"),
    "Solo Exam Pass - Physics, M/J 26": (["Solo EP MJ26", "Physics"], "Will Last May/June 26"),
    "Solo Exam Pass - Mathematics, M/J 26": (["Solo EP MJ26", "Mathematics"], "Will Last May/June 26"),
    "Solo Exam Pass - Business, M/J 26": (["Solo EP MJ26", "Business"], "Will Last May/June 26"),
    "Solo Exam Pass - Economics, M/J 26": (["Solo EP MJ26", "Economics"], "Will Last May/June 26"),
    "Solo Exam Pass - Accounting, M/J 26": (["Solo EP MJ26", "Accounting"], "Will Last May/June 26"),
    "Solo Exam Pass - Biology, M/J 26": (["Solo EP MJ26", "Biology"], "Will Last May/June 26"),
    "Solo Exam Pass - Psychology, M/J 26": (["Solo EP MJ26", "Psychology"], "Will Last May/June 26"),

    # All Access Exam Passes
    "All access - Exam Pass": (["Exam Pass 25"], "Will Last May/June 25"),
    "All Access - Exam Pass O/N 25": (["Exam Pass 25/ON"], "Will Last Oct/Nov 25"),
    "All access - Exam Pass M/J 26": (["Exam Pass 26/MJ"], "Will Last May/June 26"),
    "All access – Exam Pass O/N 26": (["Exam Pass 26/ON"], "Will Last Oct/Nov 26"),
}

# -----------------------------
# FUNCTIONS
# -----------------------------

def normalize_email(email):
    return str(email).strip().lower() if pd.notnull(email) else ""

def extract_session(tag):
    for code in SESSION_EXPIRY_MAP:
        if code in tag:
            return code
    return None

def calculate_expiry(order_date, duration_text, tag):
    if "Day" in duration_text:
        days = int(duration_text.split()[0])
        return order_date + pd.Timedelta(days=days)
    elif "Will Last" in duration_text:
        session = extract_session(tag)
        if session:
            return datetime.strptime(SESSION_EXPIRY_MAP[session], "%Y-%m-%d")
    return None

def build_entitlement_map(order_df):
    entitlements = {}
    for _, row in order_df.iterrows():
        email = normalize_email(row['Billing Address Email'])
        order_date = pd.to_datetime(row['Order Completed At'], errors='coerce')
        products = str(row['Line Items']).split("\n")

        for product in products:
            product = product.strip()
            if product in PRODUCT_TAG_MAP:
                tags, duration = PRODUCT_TAG_MAP[product]
                plan = tags[0]
                subjects = tags[1:]
                expiry = calculate_expiry(order_date, duration, plan)

                if email not in entitlements:
                    entitlements[email] = {}
                if plan not in entitlements[email]:
                    entitlements[email][plan] = {}

                for subject in subjects:
                    entitlements[email][plan][subject] = expiry
    return entitlements

def audit_user_access(lw_df, entitlements):
    today = datetime.today()
    results = []

    for _, row in lw_df.iterrows():
        email = normalize_email(row.get('email', ''))
        user = row.get('username', '')
        raw_tags = str(row.get('tags', '')).split(',')

        plans_present = set()
        subjects_present = []

        for tag in raw_tags:
            parts = tag.strip().split("|")
            if len(parts) >= 1:
                plans_present.add(parts[0])
            if len(parts) > 1:
                subjects_present.extend(parts[1:])

        for plan in plans_present:
            for subject in subjects_present:
                has_plan = entitlements.get(email, {}).get(plan, {}).get(subject)
                if has_plan:
                    decision = "Keep" if has_plan >= today else "Remove"
                    reason = f"Valid until {has_plan.date()}"
                    expiry = has_plan.date()
                else:
                    decision = "Remove"
                    reason = "No active entitlement"
                    expiry = "N/A"

                results.append({
                    "Email": email,
                    "User": user,
                    "Tag": f"{plan}|{subject}",
                    "Decision": decision,
                    "Reason": reason,
                    "Expiry": expiry
                })

    return pd.DataFrame(results)

# -----------------------------
# STREAMLIT UI
# -----------------------------

st.set_page_config(page_title="Access Audit", layout="wide")
st.title("🎓 LearnWorlds Audit System")

col1, col2 = st.columns(2)
with col1:
    lw_file = st.file_uploader("📥 LearnWorlds Users CSV")
with col2:
    met_file = st.file_uploader("📥 Metorik Orders CSV")

if lw_file and met_file:
    st.success("✅ Files received. Auditing...")
    lw_df = pd.read_csv(lw_file)
    met_df = pd.read_csv(met_file)

    entitlements = build_entitlement_map(met_df)
    audit_df = audit_user_access(lw_df, entitlements)

    st.subheader("📋 Audit Results")
    st.dataframe(audit_df)

    flagged = audit_df[audit_df['Decision'] == "Remove"]
    st.subheader(f"❌ Users to Remove: {len(flagged)}")
    st.dataframe(flagged)

    st.download_button("📤 Download Full Audit CSV", audit_df.to_csv(index=False), "audit_full.csv")
    st.download_button("📤 Download Flagged Users CSV", flagged.to_csv(index=False), "flagged_users.csv")
else:
    st.info("Please upload both CSV files to begin.")
