apt update

export DEBIAN_FRONTEND=noninteractive
apt install -y python3-pip
apt install -y nvme-cli

pip3 install prometheus-client
curl https://raw.githubusercontent.com/VladimirDiamandi/prometheus-monitoring-setup/main/nvme_metrics.py > /var/lib/node_exporter/nvme_metrics.py

cron_job="*/2 * * * * /bin/bash -c '{ PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /usr/bin/python3 /var/lib/node_exporter/nvme_metrics.py > /var/lib/node_exporter/textfile_collector/nvme.prom; } || echo "" > /var/lib/node_exporter/textfile_collector/nvme.prom'"
(crontab -l 2>/dev/null; echo "$cron_job") | crontab -
