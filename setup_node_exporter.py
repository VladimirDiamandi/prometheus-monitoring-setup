import os
import urllib.request

# Configuration
NODE_EXPORTER_VERSION = "1.6.0"
NODE_EXPORTER_URL = f"https://github.com/prometheus/node_exporter/releases/download/v{NODE_EXPORTER_VERSION}/node_exporter-{NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
TEXTFILE_COLLECTOR_DIRECTORY = "/var/lib/node_exporter/textfile_collector"  # Constant for textfile collector directory
NODE_EXPORTER_SERVICE = f"""
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory={TEXTFILE_COLLECTOR_DIRECTORY}

[Install]
WantedBy=multi-user.target
"""

# Step 1: Install Node Exporter
def install_node_exporter():
    # Download Node Exporter
    print("Downloading Node Exporter...")
    urllib.request.urlretrieve(NODE_EXPORTER_URL, "node_exporter.tar.gz")
    
    # Extract Node Exporter
    print("Extracting Node Exporter...")
    os.system("tar xvfz node_exporter.tar.gz")
    os.system("sudo mv node_exporter-1.6.0.linux-amd64/node_exporter /usr/local/bin/")
    
    # Create a user for Node Exporter
    print("Creating node_exporter user...")
    os.system("sudo useradd --no-create-home --shell /bin/false node_exporter")
    
    # Create textfile collector directory
    print(f"Creating directory for textfile collector at {TEXTFILE_COLLECTOR_DIRECTORY}...")
    os.makedirs(TEXTFILE_COLLECTOR_DIRECTORY, exist_ok=True)
    
    # Create systemd unit file
    print("Creating systemd unit for Node Exporter...")
    with open("/etc/systemd/system/node_exporter.service", "w") as f:
        f.write(NODE_EXPORTER_SERVICE)
    
    # Reload systemd and start the service
    print("Starting Node Exporter...")
    os.system("sudo systemctl daemon-reload")
    os.system("sudo systemctl enable node_exporter")
    os.system("sudo systemctl start node_exporter")

# Step 2: Create RAID status script
def create_raid_status_script():
    # Script to parse /proc/mdstat and generate metrics for Node Exporter
    raid_script = f"""
#!/bin/bash
# Parse /proc/mdstat and output RAID status for Prometheus

if grep -q "\\[.*_.*\\]" /proc/mdstat; then
  echo "raid_sync_active 1" > {TEXTFILE_COLLECTOR_DIRECTORY}/raid_status.prom
else
  echo "raid_sync_active 0" > {TEXTFILE_COLLECTOR_DIRECTORY}/raid_status.prom
fi
"""
    
    # Write the script to file
    print("Creating RAID status script...")
    script_path = "/usr/local/bin/raid_status.sh"
    with open(script_path, "w") as f:
        f.write(raid_script)
    
    # Make the script executable
    os.system(f"sudo chmod +x {script_path}")

    # Set up a cron job to run the script every 5 minutes
    print("Setting up cron job to run RAID status script...")
    cron_job = f"*/5 * * * * {script_path}"
    os.system(f'(sudo crontab -l 2>/dev/null; echo "{cron_job}") | sudo crontab -')

# Step 3: Check metrics
def check_metrics():
    # Check if metrics are available via HTTP
    url = "http://localhost:9100/metrics"
    print("Checking metrics at http://localhost:9100/metrics")
    
    try:
        with urllib.request.urlopen(url) as response:
            metrics = response.read().decode("utf-8")
            print("Metrics successfully fetched. Examples:")
            print("Uptime:", get_uptime(metrics))
            print("CPU Load:", get_cpu_load(metrics))
            print("RAM Usage:", get_ram_usage(metrics))
            print("Disk Usage:", get_disk_usage(metrics))
            print("RAID Status (mdstat):", get_mdstat_status())
    except Exception as e:
        print("Error while fetching metrics:", e)

# Functions to extract specific metrics
def get_uptime(metrics):
    # Extract uptime from metrics (convert seconds to hours)
    uptime_line = [line for line in metrics.split("\n") if "node_time_seconds" in line]
    if uptime_line:
        uptime_seconds = float(uptime_line[0].split()[1])
        return uptime_seconds / 3600  # Convert seconds to hours
    return None

def get_cpu_load(metrics):
    # Extract CPU load (average over 1 minute)
    load_lines = [line for line in metrics.split("\n") if "node_load1" in line]
    if load_lines:
        return float(load_lines[0].split()[1])
    return None

def get_ram_usage(metrics):
    # Extract total and available memory, then calculate used memory percentage
    mem_total = None
    mem_free = None
    for line in metrics.split("\n"):
        if "node_memory_MemTotal_bytes" in line:
            mem_total = float(line.split()[1])
        if "node_memory_MemAvailable_bytes" in line:
            mem_free = float(line.split()[1])
    if mem_total and mem_free:
        return (mem_total - mem_free) / mem_total * 100  # Calculate memory usage in percentage
    return None

def get_disk_usage(metrics):
    # Extract disk usage by checking available space
    disk_usage_lines = [line for line in metrics.split("\n") if "node_filesystem_avail_bytes" in line]
    if disk_usage_lines:
        return float(disk_usage_lines[0].split()[1])  # Return available disk space in bytes
    return None

def get_mdstat_status():
    # Check RAID status from /proc/mdstat
    try:
        with open("/proc/mdstat") as f:
            mdstat = f.read()
            # If no RAID arrays are listed
            if "Personalities" in mdstat and "unused devices" in mdstat:
                return "No RAID arrays are active"
            elif "active" in mdstat:
                return "RAID is working"
            else:
                return "RAID has issues"
    except Exception as e:
        return f"Error: {e}"

# Main script
if __name__ == "__main__":
    print("Installing Node Exporter...")
    install_node_exporter()
    
    print("\nCreating RAID status script...")
    create_raid_status_script()
    
    print("\nChecking Node Exporter metrics...")
    check_metrics()
