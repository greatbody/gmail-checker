#!/bin/bash

while true; do
    echo "Starting mail checker..."
    python mail_checker.py
    echo "Waiting for 30 minutes before next check..."
    sleep 1800  # 30 minutes in seconds
done 