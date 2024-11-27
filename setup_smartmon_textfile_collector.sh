apt update

export DEBIAN_FRONTEND=noninteractive
apt install -y python3-pip
apt install -y smartmontools

pip3 install prometheus-client
curl https://raw.githubusercontent.com/VladimirDiamandi/prometheus-monitoring-setup/main/smartmon.py > /var/lib/node_exporter/smartmon.py

cron_job="*/2 * * * * /bin/bash -c '{ PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /usr/bin/python3 /var/lib/node_exporter/smartmon.py > /var/lib/node_exporter/textfile_collector/smartmon.prom; } || echo "" > /var/lib/node_exporter/textfile_collector/smartmon.prom'"
(crontab -l 2>/dev/null; echo "$cron_job") | crontab -
