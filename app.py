import os
import time
import platform
from threading import Thread
from flask import Flask, jsonify, render_template_string
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017')
db = client['network_monitoring']
collection = db['ping_status']

# List of addresses to monitor with icons
addresses = {
    'Localhost': ('127.0.0.1', 'https://static.thenounproject.com/png/808277-200.png'),  # Placeholder icon
    'Google': ('google.com', 'https://www.google.com/favicon.ico'),
    'Cloudflare': ('cloudflare.com', 'https://www.cloudflare.com/favicon.ico'),
    'GitHub': ('github.com', 'https://github.githubassets.com/favicons/favicon.png'),
    'LinkedIn': ('linkedin.com', 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/LinkedIn_logo_initials.png/240px-LinkedIn_logo_initials.png'),
    'Wikipedia': ('wikipedia.org', 'https://en.wikipedia.org/static/favicon/wikipedia.ico'),
    'Stack Overflow': ('stackoverflow.com', 'https://cdn.sstatic.net/Sites/stackoverflow/img/favicon.ico')
}

# Determine the OS to use the appropriate ping command
is_windows = platform.system().lower() == 'windows'

def ping_address(address):
    if is_windows:
        # For Windows
        command = f"ping -n 1 -w 2000 {address} > nul"
    else:
        # For Unix-like systems (Linux, macOS)
        command = f"ping -c 1 -W 2 {address} > /dev/null 2>&1"
    return os.system(command) == 0

# Function to check the status of each address and save to MongoDB
def check_status():
    status = {}
    for name, (address, icon_url) in addresses.items():
        start_time = time.time()
        is_up = ping_address(address)
        end_time = time.time()
        if is_up:
            elapsed_time = (end_time - start_time) * 1000  # Convert to milliseconds
            if elapsed_time < 100:
                status[name] = ('Good', elapsed_time, icon_url)
            else:
                status[name] = ('Low', elapsed_time, icon_url)
        else:
            status[name] = ('Down', None, icon_url)
        
        # Save status to MongoDB
        status_doc = {
            'name': name,
            'address': address,
            'status': status[name][0],
            'response_time_ms': elapsed_time if is_up else None,
            'timestamp': int(time.time()),
            'icon_url': icon_url
        }
        collection.insert_one(status_doc)

    return status

# Main route to serve the dashboard (HTML omitted for brevity)
@app.route('/')
def dashboard():
    # Your dashboard HTML remains unchanged
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Network Monitoring Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh; /* Ensure full viewport height */
        }
        .container {
            width: 80%;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            text-align: center;
            margin-top: 50px; /* Push down the entire container */
        }
        h1 {
            color: #fff;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.4);
            font-size: 2.5em;
            margin-bottom: 20px;
        }
        .status {
            display: flex;
            justify-content: space-between;
            padding: 10px 20px;
            margin: 10px 0;
            border-radius: 5px;
            background-color: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .Good {
            border-left: 5px solid #28a745;
        }
        .Low {
            border-left: 5px solid #ffc107; /* Yellow border for Low status */
            background-color: rgba(255, 255, 0, 0.3); /* Brighter background for Low status */
        }
        .Down {
            border-left: 5px solid #dc3545;
        }
        .status-name {
            font-weight: bold;
            font-size: 1.2em;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
        }
        .status-logo {
            width: 32px;
            height: 32px;
            margin-right: 10px;
        }
        .status-time {
            font-size: 1em;
            color: #ddd;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
        }
        .timestamp {
            text-align: center;
            margin-top: 20px;
            color: #ddd;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
        }
        #spinner {
            display: none;
            margin: 20px auto;
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        .chart-container {
            margin-top: 100px; /* Increased top margin to push down the chart */
            width: 95%; /* Make chart wider */
            height: 500px; /* Increased chart height */
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Network Monitoring Dashboard</h1>
        <div id="status-container"></div>
        <div class="chart-container">
            <canvas id="myChart"></canvas>
        </div>
        <div id="spinner"></div>
        <div class="timestamp" id="timestamp"></div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        function fetchStatus() {
            const spinner = document.getElementById('spinner');
            spinner.style.display = 'block';

            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('status-container');
                    const timestamp = document.getElementById('timestamp');
                    container.innerHTML = '';
                    for (const [name, [state, elapsed_time, icon_url]] of Object.entries(data)) {
                        const class_name = state;
                        const elapsed_time_str = elapsed_time !== null ? ` (${elapsed_time.toFixed(2)} ms)` : '';
                        const div = document.createElement('div');
                        div.className = 'status ' + class_name;
                        
                        const nameDiv = document.createElement('div');
                        nameDiv.className = 'status-name';
                        const img = document.createElement('img');
                        img.src = icon_url;
                        img.className = 'status-logo';
                        nameDiv.appendChild(img);
                        const text = document.createElement('span');
                        text.textContent = name;
                        nameDiv.appendChild(text);
                        
                        const timeDiv = document.createElement('div');
                        timeDiv.className = 'status-time';
                        timeDiv.textContent = `${state}${elapsed_time_str}`;
                        
                        div.appendChild(nameDiv);
                        div.appendChild(timeDiv);
                        
                        container.appendChild(div);
                    }
                    updateChart(data);  // Update chart with new data
                    const now = new Date();
                    timestamp.textContent = 'Last updated: ' + now.toLocaleTimeString();
                    spinner.style.display = 'none';
                });
        }

        // Function to update the chart with new data
        function updateChart(data) {
            const labels = Object.keys(data);
            const times = labels.map(key => {
                const [, elapsed_time] = data[key];
                return elapsed_time !== null ? elapsed_time.toFixed(2) : 'NaN';
            });

            const ctx = document.getElementById('myChart').getContext('2d');
            if (window.myChart instanceof Chart) {
                // Update existing chart
                window.myChart.data.labels = labels;
                window.myChart.data.datasets[0].data = times;
                window.myChart.update();
            } else {
                // Create new chart
                                // Create new chart
                window.myChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Response Time (ms)',
                            data: times,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.5)',
                                'rgba(54, 162, 235, 0.5)',
                                'rgba(255, 206, 86, 0.5)',
                                'rgba(75, 192, 192, 0.5)',
                                'rgba(153, 102, 255, 0.5)',
                                'rgba(255, 159, 64, 0.5)',
                                'rgba(255, 99, 132, 0.5)'
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(255, 99, 132, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            }
        }

        setInterval(fetchStatus, 5000);  // Fetch status every 5 seconds
        fetchStatus();  // Initial fetch
    </script>
</body>
</html>
    """

# Route to fetch status data in JSON format
@app.route('/status')
def get_status():
    return jsonify(check_status())

# Start the Flask server
if __name__ == '__main__':
    server_thread = Thread(target=app.run, kwargs={'host': 'localhost', 'port': 8050})
    server_thread.daemon = True
    server_thread.start()
    print('Starting server at http://localhost:8050')

    # Loop to periodically update and store status in MongoDB every 7 seconds
    while True:
        try:
            check_status()
            time.sleep(7)  # Update every 7 seconds
        except KeyboardInterrupt:
            break

