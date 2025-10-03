# RAPTOR Journey Planner

**CSC3003S Capstone Project — Stage 4: Implementation and Testing**

A Django-based public transport journey planning web application built on the [RAPTOR algorithm](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf) for fast and efficient transit routing.  

---

## Description

The RAPTOR Journey Planner enables users to plan trips across a public transport network efficiently.  
It uses **GTFS data** and the **RAPTOR (Round-Based Public Transit Routing) algorithm** to compute optimal routes between stops, considering transfers and travel times.  

Unlike traditional shortest-path algorithms (e.g., Dijkstra’s), RAPTOR works in **rounds**, making it both **faster and more scalable** for journey planning across large transport networks.

### Features
- Efficient journey planning using the RAPTOR algorithm.  
- Django-based web backend for queries and routing.  
- Integration with GTFS data (`trips.txt`, `stop_times.txt`, etc.).  
- REST API to request journeys (source stop → destination stop).  
- Filtering and cleaning scripts for GTFS preprocessing.  

---

## Project Status

- ✅ **Stage 1** – Project Startup  
- ✅ **Stage 2** – Planning and Modelling  
- ✅ **Stage 3** – Prototype  
- 🔄 **Stage 4** – Implementation and Testing (current)  

---

## Badges

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)

---

## Installation

### Requirements
- Python 3.0+  
- Django  
- GTFS dataset  

### Setup
```bash
# Clone the repo
git clone https://gitlab.cs.uct.ac.za/mckevi001/capstone-project-MCKEVI001-JSSBEN002-NDXSHA111.git
cd <project dir>

# Create virtual environment
python -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
cd src/frontend
npm install
npm fund

# Apply database migrations
cd ../backend
python manage.py migrate
```

---

# Usage

### Start the Django development server
```bash
python manage.py runserver
```

### Start the Frontend server
```bash
npm run dev

note the port number given here — this will be used to access the webapp
```
### Access the web app
```bash
http://localhost:<port-number>
```
