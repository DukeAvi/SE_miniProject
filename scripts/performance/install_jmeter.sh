#!/usr/bin/env bash
set -euo pipefail

destination=${1:?Usage: install_jmeter.sh DESTINATION}
version=5.6.3
archive="apache-jmeter-${version}.tgz"
mkdir -p "$destination"
downloaded=false
for base in https://dlcdn.apache.org/jmeter/binaries https://archive.apache.org/dist/jmeter/binaries; do
  if curl --fail --location --silent --show-error --connect-timeout 15 --max-time 600 "$base/$archive" -o "$destination/$archive" &&
     curl --fail --location --silent --show-error --connect-timeout 15 --max-time 30 "$base/$archive.sha512" -o "$destination/$archive.sha512"; then
    downloaded=true
    break
  fi
done
if [ "$downloaded" != true ]; then
  echo "Could not download the pinned JMeter archive and checksum from Apache mirrors" >&2
  exit 1
fi
(cd "$destination" && sha512sum --check "$archive.sha512")
tar -xzf "$destination/$archive" -C "$destination"
"$destination/apache-jmeter-$version/bin/jmeter" --version
