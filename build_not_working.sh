#!/bin/sh

mvn clean package -DskipTests -Pnative

echo "Now run ./target/quarkus-python-hello-1.0.0-SNAPSHOT-runner"
echo "To test: curl -v http://localhost:8080/hello"
