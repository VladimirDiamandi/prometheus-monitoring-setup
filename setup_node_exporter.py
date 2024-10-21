import os
import sys
import urllib.request
import ipaddress

# Configuration
NODE_EXPORTER_VERSION = "1.8.2"
TEXTFILE_COLLECTOR_DIRECTORY = "/var/lib/node_exporter/textfile_collector"  # Constant for textfile collector directory
NODE_EXPORTER_PORT = 9100  # Constant for Node Exporter port
NODE_EXPORTER_SERVICE = f"""
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory={TEXTFILE_COLLECTOR_DIRECTORY} --web.listen-address=:{NODE_EXPORTER_PORT}

[Install]
WantedBy=multi-user.target
"""

# Step 1: Install Node Exporter
def install_node_exporter(build_architecture):
    # Download Node Exporter
    NODE_EXPORTER_URL = f"https://github.com/prometheus/node_exporter/releases/download/v{NODE_EXPORTER_VERSION}/node_exporter-{NODE_EXPORTER_VERSION}.{build_architecture}.tar.gz"
    print(f"Downloading Node Exporter ({build_architecture})...")
    urllib.request.urlretrieve(NODE_EXPORTER_URL, "node_exporter.tar.gz")
    
    # Extract Node Exporter
    print("Extracting Node Exporter...")
    os.system("tar xvfz node_exporter.tar.gz")
    
    # Move Node Exporter binary to /usr/local/bin/
    node_exporter_dir = f"node_exporter-{NODE_EXPORTER_VERSION}.{build_architecture}"
    os.system(f"sudo mv {node_exporter_dir}/node_exporter /usr/local/bin/")
    
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

    print("Removing temporary files...")
    os.system(f"rm -rf node_exporter.tar.gz {node_exporter_dir}")

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
    with open("/etc/cron.d/raid_status", "w") as cron_file:
        cron_file.write(f"*/5 * * * * root {script_path}\n")

# Step 3: Set up iptables to allow access only from a specific IP
def configure_iptables(prometheus_ip):    
    # Allow access from Prometheus server
    os.system(f"sudo iptables -A INPUT -p tcp --dport {NODE_EXPORTER_PORT} -s {prometheus_ip} -j ACCEPT")
    
    # Deny access to everyone else
    os.system(f"sudo iptables -A INPUT -p tcp --dport {NODE_EXPORTER_PORT} -j DROP")
    
    # Save iptables rules to persist after reboot
    os.system("sudo sh -c 'iptables-save > /etc/iptables/rules.v4'")

# Step 4: Validate IP address
def is_valid_ip(ip_address):
    try:
        # Validate IP address format (both IPv4 and IPv6)
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

# Main script
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 setup_node_exporter.py <prometheus_ip> <build_architecture>")
        print("Example: python3 setup_node_exporter.py 192.168.1.1 linux-amd64")
        sys.exit(1)

    prometheus_ip = sys.argv[1]
    build_architecture = sys.argv[2]

    # Validate IP address
    if not is_valid_ip(prometheus_ip):
        print(f"Invalid IP address: {prometheus_ip}")
        sys.exit(1)

    print(f"Installing Node Exporter for architecture {build_architecture}...")
    install_node_exporter(build_architecture)
    
    print("\nCreating RAID status script...")
    create_raid_status_script()
    
    print(f"\nConfiguring iptables to allow access only from {prometheus_ip}...")
    configure_iptables(prometheus_ip)
