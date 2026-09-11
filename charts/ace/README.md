# ace

Installs the ACE operator, and optionally a platform for it to reconcile.

## What it installs

- The `AutomationPlatform` CRD, the operator's RBAC, and the operator itself.
- Optionally an `AutomationPlatform` resource (`platform.create=true`).

That is the whole list. ACE deploys the controller, hub and EDA itself, so
nothing else has to be installed first. Earlier versions rendered an `AWX`, a
`Galaxy` and an `EDA` custom resource and required awx-operator,
galaxy-operator and eda-server-operator to be present to reconcile them; none
of those are needed now.

Owning the Deployments also means every image is one we build. The hand-off
design left three upstream images in the platform that were never ours to
choose -- `quay.io/ansible/awx-ee` as the controller's receptor sidecar,
`quay.io/ansible/galaxy-ui` and `quay.io/ansible/eda-ui` as web tiers that only
ever ran nginx.

## Usage

```sh
helm install ace charts/ace -n ace-system --create-namespace
```

With a platform, reachable on its own address:

```sh
helm install ace charts/ace -n ace-system --create-namespace \
  --set platform.create=true \
  --set platform.namespace=ace \
  --set platform.gateway.external_url=https://ace.example.com \
  --set platform.gateway.service_type=LoadBalancer
```

envoy terminates TLS on 443 itself and its listener is programmed by the
gateway over xDS, so `LoadBalancer` gives the front door a real address rather
than putting an HTTP proxy in front of it. Reaching the gateway's plain nginx
port instead serves the console and 404s every component API, because envoy is
what routes `/api/controller/`, `/api/galaxy/` and `/api/eda/`.

## Upgrades

The CRD ships in `crds/`, which Helm installs once and never updates. After a
chart upgrade that changes the schema, apply it by hand:

```sh
kubectl apply -f charts/ace/crds/
```
