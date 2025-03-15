# 🛡️ PhishTracker: OSINT-Based Phishing Attribution Framework

PhishTracker is a **cyber threat intelligence framework** designed for **OSINT-based phishing detection and attribution**. It collects, processes, and analyzes data from **Twitter, Pastebin, WHOIS records**, and correlates phishing indicators using **Neo4j**.

---

## **📌 Features**
✔️ **Data Collection** – Scrapes phishing-related data from:
  - Twitter (Suspicious Tweets)
  - Pastebin (Leaked Credentials, Scam Messages)
  - WHOIS (Domain Ownership Records)

✔️ **NLP-Based Data Processing** – Extracts:
  - Email Addresses
  - Domains & IPs
  - Suspicious Keywords (e.g., "login", "password", "urgent")

✔️ **Threat Intelligence Correlation** – Uses **Neo4j** to:
  - Link phishing domains to IPs & Pastebin leaks
  - Identify relationships between different phishing campaigns

✔️ **Interactive Dashboard** – A **Flask-based web UI** for threat visualization.

---

## **📁 Project Structure**



---

## **🚀 Installation & Setup**
### **🔹 Prerequisites**
- **Python 3.8+**
- **Neo4j Database (Community/Enterprise)**
- **Git**
- **pip (Python Package Manager)**

### **🔹 1️⃣ Clone the Repository**
git clone https://github.com/taowei073/PhishTracker.git \
cd PhishTracker

### **🔹 2️⃣ Install Dependencies**
pip install -r requirements.txt

### **🔹 3️⃣ Configure Neo4j**
Start Neo4j and create a database called **PhishTrackerDB**.\
Set username/password in src/correlation/neo4j_loader.py:\
URI = "bolt://localhost:7687"\
USERNAME = "neo4j"\
PASSWORD = "test1234"

### **🔹 4️⃣ Run the Data Collection**
python main.py --collect

### **🔹 5️⃣ Process the Data & Load into Neo4j**
python main.py --process

### **🔹 6️⃣ Start the Flask Dashboard**
python main.py --dashboard \
Access UI at: http://127.0.0.1:5000

### **🔍 Example Queries (Neo4j)**
Run these in Neo4j Browser:\
✅ Find all phishing-related domains
MATCH (d:Domain) RETURN d.name LIMIT 10;

✅ Show relationships between Pastebin leaks and domains
MATCH (p:Paste)-[:LINKED_TO]->(d:Domain) RETURN p.url, d.name;

✅ Find IPs hosting phishing domains
MATCH (i:IP)<-[:HOSTED_ON]-(p:Paste) RETURN i.address, p.url;


### **📜 License**
This project is open-source under the MIT License.
