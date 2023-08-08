#!/bin/sh

mvn clean package -DskipTests -Dquarkus.package.type=native-sources -Pnative
cd target/native-sources/
native-image --language:python --initialize-at-run-time=com.redhat.iteai.HelloResource  $(cat native-image.args)

echo "Now run ./target/native-sources/quarkus-python-hello-1.0.0-SNAPSHOT-runner"
echo "To test: curl -v http://localhost:8080/hello"
