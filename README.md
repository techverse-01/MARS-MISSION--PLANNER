# MARS-MISSION--PLANNER
​🔴 Project Ares: Interactive Mars Terrain Mapping & Navigation Interface
​An interactive web-based navigation frontend integrated with NASA planetary data, designed for Martian surface exploration and path planning.
​🧭 Problem Statement
​Exploring Martian terrain (such as the Jezero Crater) presents critical navigation challenges. Rovers must traverse complex landscapes filled with steep, jagged slopes (obstacles) and flat plains (safe paths). Traditional mapping tools lack specialized, lightweight interfaces optimized for visualizing planetary elevation data alongside interactive mission control controls (Start and Destination coordinate mapping) for simulated rover deployments.
​💡 Our Solution
​We developed a two-fold solution bridging raw planetary data processing and an interactive frontend web interface:
​Terrain Data Matrix (Grid Generation): Processed high-resolution Digital Elevation Model (DEM) maps from NASA/USGS into a structured binary matrix (grid.json). Slopes and rough terrain are mapped as obstacles (1), while safe plains are designated as passable paths (0).
​Interactive Mars GIBS Frontend: Built a responsive, space-themed web application using Leaflet.js and NASA GIBS (Global Imagery Browse Services) tiles to render authentic Mars surface imagery. Integrated dynamic click-to-pin functionality for setting Mission Start (Red Marker) and Destination (Blue Marker) coordinates.
​Immersive UI/UX Assets: Designed custom sci-fi dashboard overlay panels, futuristic rover pin icons, and destination markers using Canva/Figma to elevate the mission control experience.
​🚀 Key Features
​NASA GIBS Integration: Pulls real-time Mars surface raster tiles directly via Web Map Tile Service (WMTS).
​Interactive Coordinate Picker: Click-to-drop mechanism capturing precise latitude and longitude for routing.
​Sci-Fi Command Center Aesthetic: Custom-styled dark space theme with custom map markers and HUD overlays.
​Grid Matrix Ready: Prepared backend-compatible grid mapping for future pathfinding algorithms.
​🛠️ Tech Stack & Sources Used
​Data & APIs
​NASA GIBS (Global Imagery Browse Services): For rendering authentic Mars imagery tiles.
​USGS Astrogeology / NASA PDS: Source for high-resolution Digital Elevation Model (DEM) maps.
​Frontend & Libraries
​Leaflet.js: Open-source JavaScript library for interactive maps.
​HTML5 & CSS3: For structuring and styling the space-themed UI.
​JavaScript (ES6): Event handling and map-click coordinate logging.
​Design & Development Tools
​Canva & Figma: Created sci-fi dashboard panels, rover custom pins, and destination flag icons.
​AI Assistance: Leveraged for code architecture optimization, debugging, and documentation drafting.
​🔮 Future Scope
​Algorithm Integration: Implementing pathfinding algorithms (like A^* or Dijkstra) utilizing the generated grid.json matrix to automatically draw the safest route between start and destination points.
​Rover Telemetry Dashboard: Real-time speed, battery, and slope-angle tracking panel using the sci-fi UI assets.
​3D Terrain Simulation: Upgrading from 2D Leaflet mapping to a 3D WebGL-based Martian surface viewer (using Three.js/Cesium).
