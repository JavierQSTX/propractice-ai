#! /bin/bash

poetry export -f requirements.txt --without-hashes | awk -F ';' '{print $1}' > requirements.txt
