#!/usr/bin/env python3
"""Regenerate the chart's ClusterRole from the kustomize base's role.yaml.

The operator can be installed either way, and it must end up with the same
permissions both times. Keeping two hand-written copies did not survive the
first change to one of them: the base gained jobs and roles/rolebindings, the
chart did not, and the operator could not create the controller's RBAC.
"""
import sys, yaml

src = 'config/rbac/role.yaml'
dst = 'charts/ace/templates/rbac.yaml'

docs = [d for d in yaml.safe_load_all(open(src)) if d]
cr = next(d for d in docs if d['kind'] == 'ClusterRole')
rules = yaml.dump({'rules': cr['rules']}, default_flow_style=False, sort_keys=False)
rules = '\n'.join('  ' + l if l.strip() else l for l in rules.splitlines()[1:])

out = """{{- if .Values.rbac.create }}
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: {{ include "ace.fullname" . }}
  labels:
    {{- include "ace.labels" . | nindent 4 }}
# GENERATED from config/rbac/role.yaml by hack/sync-chart-rbac.py -- do not
# edit. CI fails if this file does not match what that script produces.
#
# Wider than it looks: the operator creates the components' Deployments, Jobs
# and the RBAC their pods need, so it must hold those permissions itself.
rules:
""" + rules + """
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {{ include "ace.fullname" . }}
  labels:
    {{- include "ace.labels" . | nindent 4 }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: {{ include "ace.fullname" . }}
subjects:
  - kind: ServiceAccount
    name: {{ include "ace.serviceAccountName" . }}
    namespace: {{ .Release.Namespace }}
{{- end }}
"""
if '--check' in sys.argv:
    if open(dst).read() != out:
        print(f'{dst} is out of date; run hack/sync-chart-rbac.py', file=sys.stderr)
        sys.exit(1)
    print(f'{dst} is up to date')
else:
    open(dst, 'w').write(out)
    print(f'wrote {dst}')
