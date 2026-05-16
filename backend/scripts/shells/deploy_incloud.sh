#!/bin/bash
# Deploy Incloud Playbook Script
# Target: 192.168.23.38
# Purpose: Execute ansible playbook on remote server
set -e # Exit on first error

cd /home/shdy/.ansible && ansible-playbook -i inventory/incloud_all/hosts playbooks/site.yml -l all
