#!/bin/bash

echo "creating emails directory..."
mkdir emails
echo "creating a grades directory..."
mkdir grades
echo "creating a blank assignments file..."
touch assignments
echo "creating a blank admins file..."
touch admins
echo "creating a default serverconfig.py..."
cp serverconfig.py.example serverconfig.py

echo "done"
