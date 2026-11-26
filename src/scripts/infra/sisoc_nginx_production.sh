#!/bin/sh
# Install as /usr/local/sbin/sisoc-nginx-production, root-owned and not runner-writable.
exec /usr/bin/python3 -I /usr/local/libexec/sisoc-nginx-reconcile.py production
