#!/bin/bash

echo "creating users directory..."
mkdir users
echo "creating a grades directory..."
mkdir grades
echo "creating a blank assignments file..."
touch assignments
echo "creating a default serverconfig.py..."
cp serverconfig.py.example serverconfig.py

echo "done"
