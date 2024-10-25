import os
import sys
import urllib.request
import ipaddress

# Configuration
MYSQL_EXPORTER_VERSION = "0.15.1"
MYSQL_EXPORTER_PORT = 9104
MY_CNF_DIR = "/etc/mysqld_exporter"
MY_CNF_PATH = f"{MY_CNF_DIR}/mysql_exporter.cnf"
MYSQL_EXPORTER_SERVICE = f"""
[Unit]
Description=MySQL Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=mysql_exporter
Group=mysql_exporter
Type=simple
ExecStart=/usr/local/bin/mysqld_exporter --web.listen-address=:{MYSQL_EXPORTER_PORT} --config.my-cnf={MY_CNF_PATH}

[Install]
WantedBy=multi-user.target
"""


# Step 1: Install MySQL Exporter
def install_mysql_exporter(build_architecture, db_user, db_password):
    # Download MySQL Exporter
    MYSQL_EXPORTER_URL = f"https://github.com/prometheus/mysqld_exporter/releases/download/v{MYSQL_EXPORTER_VERSION}/mysqld_exporter-{MYSQL_EXPORTER_VERSION}.{build_architecture}.tar.gz"
    print(f"Downloading MySQL Exporter ({build_architecture})...")
    urllib.request.urlretrieve(MYSQL_EXPORTER_URL, "mysqld_exporter.tar.gz")

    # Extract MySQL Exporter
    print("Extracting MySQL Exporter...")
    os.system("tar xvfz mysqld_exporter.tar.gz")

    # Move MySQL Exporter binary to /usr/local/bin/
    mysql_exporter_dir = (
        f"mysqld_exporter-{MYSQL_EXPORTER_VERSION}.{build_architecture}"
    )
    os.system(f"sudo mv {mysql_exporter_dir}/mysqld_exporter /usr/local/bin/")

    # Create a user for MySQL Exporter
    print("Creating mysql_exporter user...")
    os.system("sudo useradd --no-create-home --shell /bin/false mysql_exporter")

    # Create configuration directory
    os.makedirs(MY_CNF_DIR, exist_ok=True)

    # Create .my.cnf file with credentials
    print("Creating MySQL configuration file...")
    with open(MY_CNF_PATH, "w") as f:
        f.write(f"[client]\nuser={db_user}\npassword={db_password}\n")

    # Set permissions for mysql_exporter user
    os.system(f"sudo chown mysql_exporter:mysql_exporter {MY_CNF_PATH}")
    os.system(f"sudo chmod 600 {MY_CNF_PATH}")

    # Create systemd unit file
    print("Creating systemd unit for MySQL Exporter...")
    with open("/etc/systemd/system/mysqld_exporter.service", "w") as f:
        f.write(MYSQL_EXPORTER_SERVICE)

    # Reload systemd and start the service
    print("Starting MySQL Exporter...")
    os.system("sudo systemctl daemon-reload")
    os.system("sudo systemctl enable mysqld_exporter")
    os.system("sudo systemctl start mysqld_exporter")

    print("Removing temporary files...")
    os.system(f"rm -rf mysqld_exporter.tar.gz {mysql_exporter_dir}")


# Step 2: Set up iptables to allow access only from a specific IP
def configure_iptables(prometheus_ip):
    # Allow access from Prometheus server
    os.system(
        f"sudo iptables -I INPUT 1 -p tcp --dport {MYSQL_EXPORTER_PORT} -s {prometheus_ip} -j ACCEPT"
    )

    # Deny access to everyone else
    os.system(f"sudo iptables -I INPUT 2 -p tcp --dport {MYSQL_EXPORTER_PORT} -j DROP")

    # Create directory if it doesn't exist
    os.makedirs("/etc/iptables", exist_ok=True)
    # Save iptables rules to persist after reboot
    os.system("sudo sh -c 'iptables-save > /etc/iptables/rules.v4'")


def is_valid_ip(ip_address):
    try:
        # Validate IP address format (both IPv4 and IPv6)
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False


# Main script
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python3 setup_mysql_exporter.py <prometheus_ip> <build_architecture> <db_user> <db_password>"
        )
        print(
            "Example: python3 setup_mysql_exporter.py 192.168.1.1 linux-amd64 exporter secure_password"
        )
        sys.exit(1)

    prometheus_ip = sys.argv[1]
    build_architecture = sys.argv[2]
    db_user = sys.argv[3]
    db_password = sys.argv[4]

    # Validate IP address
    if not is_valid_ip(prometheus_ip):
        print(f"Invalid IP address: {prometheus_ip}")
        sys.exit(1)

    print(f"Installing MySQL Exporter for architecture {build_architecture}...")
    install_mysql_exporter(build_architecture, db_user, db_password)

    print(f"\nConfiguring iptables to allow access only from {prometheus_ip}...")
    configure_iptables(prometheus_ip)
