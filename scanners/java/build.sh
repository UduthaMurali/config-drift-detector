#!/bin/bash
# Build the Java scanner JAR using Maven
# Run this once on your machine: cd scanners/java && bash build.sh

set -e
echo "Building Java scanner..."
mvn package -q -DskipTests
echo "Done! JAR created at: target/java-scanner.jar"
echo "Test: java -jar target/java-scanner.jar ../../tests/fixtures/java/"
