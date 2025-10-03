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
- REST API endpoint to request journeys (source stop → destination stop).  
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
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)  

---

## Visuals

(Include screenshots or GIFs here once the frontend is ready. For now, example API request/response logs could be shown.)  


---

## Installation

### Requirements
- Python 3.7+  
- Django 5.0+  
- GTFS dataset (CSV files)  

### Setup
```bash
# Clone the repo
git clone https://gitlab.cs.uct.ac.za/mckevi001/capstone-project-MCKEVI001-JSSBEN002-NDXSHA111.git
cd raptor-journey-planner

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Load GTFS data into the database (scripts provided in /scripts)
python scripts/load_gtfs.py

# Run the server
python manage.py runserver
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
