#!/bin/bash

echo "creating static files directory..."
mkdir static
echo "creating emails directory..."
mkdir emails
echo "creating a blank assignments file..."
touch assignments
echo "creating a default serverconfig.py..."
cp serverconfig.py.example serverconfig.py

echo "done"
