from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27017")
db = client["legalbot_db"]

# Ensure clean collection
db.client_profiles.drop()

sample_clients = [
    {
        "_id": "case_1",
        "client_name": "Apex Innovations Ltd.",
        "jurisdiction": "Delaware Corporate & IP Law",
        "cases": [
            {
                "case_id": "APX-2026-01",
                "title": "Contractual Breach & Proprietary Code Leakage",
                "status": "ongoing",
                "summary": "Investigating unauthorized exfiltration of proprietary neural model weights and internal API documentation by former contractor Jordan Lee.",
                "court_updates": [
                    "2026-10-02: Delaware Court of Chancery scheduled preliminary injunction hearing.",
                    "2026-10-10: Subpoena served for personal cloud repository audit."
                ]
            },
            {
                "case_id": "APX-2026-02",
                "title": "Enterprise Series-B Equity Financing Diligence",
                "status": "ongoing",
                "summary": "Reviewing shareholder tag-along and drag-along covenants under Amended Shareholder Agreement.",
                "court_updates": []
            },
            {
                "case_id": "APX-2023-09",
                "title": "Apex Innovations v. Nexa Systems",
                "status": "closed",
                "summary": "Former contractor software misappropriation dispute.",
                "court_updates": [
                    "2023-11-15: Final decree entered granting $150,000 liquidated damages and permanent injunction."
                ]
            }
        ]
    },
    {
        "_id": "case_2",
        "client_name": "Northstar Systems LLC",
        "jurisdiction": "California & Federal Commercial Law",
        "cases": [
            {
                "case_id": "NST-2026-04",
                "title": "Enterprise Cloud SLA Default Dispute",
                "status": "ongoing",
                "summary": "Contesting 99.0% downtime violations and termination fees under Master Professional Services Agreement.",
                "court_updates": [
                    "2026-09-28: Formal cure notice expired without technical remediation."
                ]
            },
            {
                "case_id": "NST-2022-01",
                "title": "Northstar Corporate Subsidiary Merger",
                "status": "closed",
                "summary": "Merger agreement and rollover equity transfer.",
                "court_updates": [
                    "2022-08-30: Transaction closed with $1,000,000 indemnity escrow."
                ]
            }
        ]
    }
]

db.client_profiles.insert_many(sample_clients)
print("Successfully seeded MongoDB 'client_profiles' with dynamic multi-case records!")
