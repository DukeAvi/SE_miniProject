#!/usr/bin/env bash
set -euo pipefail

destination=${1:?Usage: install_jmeter.sh DESTINATION}
version=5.6.3
archive="apache-jmeter-${version}.tgz"
base="https://archive.apache.org/dist/jmeter/binaries"
mkdir -p "$destination"
curl --fail --location --silent --show-error "$base/$archive" -o "$destination/$archive"
curl --fail --location --silent --show-error "$base/$archive.sha512" -o "$destination/$archive.sha512"
(cd "$destination" && sha512sum --check "$archive.sha512")
tar -xzf "$destination/$archive" -C "$destination"
"$destination/apache-jmeter-$version/bin/jmeter" --version
