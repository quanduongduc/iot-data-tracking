#!/bin/bash

set -e

# Check if the package name and environment name were provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Error: Both package name and environment name must be provided."
    echo "Usage: ./require.sh <package_name> <env>"
    exit 1
fi

# Get the package name from the command line arguments
package_name=$1

# Get the environment name from the command line arguments (base, dev, prod)
env=$2

requirements_path="./requirements/$env.txt"

# Get the package information
package_info=$(pip show $package_name)

# Check if the package information is valid
if [ -z "$package_info" ]; then
    echo "Package '$package_name' not found. Installing..."
    pip install $package_name
    package_info=$(pip show $package_name)
fi

# Extract the name and version
name=$(echo "$package_info" | grep '^Name: ' | cut -d' ' -f2)
version=$(echo "$package_info" | grep '^Version: ' | cut -d' ' -f2)

# dump the package information to a file
echo "$name==$version" >> $requirements_path
echo "Package '$name' with version '$version' added to '$requirements_path'."
echo "preview of $requirements_path : "
cat $requirements_path