#!/bin/sh
# Despierta a mrtn-main. Home Assistant lo corre por SSH: ver wake_pc en configuration.yaml.
# Necesita el paquete wakeonlan (lo instala linux/bootstrap.sh).
MAC="${1:-58:11:22:4d:ef:8a}"
wakeonlan -i 192.168.0.255 "$MAC"
